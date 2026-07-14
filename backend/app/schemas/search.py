from pydantic import BaseModel
from typing import Optional

class VectorSearchResult(BaseModel):
    chunk_id: int
    score: float
    document_id: Optional[int] = None
    document_name: str
    chunk_index: int
    content: Optional[str] = None