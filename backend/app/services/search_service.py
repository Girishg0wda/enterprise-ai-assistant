import logging
from typing import List
from app.services.embedding_service import embedding_service
from app.services.vector_service import vector_service
from app.schemas.search import VectorSearchResult

logger = logging.getLogger(__name__)

class SearchService:
    def search_similar_chunks(self, query_text: str, user_id: int, user_role: str, limit: int = 5) -> List[VectorSearchResult]:
        if not query_text or not query_text.strip():
            return []

        logger.info(f"Processing hybrid retrieval match for query: '{query_text}' with Role Clearance: '{user_role}'")
        
        # 1. Extract standard query embedding coordinates
        query_vector = embedding_service.generate_query_embedding(query_text)
        
        # 2. 🛡️ Pass the session user role to the hybrid engine to filter search matches
        return vector_service.hybrid_search(
            dense_vector=query_vector, 
            query_text=query_text, 
            user_id=user_id, 
            user_role=user_role,  # 🚀 Security injection
            limit=limit
        )

search_service = SearchService()