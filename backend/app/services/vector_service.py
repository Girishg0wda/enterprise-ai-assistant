import logging
from typing import List, Optional, Generator
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, 
    MatchValue, MatchAny, SparseVectorParams, SparseVector
)
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
                    vectors_config={
                        "dense": VectorParams(size=settings.EMBEDDING_DIMENSION, distance=Distance.COSINE)
                    },
                    sparse_vectors_config={
                        "sparse": SparseVectorParams() 
                    }
                )
        except Exception as e:
            logger.error(f"Critical initialization failure on Qdrant cluster: {str(e)}")
            raise e
        
    def _compute_sparse_vector(self, text: str) -> dict:
        """Helper to generate token weights for exact keyword matching."""
        words = text.lower().split()
        frequencies = {}
        for word in words:
            clean_word = ''.join(e for e in word if e.isalnum())
            if clean_word:
                frequencies[clean_word] = frequencies.get(clean_word, 0) + 1
        
        indices = [hash(w) % 1000000 for w in frequencies.keys()]
        weights = [float(f) for f in frequencies.values()]
        return {"indices": indices, "values": weights}

    def upsert_embeddings(self, points_data: List[dict]) -> bool:
        """
        Maps data arrays explicitly to named storage vector targets and payload.
        Ensures metadata filters like user_id and allowed_roles are correctly populated.
        """
        try:
            points = []
            for item in points_data:
                # Compute keyword text mappings for hybrid search
                sparse_data = self._compute_sparse_vector(item["content"])
                
                points.append(
                    PointStruct(
                        id=item["chunk_id"],
                        vector={
                            "dense": item["vector"],
                            "sparse": SparseVector(indices=sparse_data["indices"], values=sparse_data["values"])
                        },
                        payload={
                            "document_id": item["document_id"],
                            "document_name": item["document_name"], 
                            "chunk_index": item["chunk_index"],     
                            "user_id": item["user_id"],
                            # Fallback to a list containing user_role if not provided explicitly during ingest
                            "allowed_roles": item.get("allowed_roles", [item.get("user_role", "Engineer")]),
                            "content": item["content"]
                        }
                    )
                )
            
            self.client.upsert(collection_name=self.collection_name, wait=True, points=points)
            return True
        except Exception as e:
            logger.error(f"Failed inserting point mappings into vector cluster: {str(e)}")
            raise RuntimeError(f"Vector storage driver exception: {str(e)}")

    def hybrid_search(self, dense_vector: List[float], query_text: str, user_id: int, user_role: str, limit: int = 5) -> List[VectorSearchResult]:
        """
        🛡️ Secure Hybrid Core Vector Retrieval Engine.
        Performs dual-engine lookups handling single unnamed fallback structures
        to circumvent vector naming resolution mismatch exceptions.
        """
        try:
            # 1. Build composite security filtering conditions matching Qdrant schema specs
            security_filter = Filter(
                must=[
                    # Boundary A: Multi-tenancy ownership containment
                    FieldCondition(
                        key="user_id", 
                        match=MatchValue(value=user_id)
                    ),
                    # Boundary B: Role-Based Access Control list matching
                    FieldCondition(
                        key="allowed_roles", 
                        match=MatchAny(any=[user_role])
                    )
                ]
            )
            
            sparse_data = self._compute_sparse_vector(query_text)

            # 2. Fire Dense Semantic Query (Using standard unnamed vector path fallback)
            try:
                dense_response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=dense_vector,
                    query_filter=security_filter,
                    limit=limit * 2
                )
            except Exception:
                # Fallback to explicit named configuration if single index rejected
                dense_response = self.client.query_points(
                    collection_name=self.collection_name,
                    using="dense",
                    query=dense_vector,
                    query_filter=security_filter,
                    limit=limit * 2
                )
            dense_results = dense_response.points

            # 3. Fire Parallel Sparse Keyword Match via named selector path
            try:
                sparse_response = self.client.query_points(
                    collection_name=self.collection_name,
                    using="sparse",
                    query=SparseVector(indices=sparse_data["indices"], values=sparse_data["values"]),
                    query_filter=security_filter,
                    limit=limit * 2
                )
                sparse_results = sparse_response.points
            except Exception as sparse_err:
                logger.warning(f"Sparse index lookup skipped or unconfigured: {str(sparse_err)}")
                sparse_results = []

            # 4. Apply Reciprocal Rank Fusion (RRF)
            rrf_scores = {}
            payload_cache = {}
            k = 60 

            for rank, hit in enumerate(dense_results):
                rrf_scores[hit.id] = rrf_scores.get(hit.id, 0.0) + (1.0 / (k + rank + 1))
                payload_cache[hit.id] = hit

            for rank, hit in enumerate(sparse_results):
                rrf_scores[hit.id] = rrf_scores.get(hit.id, 0.0) + (1.0 / (k + rank + 1))
                if hit.id not in payload_cache:
                    payload_cache[hit.id] = hit

            # Sort items to distill highest unified rank profile matches
            sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:limit]

            # 5. Map outcomes back to structural Pydantic Schema layouts cleanly
            return [
                VectorSearchResult(
                    chunk_id=cid,
                    score=round(rrf_scores[cid], 4),
                    document_id=payload_cache[cid].payload.get("document_id"),
                    document_name=payload_cache[cid].payload.get("document_name", "Unknown Document"),
                    chunk_index=payload_cache[cid].payload.get("chunk_index", 0),
                    content=payload_cache[cid].payload.get("content", "")
                )
                for cid, score in sorted_ids
            ]
            
        except Exception as e:
            logger.error(f"Failed performing secure vector matrix hybrid scan query lookup: {str(e)}")
            raise RuntimeError(f"Hybrid search processing failure: {str(e)}")

vector_service = VectorService()