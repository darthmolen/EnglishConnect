"""Azure OpenAI service for AI-powered conversation."""

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


async def get_chat_completion(
    system_prompt: str,
    user_message: str,
    history: list[dict],
) -> str:
    """Get chat completion from Azure OpenAI.

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
