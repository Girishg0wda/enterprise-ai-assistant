import logging
import uuid
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from app.core.config import settings
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

class SemanticMemoryService:
    def __init__(self):
        self.client = QdrantClient(host=settings.QDRANT_HOST, port=6333)
        self.collection_name = "long_term_memory"
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        try:
            if not self.client.collection_exists(self.collection_name):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=settings.EMBEDDING_DIMENSION, distance=Distance.COSINE),
                )
                logger.info(f"Initialized long-term vector memory layer index: '{self.collection_name}'")
        except Exception as e:
            logger.error(f"Failed configuring semantic memory vector index: {str(e)}")

    def store_memory_turn(self, user_id: int, conversation_id: int, user_msg: str, assistant_msg: str):
        """Compiles a text-turn block, generates embeddings, and vectors it directly to Qdrant."""
        try:
            memory_text = f"User asked: {user_msg}\nAssistant responded: {assistant_msg}"
            
            # 🚀 FIXED: Calling the correct method signature from EmbeddingService
            memory_vector = embedding_service.generate_query_embedding(memory_text)
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=memory_vector,
                        payload={
                            "user_id": user_id,
                            "conversation_id": conversation_id,
                            "content": memory_text,
                            "type": "chat_memory"
                        }
                    )
                ]
            )
            logger.info(f"🧠 [Semantic Memory Engine] Logged historical vector turn context for Conversation {conversation_id}")
        except Exception as e:
            logger.error(f"Failed upserting semantic turn context block: {str(e)}")

    def recall_relevant_memories(self, user_id: int, query_text: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Queries historical interactions filtered strictly by the tenant user boundary."""
        try:
            # 🚀 FIXED: Calling the correct method signature from EmbeddingService
            query_vector = embedding_service.generate_query_embedding(query_text)
            user_filter = Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))])
            
            # 🚀 SECURE PATCH: Utilizing query_points to completely align client libraries
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=user_filter,
                limit=limit
            )
            results = response.points
            
            # Filter matches using a baseline distance threshold filter
            return [{"content": hit.payload["content"], "score": hit.score} for hit in results if hit.score >= 0.70]
        except Exception as e:
            logger.error(f"Failed searching semantic conversation memory space: {str(e)}")
            return []

semantic_memory_service = SemanticMemoryService()