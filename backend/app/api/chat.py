from fastapi import APIRouter, Depends, status, HTTPException  
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
)
from app.services.chat_service import (
    create_conversation,
    get_user_conversations,
    create_message_in_conversation
)
from app.schemas.message import (
    MessageCreate,
    MessageResponse
)


router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_conversation(
    conversation: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_conversation(
        db=db,
        user=current_user,
        conversation_data=conversation,
    )


@router.get(
    "/conversations",
    response_model=list[ConversationResponse],
    status_code=status.HTTP_200_OK
)
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
): 
    return get_user_conversations(
        db=db, 
        user=current_user
    )

@router.post(
    "/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED
)
def send_message(
    message_input: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
   
    new_message = create_message_in_conversation(
        db=db,
        user=current_user,
        message_data=message_input,
        role="user"
    )

    if not new_message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    return new_message