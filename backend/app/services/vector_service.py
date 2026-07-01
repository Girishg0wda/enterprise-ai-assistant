import logging
from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from app.core.config import settings
from app.schemas.search import VectorSearchResult

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self):
        logger.info(f"Connecting client layer to Qdrant cluster: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
        self.client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        self.collection_name = settings.QDRANT_COLLECTION

    def create_collection(self):
        """Explicitly invoked once during application startup event loop."""
        try:
            if not self.client.collection_exists(collection_name=self.collection_name):
                logger.info(f"Initializing collection '{self.collection_name}' with dimension scale {settings.EMBEDDING_DIMENSION}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=settings.EMBEDDING_DIMENSION, 
                        distance=Distance.COSINE
                    )
                )
        except Exception as e:
            logger.error(f"Critical initialization failure on Qdrant cluster: {str(e)}")
            raise e

    def upsert_embeddings(self, points_data: List[dict]) -> bool:
        try:
            points = [
                PointStruct(
                    id=item["chunk_id"],
                    vector=item["vector"],
                    payload={
                        "document_id": item["document_id"],
                        "user_id": item["user_id"],
                        "content": item["content"]
                    }
                )
                for item in points_data
            ]
            self.client.upsert(collection_name=self.collection_name, wait=True, points=points)
            return True
        except Exception as e:
            logger.error(f"Failed inserting point mappings into vector cluster: {str(e)}")
            raise RuntimeError(f"Vector storage driver exception: {str(e)}")

    def search(self, query_vector: List[float], user_id: int, document_ids: Optional[List[int]] = None, limit: int = 5) -> List[VectorSearchResult]:
        """Performs robust similarity searches, supporting future document scoped filters."""
        try:
            conditions = [FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            
            # Future Proofing: Filter by specific document subsets if passed down
            if document_ids:
                from qdrant_client.models import MatchAny
                conditions.append(FieldCondition(key="document_id", match=MatchAny(any=document_ids)))

            user_security_filter = Filter(must=conditions)

            search_results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=user_security_filter,
                limit=limit
            )

            return [
                VectorSearchResult(
                    chunk_id=hit.id,
                    score=hit.score,
                    document_id=hit.payload.get("document_id") if hit.payload else None,
                    content=hit.payload.get("content") if hit.payload else None
                )
                for hit in search_results.points
            ]
        except Exception as e:
            logger.error(f"Raw vector indexing lookup exception: {str(e)}")
            raise RuntimeError(f"Vector search calculation failure: {str(e)}")

vector_service = VectorService()