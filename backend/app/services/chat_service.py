from datetime import datetime
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.conversation import ConversationCreate
from app.schemas.message import MessageCreate  # Verified Schema Import

def create_conversation(
    db: Session,
    user: User,
    conversation_data: ConversationCreate,
) -> Conversation:
    db_conversation = Conversation(
        user_id=user.id,
        title=conversation_data.title
    )

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


def create_message_in_conversation(
    db: Session,
    user: User,
    message_data: MessageCreate,  # Adjusted to match incoming payload schema object
    role: str = "user"
) -> Message:
    # Query validates both the existence and the ownership of the thread
    conversation = db.query(Conversation).filter(
        Conversation.id == message_data.conversation_id,
        Conversation.user_id == user.id
    ).first()

    if not conversation:
        return None  
        
    approx_token_count = len(message_data.content.split())

    db_message = Message(
        conversation_id=message_data.conversation_id,
        role=role,
        content=message_data.content,
        token_count=max(1, approx_token_count)
    )

    # Bump conversation updated_at milestone
    conversation.updated_at = datetime.utcnow()
    
    db.add(conversation)
    db.add(db_message)
    db.commit()
    db.refresh(db_message)

    return db_message