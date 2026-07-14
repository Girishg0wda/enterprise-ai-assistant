import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.conversation import ConversationCreate

logger = logging.getLogger(__name__)

class ConversationService:
    def create_conversation(self, db: Session, user_id: int, conversation_data: ConversationCreate) -> Conversation:
        db_conversation = Conversation(user_id=user_id, title=conversation_data.title)
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)
        return db_conversation

    def get_user_conversations(self, db: Session, user_id: int) -> list[Conversation]:
        return (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .all()
        )

    def save_message(self, db: Session, conversation_id: int, user_id: int, role: str, content: str) -> Message:
        """Saves message strings after verifying security isolation boundaries."""
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()

        if not conversation:
            logger.error(f"Security multi-tenancy violation check failed for Conversation ID {conversation_id}")
            raise PermissionError("Unauthorized access to requested conversation pool container.")

        token_est = max(1, len(content.split()))
        db_msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            token_count=token_est
        )
        db.add(db_msg)
        
        # Advance thread update timestamp tracker
        conversation.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_msg)
        return db_msg

conversation_service = ConversationService()