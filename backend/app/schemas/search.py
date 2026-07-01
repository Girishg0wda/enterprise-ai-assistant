from pydantic import BaseModel
from typing import Optional

class VectorSearchResult(BaseModel):
    chunk_id: int
    score: float
    document_id: Optional[int] = None
    content: Optional[str] = None