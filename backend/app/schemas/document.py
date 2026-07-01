from pydantic import BaseModel
from datetime import datetime

class DocumentResponse(BaseModel):
    id: int
    user_id: int
    filename: str
    file_size: int
    content_type: str
    extracted_text: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True