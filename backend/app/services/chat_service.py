from sqlalchemy.orm import Session
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.conversation import ConversationCreate

def create_conversation(
    db: Session,
    user: User,
    conversation_data: ConversationCreate,
) -> Conversation:
    
    conversation_title = conversation_data.title if hasattr(conversation_data, 'title') else None

    db_conversation = Conversation(
        user_id=user.id,
        title=conversation_title
    )

    try:
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)
    except:
        db.rollback()
        raise
    return db_conversation

def get_user_conversations(db: Session, user: User) -> list[Conversation]:
    return(
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )