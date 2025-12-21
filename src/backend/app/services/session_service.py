"""Session service for tracking conversation sessions and exchanges.

Stores conversation data for evaluation and analysis purposes.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.progress import PracticeSession, ConversationExchange

logger = logging.getLogger(__name__)


class SessionService:
    """Service for managing practice sessions and conversation exchanges."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_session(
        self,
        user_id: Optional[UUID],
        lesson_id: int,
        session_type: str = "conversation_practice",
    ) -> PracticeSession:
        """Get active session or create a new one.

        An active session is one that started within the last 30 minutes
        and hasn't ended.

        Args:
            user_id: User UUID (None for anonymous)
            lesson_id: Current lesson ID
            session_type: Type of practice session

        Returns:
            PracticeSession instance
        """
        # For now, always create a new session
        # TODO: Implement session continuity logic
        session = PracticeSession(
            user_id=user_id,
            lesson_id=lesson_id,
            session_type=session_type,
            started_at=datetime.utcnow(),
            exchanges_count=0,
        )
        self.db.add(session)
        await self.db.flush()  # Get the ID
        logger.info(f"Created new session {session.id} for lesson {lesson_id}")
        return session

    async def record_exchange(
        self,
        session_id: int,
        agent_utterance: str,
        user_utterance: str,
        transcription_confidence: Optional[float] = None,
        pronunciation_feedback: Optional[dict] = None,
        grammar_feedback: Optional[dict] = None,
    ) -> ConversationExchange:
        """Record a conversation exchange.

        Args:
            session_id: Practice session ID
            agent_utterance: What the agent said
            user_utterance: What the user said
            transcription_confidence: STT confidence score
            pronunciation_feedback: Pronunciation analysis
            grammar_feedback: Grammar analysis

        Returns:
            ConversationExchange instance
        """
        # Get next sequence number
        result = await self.db.execute(
            select(func.coalesce(func.max(ConversationExchange.sequence_number), 0))
            .where(ConversationExchange.session_id == session_id)
        )
        max_seq = result.scalar() or 0

        exchange = ConversationExchange(
            session_id=session_id,
            sequence_number=max_seq + 1,
            agent_utterance=agent_utterance,
            user_utterance=user_utterance,
            transcription_confidence=transcription_confidence,
            pronunciation_feedback=pronunciation_feedback,
            grammar_feedback=grammar_feedback,
            created_at=datetime.utcnow(),
        )
        self.db.add(exchange)

        # Update session exchange count
        result = await self.db.execute(
            select(PracticeSession).where(PracticeSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            session.exchanges_count = max_seq + 1

        await self.db.flush()
        logger.debug(f"Recorded exchange {exchange.id} in session {session_id}")
        return exchange

    async def end_session(self, session_id: int) -> Optional[PracticeSession]:
        """End a practice session.

        Args:
            session_id: Session to end

        Returns:
            Updated PracticeSession or None
        """
        result = await self.db.execute(
            select(PracticeSession).where(PracticeSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if session:
            session.ended_at = datetime.utcnow()
            if session.started_at:
                session.duration_seconds = int(
                    (session.ended_at - session.started_at).total_seconds()
                )
            await self.db.flush()
            logger.info(f"Ended session {session_id}, duration: {session.duration_seconds}s")

        return session

    async def get_session_exchanges(
        self,
        session_id: int,
    ) -> list[ConversationExchange]:
        """Get all exchanges for a session.

        Args:
            session_id: Session ID

        Returns:
            List of ConversationExchange instances
        """
        result = await self.db.execute(
            select(ConversationExchange)
            .where(ConversationExchange.session_id == session_id)
            .order_by(ConversationExchange.sequence_number)
        )
        return list(result.scalars().all())
