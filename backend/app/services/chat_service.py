from datetime import datetime
from sqlalchemy.orm import Session
from pprint import pprint

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.conversation import ConversationCreate
from app.schemas.message import MessageCreate
from app.services.llm_service import llm_service
from backend.app.services.prompt_service import prompt_builder  


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

def create_message_in_conversation(
    db: Session,
    user: User,
    message_data: MessageCreate,
    role: str = "user"
) -> Message:
    # 1. Isolation boundary validation
    conversation = db.query(Conversation).filter(
        Conversation.id == message_data.conversation_id,
        Conversation.user_id == user.id
    ).first()

    if not conversation:
        return None  

    # 2. Persistent logging of user message
    user_token_est = len(message_data.content.split())
    db_user_message = Message(
        conversation_id=message_data.conversation_id,
        role="user",
        content=message_data.content,
        token_count=max(1, user_token_est)
    )
    db.add(db_user_message)
    
    # 3. Pull historical context
    history = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
        .all()
    )

    # 4. Extract raw conversational log array
    history_payload = [{"role": msg.role, "content": msg.content} for msg in history]
    if not any(m["content"] == message_data.content for m in history_payload):
        history_payload.append({"role": "user", "content": message_data.content})

    # 5. Delegate prompt building to the specialized builder layer
    # We pass the user's name from current_user directly into the system template
    llm_payload = prompt_builder.build_chat_messages(
        history_messages=history_payload,
        user_name=getattr(user, "username", "User")
    )
    print("\n========== LLM PAYLOAD ==========")
    pprint(llm_payload)
    print("=================================\n")
    # 6. Fire execution over to Groq
    llm_result = llm_service.generate_response(messages=llm_payload)

    # 7. Write AI record back to persistence
    db_assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=llm_result["content"],
        token_count=llm_result["completion_tokens"]
    )
    db.add(db_assistant_message)

    # 8. Advance timestamp milestone
    conversation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_assistant_message)

    return db_assistant_message