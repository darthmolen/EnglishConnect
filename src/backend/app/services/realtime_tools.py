"""Tool definitions for Azure OpenAI Realtime API.

The Realtime API handles TTS natively, so we don't need a 'speak' tool.
Instead, the agent speaks by returning text which is automatically converted to audio.

Tools here are for:
- Retrieving teaching content
- Recording student attempts
- Rendering rich UI content (vocabulary cards, patterns)
"""

from typing import Any

# Tool definitions in Realtime API format
REALTIME_TOOLS = [
    {
        "type": "function",
        "name": "get_teaching_help",
        "description": "Retrieve additional teaching content when the student struggles with a concept. Returns helpful explanations, examples, or tips.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What the student is struggling with or needs help understanding"
                }
            },
            "required": ["query"]
        }
    },
    {
        "type": "function",
        "name": "record_attempt",
        "description": "Record a student's attempt at pronunciation or grammar. Used to track progress and identify areas for improvement.",
        "parameters": {
            "type": "object",
            "properties": {
                "expected": {
                    "type": "string",
                    "description": "The expected correct phrase or word"
                },
                "actual": {
                    "type": "string",
                    "description": "What the student actually said"
                },
                "is_correct": {
                    "type": "boolean",
                    "description": "Whether the attempt was correct"
                },
                "feedback": {
                    "type": "string",
                    "description": "Brief feedback about the attempt"
                }
            },
            "required": ["expected", "actual", "is_correct"]
        }
    },
    {
        "type": "function",
        "name": "render_vocabulary",
        "description": "Display a vocabulary card in the UI with the English word, Spanish translation, and audio playback button.",
        "parameters": {
            "type": "object",
            "properties": {
                "english_word": {
                    "type": "string",
                    "description": "The English vocabulary word to display"
                }
            },
            "required": ["english_word"]
        }
    },
    {
        "type": "function",
        "name": "render_pattern",
        "description": "Display a conversation pattern card in the UI showing the question template and answer template.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern_number": {
                    "type": "integer",
                    "description": "The pattern number from the lesson (1-based)"
                }
            },
            "required": ["pattern_number"]
        }
    }
]


def get_tool_definitions() -> list[dict[str, Any]]:
    """Get tool definitions for Realtime API session configuration."""
    return REALTIME_TOOLS
