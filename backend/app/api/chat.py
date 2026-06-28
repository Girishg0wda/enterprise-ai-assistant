from fastapi import APIRouter, Depends, status
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
    get_user_conversations
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