import logging
from datetime import datetime
from sqlalchemy.orm import Session
from typing import List, Dict

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.conversation import ConversationCreate
from app.schemas.message import MessageCreate
from app.services.prompt_service import prompt_service 

logger = logging.getLogger(__name__)

def create_conversation(db: Session, user: User, conversation_data: ConversationCreate) -> Conversation:
    db_conversation = Conversation(user_id=user.id, title=conversation_data.title)
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    return db_conversation

def get_user_conversations(db: Session, user: User) -> list[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )

def save_raw_db_message(db: Session, conversation_id: int, role: str, content: str) -> Message:
    """Helper utility to save an incoming or inferred message securely to Postgres."""
    token_est = max(1, len(content.split()))
    db_msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        token_count=token_est
    )
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)
    return db_msg

def get_sliding_window_history(db: Session, conversation_id: int, limit: int = 10) -> List[Dict[str, str]]:
    """
    🚀 Core Phase 1 Memory Rule:
    Pull the last 10 messages DESCENDING, then reverse them chronologically 
    so the oldest of the 10 comes first in the LLM prompt context payload.
    """
    recent_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )

    # Reverse back to maintain proper temporal conversation flow
    chronological_messages = reversed(recent_messages)

    formatted_history = []
    total_characters = 0
    for msg in chronological_messages:
        formatted_history.append({"role": msg.role, "content": msg.content})
        total_characters += len(msg.content)

    # 📊 Measure prompt history memory size in logs (Rule 4)
    logger.info(
        f"📊 [Memory Matrix] Bounded sliding window extracted {len(formatted_history)} records. "
        f"Estimated history segment payload weight: ~{total_characters // 4} tokens."
    )
    return formatted_history