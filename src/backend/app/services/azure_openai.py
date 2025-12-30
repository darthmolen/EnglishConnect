"""Azure OpenAI service for AI-powered conversation with tool support."""

import json
import logging
from typing import Callable, Optional

from openai import AsyncAzureOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)

# Memori integration state (lazy initialization)
_memori = None
_memori_initialized = False
_client_registered = False


def _init_memori():
    """Initialize Memori if available (lazy, idempotent).

    Returns True if Memori is available, False otherwise.
    """
    global _memori, _memori_initialized

    if _memori_initialized:
        return _memori is not None

    _memori_initialized = True

    try:
        from app.services.memory_service import get_memori
        _memori = get_memori()
        logger.info("Memori v3 memory layer available")
        return True
    except Exception as e:
        logger.warning(f"Memori not available: {e}")
        _memori = None
        return False


def _register_client_with_memori(client):
    """Register LLM client with Memori for memory extraction.

    In Memori v3, clients must be registered to enable interception.
    Only registers once per client type.
    """
    global _client_registered

    if not _init_memori() or _client_registered:
        return

    try:
        _memori.llm.register(client)
        _client_registered = True
        logger.info("Azure OpenAI client registered with Memori")
    except Exception as e:
        logger.warning(f"Failed to register client with Memori: {e}")


def set_memory_context(user_id: Optional[str] = None, process_id: str = "conversation-agent"):
    """Set Memori context for the current user.

    Must be called before LLM requests to attribute memories to the user.

    Args:
        user_id: User identifier for memory attribution
        process_id: Process/agent identifier
    """
    if not _init_memori():
        return

    if user_id and _memori:
        _memori.attribution(entity_id=user_id, process_id=process_id)
        logger.debug(f"Memory context set: user={user_id}, process={process_id}")


def get_azure_client() -> AsyncAzureOpenAI:
    """Get configured Azure OpenAI client.

    Registers the client with Memori on first call for memory extraction.
    """
    settings = get_settings()
    client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )

    # Register with Memori for memory extraction (once per client type)
    _register_client_with_memori(client)

    return client


# Speak tool definition (shared between practice and lesson agents)
SPEAK_TOOL = {
    "type": "function",
    "function": {
        "name": "speak",
        "description": "Speak text aloud to the student using text-to-speech. Use this to make your responses audible. You can choose to speak in English or Spanish.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to speak aloud"
                },
                "language": {
                    "type": "string",
                    "enum": ["en", "es"],
                    "description": "Language of the text (en=English, es=Spanish)"
                },
                "voice": {
                    "type": "string",
                    "enum": ["speaker_a", "speaker_b", "speaker_c", "speaker_d", "speaker_e", "speaker_f"],
                    "description": "Voice to use (speaker_b is recommended for warm, friendly tone)"
                }
            },
            "required": ["text", "language"]
        }
    }
}

# Tool definitions for the free-form practice conversation agent
AGENT_TOOLS = [SPEAK_TOOL]

# Tool definitions for the structured lesson teacher agent
LESSON_AGENT_TOOLS = [
    SPEAK_TOOL,
    {
        "type": "function",
        "function": {
            "name": "advance_phase",
            "description": "Move to the next phase of the lesson or the next item within the current phase. Call this when the student has completed the current phase objective (e.g., repeated a vocabulary word correctly, answered a pattern question).",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Brief reason for advancing (e.g., 'student repeated word correctly', 'pattern practice complete')"
                    }
                },
                "required": ["reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_attempt",
            "description": "Record the student's attempt at a vocabulary word or pattern. Call this after evaluating their response.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_type": {
                        "type": "string",
                        "enum": ["vocab", "pattern"],
                        "description": "Type of item being practiced"
                    },
                    "correct": {
                        "type": "boolean",
                        "description": "Whether the student's attempt was correct"
                    }
                },
                "required": ["item_type", "correct"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_pattern",
            "description": "Jump to a specific pattern within the practice phase. Use this to announce pattern changes conversationally (e.g., 'Let's practice pattern 2 now!'). Can also be triggered when user clicks a pattern card.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern_index": {
                        "type": "integer",
                        "description": "Zero-based index of the pattern to practice (0 = first pattern, 1 = second, etc.)"
                    }
                },
                "required": ["pattern_index"]
            }
        }
    }
]


async def get_chat_completion(
    system_prompt: str,
    user_message: str,
    history: list[dict],
) -> str:
    """Get chat completion from Azure OpenAI (simple mode, no tools).

    Args:
        system_prompt: System message for the AI tutor
        user_message: Current user message
        history: Previous conversation messages

    Returns:
        AI response text
    """
    settings = get_settings()
    client = get_azure_client()

    # Build messages list
    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    # Call Azure OpenAI
    response = await client.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=messages,
        max_tokens=200,
        temperature=0.7,
    )

    return response.choices[0].message.content or ""


async def get_agent_response(
    system_prompt: str,
    user_message: str,
    history: list[dict],
    tool_handlers: dict[str, Callable],
    user_id: Optional[str] = None,
    tools: Optional[list[dict]] = None,
) -> dict:
    """Get response from conversation agent with tool calling support.

    The agent can call tools like speak() to control TTS. This function
    handles the tool calling loop until the agent produces a final response.

    Args:
        system_prompt: System message for the AI tutor
        user_message: Current user message
        history: Previous conversation messages
        tool_handlers: Dict mapping tool names to async handler functions
        user_id: Optional user ID for memory attribution (Memori)
        tools: Optional custom tool definitions (defaults to AGENT_TOOLS)

    Returns:
        Dict with:
            - text: The agent's text response
            - tool_calls: List of tool calls made (for logging/debugging)
            - tool_results: Results from tool executions
    """
    # Use provided tools or default to AGENT_TOOLS
    active_tools = tools if tools is not None else AGENT_TOOLS
    settings = get_settings()
    client = get_azure_client()

    # Set memory context for this user (if Memori is enabled)
    if user_id:
        set_memory_context(user_id=user_id, process_id="conversation-agent")

    # Build messages list
    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    tool_calls_made = []
    tool_results = []

    # === LOGGING: Request details ===
    logger.info("=" * 60)
    logger.info("CONVERSATION REQUEST")
    logger.info(f"  User message: {user_message}")
    logger.info(f"  History: {len(history)} messages")
    for i, h in enumerate(history):
        logger.info(f"    [{i}] {h['role']}: {h['content'][:80]}{'...' if len(h['content']) > 80 else ''}")
    logger.info(f"  System prompt: {len(system_prompt)} chars")
    logger.info("=" * 60)
    logger.info("FULL SYSTEM PROMPT:")
    logger.info("=" * 60)
    logger.info(system_prompt)
    logger.info("=" * 60)
    logger.info("END SYSTEM PROMPT")
    logger.info("-" * 60)

    # Tool calling loop
    max_iterations = 5  # Prevent infinite loops
    for iteration in range(max_iterations):
        logger.info(f"LLM call iteration {iteration + 1}")

        # Force tool call on first iteration, then let model decide
        # This ensures speak() is called at least once
        current_tool_choice = "required" if iteration == 0 else "auto"

        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=messages,
            tools=active_tools,
            tool_choice=current_tool_choice,
            max_tokens=300,
            temperature=0.7,
        )

        message = response.choices[0].message
        logger.info(f"  LLM response: content={message.content[:100] if message.content else 'None'}{'...' if message.content and len(message.content) > 100 else ''}")
        logger.info(f"  LLM tool_calls: {len(message.tool_calls) if message.tool_calls else 0}")

        # Check if the model wants to call tools
        if message.tool_calls:
            # Add assistant's response to messages
            messages.append(message)

            # Process each tool call
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                logger.info(f"  TOOL CALL: {tool_name}")
                logger.info(f"    args: {json.dumps(tool_args)[:200]}{'...' if len(json.dumps(tool_args)) > 200 else ''}")

                tool_calls_made.append({
                    "name": tool_name,
                    "arguments": tool_args
                })

                # Execute the tool
                if tool_name in tool_handlers:
                    try:
                        result = await tool_handlers[tool_name](**tool_args)

                        # Log result (with audio size, not content)
                        audio_size = len(result.get("audio_base64", "")) if result.get("audio_base64") else 0
                        logger.info(f"    result: success={result.get('spoken')}, audio_size={audio_size} chars")

                        tool_results.append({
                            "tool": tool_name,
                            "success": True,
                            "result": result
                        })
                        # Return minimal confirmation to LLM (don't include audio_base64)
                        llm_result = {k: v for k, v in result.items() if k != "audio_base64"}
                        tool_response = json.dumps({"status": "success", "result": llm_result})
                    except Exception as e:
                        logger.error(f"    result: FAILED - {e}")
                        tool_results.append({
                            "tool": tool_name,
                            "success": False,
                            "error": str(e)
                        })
                        tool_response = json.dumps({"status": "error", "error": str(e)})
                else:
                    logger.error(f"    result: UNKNOWN TOOL")
                    tool_results.append({
                        "tool": tool_name,
                        "success": False,
                        "error": f"Unknown tool: {tool_name}"
                    })
                    tool_response = json.dumps({"status": "error", "error": f"Unknown tool: {tool_name}"})

                # Add tool response to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_response
                })
        else:
            # No tool calls - we have the final response
            logger.info("=" * 60)
            logger.info("CONVERSATION COMPLETE")
            logger.info(f"  Final text: {message.content[:150] if message.content else 'None'}{'...' if message.content and len(message.content) > 150 else ''}")
            logger.info(f"  Tool calls made: {len(tool_calls_made)}")
            logger.info(f"  Tool results: {len(tool_results)}")
            logger.info("=" * 60)

            return {
                "text": message.content or "",
                "tool_calls": tool_calls_made,
                "tool_results": tool_results
            }

    # If we hit max iterations, return what we have
    return {
        "text": "[Agent exceeded maximum tool iterations]",
        "tool_calls": tool_calls_made,
        "tool_results": tool_results
    }
