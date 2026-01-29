"""Pydantic schemas for helping phrases."""

from pydantic import BaseModel


class HelpingPhraseSchema(BaseModel):
    """Schema for helping phrase display and recognition."""

    phrase_key: str  # 'repeat', 'dont_understand', 'slower', 'example'
    phrase_text: str  # "Repite, por favor" (native language)
    english_meaning: str  # "Please repeat"
    usage_context: str | None = None  # When to use this phrase

    class Config:
        """Pydantic configuration."""

        from_attributes = True
