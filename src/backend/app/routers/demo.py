"""Demo conversation API router for playing pre-recorded examples."""

import base64
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.services.lesson_service import LessonService
from app.services.azure_openai import get_agent_response, SPEAK_TOOL
from app.services.tool_handlers import speak_tool_handler
from app.agents.demo_agent import DemoAgent
from app.config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/demo", tags=["demo"])

# Path to audio content
AUDIO_BASE = (
    Path(__file__).parent.parent.parent.parent.parent
    / "content"
    / "audio"
)


class DemoConversationRequest(BaseModel):
    """Request for demo conversation."""

    message: str
    lesson_number: int
    history: list[dict] = []


class DemoConversationResponse(BaseModel):
    """Response from demo conversation."""

    text: str
    lesson_number: int
    audio_base64: str | None = None
    audio_format: str = "wav"
    language: str = "en"
    demo_played: int | None = None  # Index of demo that was played, if any


# Tool definition for playing demo audio
PLAY_DEMO_TOOL = {
    "type": "function",
    "function": {
        "name": "play_demo",
        "description": "Play a pre-recorded demo audio file for the student. Use this to play conversation examples.",
        "parameters": {
            "type": "object",
            "properties": {
                "demo_index": {
                    "type": "integer",
                    "description": "The index of the demo to play (0-based)"
                }
            },
            "required": ["demo_index"]
        }
    }
}

# Tools available to demo agent
DEMO_AGENT_TOOLS = [SPEAK_TOOL, PLAY_DEMO_TOOL]


async def _load_demo_metadata(course_id: str, lesson_number: int) -> list[dict]:
    """Load demo metadata for a lesson.

    Args:
        course_id: Course identifier (e.g., 'ec1')
        lesson_number: Lesson number

    Returns:
        List of demo metadata dicts
    """
    import glob
    import json

    demos_dir = AUDIO_BASE / course_id / "demos" / f"lesson-{lesson_number:02d}"
    if not demos_dir.exists():
        return []

    demos = []
    for meta_path in glob.glob(str(demos_dir / "*.json")):
        try:
            with open(meta_path) as f:
                meta = json.load(f)
            # Add audio file path
            audio_path = Path(meta_path).with_suffix(".wav")
            meta["audio_path"] = str(audio_path)
            demos.append(meta)
        except Exception:
            continue

    # Sort by pattern_number, example_index
    demos.sort(key=lambda d: (
        d.get("pattern_number", 0),
        d.get("example_index", 0),
    ))

    return demos


def _create_play_demo_handler(demos: list[dict]):
    """Create a play_demo tool handler with access to demo metadata.

    Args:
        demos: List of demo metadata

    Returns:
        Async handler function for play_demo tool
    """
    async def play_demo_handler(demo_index: int) -> dict:
        """Handle play_demo tool calls.

        Args:
            demo_index: Index of demo to play (0-based)

        Returns:
            Dict with success status and audio data
        """
        if demo_index < 0 or demo_index >= len(demos):
            return {
                "played": False,
                "error": f"Invalid demo index: {demo_index}. Available: 0-{len(demos)-1}"
            }

        demo = demos[demo_index]
        audio_path = Path(demo["audio_path"])

        if not audio_path.exists():
            return {
                "played": False,
                "error": f"Demo audio file not found: {audio_path}"
            }

        try:
            # Read and encode audio file
            with open(audio_path, "rb") as f:
                audio_data = f.read()
            audio_base64 = base64.b64encode(audio_data).decode("utf-8")

            return {
                "played": True,
                "demo_index": demo_index,
                "pattern_number": demo.get("pattern_number"),
                "example_index": demo.get("example_index"),
                "duration_seconds": demo.get("duration_seconds", 0),
                "audio_base64": audio_base64,
                "format": "wav",
                "sample_rate": demo.get("sample_rate", 24000),
            }
        except Exception as e:
            logger.error(f"Failed to load demo audio: {e}")
            return {
                "played": False,
                "error": str(e)
            }

    return play_demo_handler


@router.post("/conversation", response_model=DemoConversationResponse)
async def demo_conversation(
    request: DemoConversationRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Process a demo conversation message.

    The demo agent plays pre-recorded audio examples and can answer
    basic questions about the patterns and vocabulary.

    Args:
        request: DemoConversationRequest with message and lesson_number
        current_user: Authenticated user
        db: Database session dependency

    Returns:
        DemoConversationResponse with audio and state

    Raises:
        HTTPException: 404 if lesson not found or no demos available
    """
    # Get lesson details
    lesson_service = LessonService(db)
    lesson = await lesson_service.get_lesson_detail("ec1", request.lesson_number)

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Load demo metadata
    demos = await _load_demo_metadata("ec1", request.lesson_number)
    if not demos:
        raise HTTPException(
            status_code=404,
            detail="No demo audio available for this lesson"
        )

    # Build the demo agent
    agent = DemoAgent(lesson=lesson, demo_metadata=demos)
    system_prompt = agent.build_system_prompt()

    # Check if Azure OpenAI is configured
    settings = get_settings()
    if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
        return DemoConversationResponse(
            text=f"[Azure OpenAI not configured - Lesson {request.lesson_number}]",
            lesson_number=request.lesson_number,
        )

    # Create tool handlers
    play_demo_handler = _create_play_demo_handler(demos)
    tool_handlers = {
        "speak": speak_tool_handler,
        "play_demo": play_demo_handler,
    }

    # Call the agent
    history = [{"role": m["role"], "content": m["content"]} for m in request.history]

    agent_result = await get_agent_response(
        system_prompt=system_prompt,
        user_message=request.message,
        history=history,
        tool_handlers=tool_handlers,
        user_id=str(current_user.id),
        tools=DEMO_AGENT_TOOLS,
    )

    # Extract audio from tool results
    audio_base64 = None
    audio_format = "wav"
    language = "en"
    demo_played = None
    response_text = agent_result["text"]

    for tool_result in agent_result.get("tool_results", []):
        if tool_result.get("success"):
            result_data = tool_result.get("result", {})

            if tool_result.get("tool") == "play_demo" and result_data.get("played"):
                # Demo audio takes priority
                audio_base64 = result_data.get("audio_base64")
                audio_format = result_data.get("format", "wav")
                demo_played = result_data.get("demo_index")
                language = "en"  # Demo audio is always English

            elif tool_result.get("tool") == "speak" and result_data.get("spoken"):
                # Only use speak audio if no demo was played
                if audio_base64 is None:
                    audio_base64 = result_data.get("audio_base64")
                    audio_format = result_data.get("format", "wav")
                    language = result_data.get("language", "en")
                    response_text = result_data.get("text", response_text)

    return DemoConversationResponse(
        text=response_text,
        lesson_number=request.lesson_number,
        audio_base64=audio_base64,
        audio_format=audio_format,
        language=language,
        demo_played=demo_played,
    )


@router.get("/metadata/{course_id}/{lesson_number}")
async def get_demo_metadata(
    course_id: str,
    lesson_number: int,
    current_user: CurrentUser,
) -> list[dict]:
    """Get demo metadata for a lesson.

    Args:
        course_id: Course identifier (e.g., 'ec1')
        lesson_number: Lesson number
        current_user: Authenticated user

    Returns:
        List of demo metadata (without audio data)
    """
    demos = await _load_demo_metadata(course_id, lesson_number)

    # Remove audio_path from response for security
    return [
        {k: v for k, v in demo.items() if k != "audio_path"}
        for demo in demos
    ]
