import logging
from typing import List
from app.services.embedding_service import embedding_service
from app.services.vector_service import vector_service
from app.schemas.search import VectorSearchResult

logger = logging.getLogger(__name__)

class SearchService:
    def search_similar_chunks(self, query_text: str, user_id: int, limit: int = 5) -> List[VectorSearchResult]:
        if not query_text or not query_text.strip():
            return []

        logger.info(f"Processing retrieval match for question: '{query_text}'")
        
        # 🚀 Consuming your clean, future-proof query embedding interface!
        query_vector = embedding_service.generate_query_embedding(query_text)
        
        # Delegate clean searching to your single-responsibility service
        return vector_service.search(query_vector=query_vector, user_id=user_id, limit=limit)

search_service = SearchService()