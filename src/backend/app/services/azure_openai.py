"""Azure OpenAI service for AI-powered conversation with tool support."""

import json
from typing import Callable

from openai import AsyncAzureOpenAI

from app.config import get_settings


def get_azure_client() -> AsyncAzureOpenAI:
    """Get configured Azure OpenAI client."""
    settings = get_settings()
    return AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )


# Tool definitions for the conversation agent
AGENT_TOOLS = [
    {
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
) -> dict:
    """Get response from conversation agent with tool calling support.

    The agent can call tools like speak() to control TTS. This function
    handles the tool calling loop until the agent produces a final response.

    Args:
        system_prompt: System message for the AI tutor
        user_message: Current user message
        history: Previous conversation messages
        tool_handlers: Dict mapping tool names to async handler functions

    Returns:
        Dict with:
            - text: The agent's text response
            - tool_calls: List of tool calls made (for logging/debugging)
            - tool_results: Results from tool executions
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

    tool_calls_made = []
    tool_results = []

    # Tool calling loop
    max_iterations = 5  # Prevent infinite loops
    for _ in range(max_iterations):
        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=messages,
            tools=AGENT_TOOLS,
            tool_choice="auto",
            max_tokens=300,
            temperature=0.7,
        )

        message = response.choices[0].message

        # Check if the model wants to call tools
        if message.tool_calls:
            # Add assistant's response to messages
            messages.append(message)

            # Process each tool call
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                tool_calls_made.append({
                    "name": tool_name,
                    "arguments": tool_args
                })

                # Execute the tool
                if tool_name in tool_handlers:
                    try:
                        result = await tool_handlers[tool_name](**tool_args)
                        tool_results.append({
                            "tool": tool_name,
                            "success": True,
                            "result": result
                        })
                        tool_response = json.dumps({"status": "success", "result": result})
                    except Exception as e:
                        tool_results.append({
                            "tool": tool_name,
                            "success": False,
                            "error": str(e)
                        })
                        tool_response = json.dumps({"status": "error", "error": str(e)})
                else:
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
