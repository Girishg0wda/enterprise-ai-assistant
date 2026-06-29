from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class MessageCreate(BaseModel):
    conversation_id: int = Field(..., description="The ID of the conversation thread")
    content: str = Field(..., min_length=1, description="The textual content of the message")

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    token_count: int
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )