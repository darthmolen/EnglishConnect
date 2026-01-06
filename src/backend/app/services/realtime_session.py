"""Azure OpenAI Realtime API session manager.

Manages WebSocket connections to the Realtime API for unified STT+LLM+TTS.
"""

import asyncio
import base64
import json
import logging
from typing import Any, AsyncIterator, Callable, Optional

import websockets
from azure.identity.aio import DefaultAzureCredential, ManagedIdentityCredential

from app.config import get_settings
from app.services.realtime_tools import get_tool_definitions

logger = logging.getLogger(__name__)


class RealtimeSessionManager:
    """Manages a real-time audio session with Azure OpenAI Realtime API.

    Key responsibilities:
    - Establish WebSocket connection to Realtime API
    - Configure session with system prompt, tools, and voice
    - Handle incoming audio from client
    - Process tool calls (render_vocabulary, get_teaching_help, etc.)
    - Forward audio responses to client
    """

    def __init__(
        self,
        system_prompt: str,
        tool_handlers: dict[str, Callable],
        voice: str = "alloy",
        language: str = "en",
    ):
        """Initialize the session manager.

        Args:
            system_prompt: System instructions for the agent
            tool_handlers: Dict mapping tool names to async handler functions
            voice: Voice to use for TTS (alloy, echo, fable, onyx, nova, shimmer)
            language: Primary language (en, es)
        """
        self.system_prompt = system_prompt
        self.tool_handlers = tool_handlers
        self.voice = voice
        self.language = language
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        self._credential = None

    async def _get_access_token(self) -> str:
        """Get access token for Azure OpenAI using managed identity or API key."""
        settings = get_settings()

        # If API key is set, return it directly (for local development)
        if settings.azure_openai_api_key:
            return settings.azure_openai_api_key

        # Use managed identity for cloud deployment
        if self._credential is None:
            if settings.azure_client_id:
                # User-assigned managed identity
                self._credential = ManagedIdentityCredential(
                    client_id=settings.azure_client_id
                )
            else:
                # System-assigned or default credential chain
                self._credential = DefaultAzureCredential()

        token = await self._credential.get_token(
            "https://cognitiveservices.azure.com/.default"
        )
        return token.token

    def _build_websocket_url(self) -> str:
        """Build the WebSocket URL for Realtime API."""
        settings = get_settings()

        # Convert https endpoint to wss
        endpoint = settings.azure_openai_endpoint.rstrip("/")
        if endpoint.startswith("https://"):
            endpoint = "wss://" + endpoint[8:]

        deployment = settings.azure_openai_realtime_deployment
        api_version = settings.azure_openai_realtime_api_version

        return f"{endpoint}/openai/realtime?api-version={api_version}&deployment={deployment}"

    async def connect(self) -> None:
        """Establish connection to Realtime API and configure session."""
        url = self._build_websocket_url()
        token = await self._get_access_token()

        settings = get_settings()
        headers = {}

        if settings.azure_openai_api_key:
            headers["api-key"] = token
        else:
            headers["Authorization"] = f"Bearer {token}"

        logger.info(f"Connecting to Realtime API: {url[:50]}...")

        self.ws = await websockets.connect(url, additional_headers=headers)
        self._connected = True

        # Configure the session
        await self._configure_session()
        logger.info("Realtime API session configured")

    async def _configure_session(self) -> None:
        """Send session configuration to Realtime API."""
        session_config = {
            "type": "session.update",
            "session": {
                "instructions": self.system_prompt,
                "modalities": ["audio", "text"],
                "voice": self.voice,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                    "create_response": True
                },
                "tools": get_tool_definitions(),
                "tool_choice": "auto"
            }
        }

        await self.ws.send(json.dumps(session_config))

    async def send_audio(self, audio_data: bytes) -> None:
        """Send audio chunk to Realtime API.

        Args:
            audio_data: Raw PCM16 audio data (24kHz, mono)
        """
        if not self._connected or not self.ws:
            raise RuntimeError("Not connected to Realtime API")

        event = {
            "type": "input_audio_buffer.append",
            "audio": base64.b64encode(audio_data).decode("utf-8")
        }
        await self.ws.send(json.dumps(event))

    async def commit_audio(self) -> None:
        """Commit the audio buffer to trigger processing."""
        if not self._connected or not self.ws:
            return

        event = {"type": "input_audio_buffer.commit"}
        await self.ws.send(json.dumps(event))

    async def cancel_response(self) -> None:
        """Cancel the current response (for interruption handling)."""
        if not self._connected or not self.ws:
            return

        event = {"type": "response.cancel"}
        await self.ws.send(json.dumps(event))

    async def process_events(self) -> AsyncIterator[dict[str, Any]]:
        """Process events from Realtime API and yield client events.

        Yields:
            Events to forward to the client:
            - {"type": "audio", "data": bytes} - Audio chunk
            - {"type": "transcript", "role": str, "text": str} - Transcription
            - {"type": "rich_content", "tool": str, "data": dict} - UI content
            - {"type": "speech_started"} - VAD detected speech start
            - {"type": "speech_stopped"} - VAD detected speech end
            - {"type": "response_done"} - Response complete
            - {"type": "error", "message": str} - Error occurred
        """
        if not self._connected or not self.ws:
            return

        try:
            async for message in self.ws:
                event = json.loads(message)
                event_type = event.get("type", "")

                # Audio delta - forward to client
                if event_type == "response.audio.delta":
                    audio_bytes = base64.b64decode(event.get("delta", ""))
                    yield {"type": "audio", "data": audio_bytes}

                # Audio transcript - agent's spoken text
                elif event_type == "response.audio_transcript.delta":
                    yield {
                        "type": "transcript",
                        "role": "assistant",
                        "text": event.get("delta", "")
                    }

                # Input audio transcript - user's spoken text
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    yield {
                        "type": "transcript",
                        "role": "user",
                        "text": event.get("transcript", "")
                    }

                # Function call - execute tool
                elif event_type == "response.function_call_arguments.done":
                    tool_result = await self._handle_tool_call(event)
                    if tool_result:
                        yield tool_result

                # VAD events
                elif event_type == "input_audio_buffer.speech_started":
                    yield {"type": "speech_started"}

                elif event_type == "input_audio_buffer.speech_stopped":
                    yield {"type": "speech_stopped"}

                # Response complete
                elif event_type == "response.done":
                    yield {"type": "response_done"}

                # Error
                elif event_type == "error":
                    error_msg = event.get("error", {}).get("message", "Unknown error")
                    logger.error(f"Realtime API error: {error_msg}")
                    yield {"type": "error", "message": error_msg}

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed: {e}")
            yield {"type": "error", "message": "Connection closed"}

    async def _handle_tool_call(self, event: dict) -> Optional[dict]:
        """Handle a function call from the Realtime API.

        Args:
            event: Function call event from Realtime API

        Returns:
            Rich content event to send to client, or None
        """
        call_id = event.get("call_id", "")
        name = event.get("name", "")
        arguments_str = event.get("arguments", "{}")

        try:
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError:
            arguments = {}

        logger.info(f"Tool call: {name}({arguments})")

        # Execute the tool handler if registered
        handler = self.tool_handlers.get(name)
        result = None

        if handler:
            try:
                result = await handler(**arguments)
            except Exception as e:
                logger.error(f"Tool handler error: {e}")
                result = {"error": str(e)}

        # Send tool result back to Realtime API
        if self.ws:
            tool_response = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(result or {})
                }
            }
            await self.ws.send(json.dumps(tool_response))

            # Trigger response generation after tool call
            await self.ws.send(json.dumps({"type": "response.create"}))

        # Return rich content for UI rendering
        if name in ["render_vocabulary", "render_pattern"]:
            return {
                "type": "rich_content",
                "tool": name,
                "data": result
            }

        return None

    async def disconnect(self) -> None:
        """Close the WebSocket connection."""
        if self.ws:
            await self.ws.close()
            self.ws = None
        self._connected = False

        if self._credential:
            await self._credential.close()
            self._credential = None

        logger.info("Disconnected from Realtime API")

    @property
    def is_connected(self) -> bool:
        """Check if connected to Realtime API."""
        return self._connected and self.ws is not None
