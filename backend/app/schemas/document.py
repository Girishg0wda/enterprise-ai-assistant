from pydantic import BaseModel
from datetime import datetime
from app.models.document import DocumentStatus

class DocumentResponse(BaseModel):
    id: int
    user_id: int
    filename: str
    file_size: int
    content_type: str
    extracted_text: str | None = None
    status: DocumentStatus
    error_message: str | None
    created_at: datetime

    class Config:
        from_attributes = True