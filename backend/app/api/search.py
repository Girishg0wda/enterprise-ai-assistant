from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database.base import get_db
from app.models.user import User
from app.api.auth import get_current_user
from app.services.search_service import search_service
from app.schemas.search import VectorSearchResult # 🚀 Import the typed schema

router = APIRouter(prefix="/search", tags=["Semantic Search"])

# 🚀 Update response_model to match your Pydantic schema class type perfectly
@router.get("", response_model=List[VectorSearchResult])
def semantic_document_search(
    query: str = Query(..., description="The search string or question to answer"),
    limit: int = Query(5, description="Number of context slices to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exposes semantic vector search across your uploaded documents.
    Enforces user isolation via secure background matching.
    """
    try:
        results = search_service.search_similar_chunks(
            query_text=query,
            user_id=current_user.id,
            limit=limit
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))