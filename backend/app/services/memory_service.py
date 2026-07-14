import logging
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.message import Message

logger = logging.getLogger(__name__)

class MemoryService:
    def get_sliding_window_history(self, db: Session, conversation_id: int, limit: int = 10) -> List[Dict[str, str]]:
        """
        🚀 Single Responsibility: Bounded Sliding Window Management.
        Extracts the last N historical records DESC, then flips them chronologically.
        """
        recent_messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .all()
        )

        # Reverse back to maintain proper chronological conversation context flow
        chronological_messages = reversed(recent_messages)

        formatted_history = []
        total_characters = 0
        for msg in chronological_messages:
            formatted_history.append({"role": msg.role, "content": msg.content})
            total_characters += len(msg.content)

        # Telemetry log metric size profiles
        logger.info(
            f"📊 [Memory Matrix] Bounded context sliding window extracted {len(formatted_history)} messages. "
            f"Estimated history block payload size: ~{total_characters // 4} tokens."
        )
        return formatted_history

memory_service = MemoryService()