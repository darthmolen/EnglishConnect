"""Prompt loading and template rendering utilities.

Loads prompts from .md files and renders them with context variables.
This allows prompts to be edited as human-readable markdown files and
shared between production code and tests.
"""

import re
from pathlib import Path
from functools import lru_cache

PROMPTS_DIR = Path(__file__).parent


@lru_cache(maxsize=32)
def load_prompt(path: str) -> str:
    """Load prompt template from .md file.

    Args:
        path: Relative path from prompts directory (e.g., "teacher/base.md")

    Returns:
        Raw prompt template string

    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    prompt_path = PROMPTS_DIR / path
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def render_prompt(template: str, **context) -> str:
    """Render prompt template with context variables.

    Uses {variable_name} placeholder syntax. Placeholders not found in
    context are left unchanged (useful for partial rendering).

    Args:
        template: Prompt template string with {placeholders}
        **context: Variable values to substitute

    Returns:
        Rendered prompt string

    Example:
        >>> render_prompt("Hello {name}!", name="World")
        'Hello World!'
    """
    result = template
    for key, value in context.items():
        placeholder = "{" + key + "}"
        result = result.replace(placeholder, str(value))
    return result


def load_and_render(path: str, **context) -> str:
    """Load prompt and render it with context in one call.

    Convenience function combining load_prompt and render_prompt.

    Args:
        path: Relative path from prompts directory
        **context: Variable values to substitute

    Returns:
        Rendered prompt string
    """
    template = load_prompt(path)
    return render_prompt(template, **context)


def clear_cache() -> None:
    """Clear the prompt loading cache.

    Useful for testing or when prompt files are updated at runtime.
    """
    load_prompt.cache_clear()
