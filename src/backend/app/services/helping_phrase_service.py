"""Service for helping phrases CRUD and lookup.

Helping phrases allow students to request assistance during practice
in their native language (e.g., "No entiendo" in Spanish).
"""

from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import HelpingPhrase
from app.schemas.helping_phrase import HelpingPhraseSchema


class HelpingPhraseService:
    """Service for helping phrase operations."""

    def __init__(self, db: AsyncSession):
        """Initialize the service with a database session.

        Args:
            db: Async SQLAlchemy session
        """
        self.db = db

    async def get_phrases_for_language(
        self, language_code: str
    ) -> list[HelpingPhraseSchema]:
        """Get all helping phrases for a language, ordered by display_order.

        Args:
            language_code: Language code (e.g., 'es', 'en')

        Returns:
            List of HelpingPhraseSchema objects
        """
        query = (
            select(HelpingPhrase)
            .where(HelpingPhrase.language_code == language_code)
            .order_by(HelpingPhrase.display_order)
        )
        result = await self.db.execute(query)
        phrases = result.scalars().all()

        return [
            HelpingPhraseSchema(
                phrase_key=p.phrase_key,
                phrase_text=p.phrase_text,
                english_meaning=p.english_meaning,
                usage_context=p.usage_context,
            )
            for p in phrases
        ]

    async def match_help_request(
        self, user_input: str, language_code: str, threshold: float = 0.7
    ) -> HelpingPhraseSchema | None:
        """Detect if user input contains a help phrase.

        Uses fuzzy matching to handle STT errors:
        - 'repite por favor' matches 'repeat'
        - 'no entiendo' matches 'dont_understand'
        - 'no en tiendo' (STT error) should still match

        Args:
            user_input: User's transcribed input
            language_code: Language code to match against
            threshold: Similarity threshold (0-1) for fuzzy matching

        Returns:
            Matching HelpingPhraseSchema or None if no match
        """
        if not user_input:
            return None

        # Get all phrases for the language
        phrases = await self.get_phrases_for_language(language_code)

        if not phrases:
            return None

        # Normalize input for matching
        normalized_input = self._normalize(user_input)

        best_match = None
        best_score = 0.0

        for phrase in phrases:
            normalized_phrase = self._normalize(phrase.phrase_text)

            # Check for exact substring match first
            if normalized_phrase in normalized_input:
                return phrase

            # Fuzzy match using SequenceMatcher
            score = SequenceMatcher(None, normalized_input, normalized_phrase).ratio()

            # Also check if input is a significant substring
            if len(normalized_phrase) > 3 and normalized_phrase[:4] in normalized_input:
                score = max(score, 0.75)  # Boost for prefix match

            if score > best_score and score >= threshold:
                best_score = score
                best_match = phrase

        return best_match

    def _normalize(self, text: str) -> str:
        """Normalize text for comparison.

        - Lowercase
        - Remove punctuation
        - Collapse whitespace

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        import re

        # Lowercase and remove punctuation
        text = text.lower()
        text = re.sub(r"[^\w\s]", "", text)
        # Collapse whitespace
        text = " ".join(text.split())
        return text
