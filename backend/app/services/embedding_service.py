import logging
from typing import List
from sentence_transformers import SentenceTransformer
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        # 🚀 1. Sourced cleanly from app environment configuration constants
        logger.info(f"Loading local embedding transformer: {settings.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Accepts multiple text chunks -> Computes dense weight vectors in batches.
        Used for indexing documents.
        """
        if not texts:
            return []

        try:
            logger.info(f"Calculating batch vector matrices for {len(texts)} chunks.")
            embeddings = self.model.encode(texts, batch_size=32, show_progress_bar=False)
            return [embedding.tolist() for embedding in embeddings]
        except Exception as e:
            logger.error(f"Batch embedding generation pipeline error: {str(e)}")
            raise RuntimeError(f"Vector transformation driver failure: {str(e)}")

    def generate_query_embedding(self, text: str) -> List[float]:
        """
        🚀 3. Clear API for Retrieval:
        Accepts a single user search string/question -> Returns individual dense vector list.
        """
        if not text or not text.strip():
            raise ValueError("Query text cannot be empty.")
            
        # Internally wraps string into the optimized matrix extractor and pulls item index 0
        results = self.generate_embeddings([text])
        return results[0]

# Single state instantiation export
embedding_service = EmbeddingService()