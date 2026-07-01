import logging
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.chunk_service import chunk_service
from app.services.embedding_service import embedding_service
from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)

class IngestionService:
    def index_document(self, db: Session, document: Document) -> int:
        """Orchestrates Text Chunking -> Postgres Registration -> Batch Embedding -> Qdrant Upsert."""
        if not document.extracted_text or not document.extracted_text.strip():
            return 0

        try:
            logger.info(f"Running index extraction cascade for Doc ID: {document.id}")

            # 1. Split Text
            text_blocks = chunk_service.split_text(document.extracted_text)
            if not text_blocks:
                return 0

            # 2. Commit blocks to PostgreSQL to generate primary keys
            db_chunks = []
            for index, content in enumerate(text_blocks):
                chunk_record = DocumentChunk(
                    document_id=document.id,
                    chunk_index=index,
                    content=content
                )
                db.add(chunk_record)
                db_chunks.append(chunk_record)
            
            db.commit()
            for chunk in db_chunks:
                db.refresh(chunk)

            # 3. Compile Batch Embeddings
            qdrant_payloads = []
            for chunk in db_chunks:
                vector_weights = embedding_service.generate_embedding(chunk.content)
                qdrant_payloads.append({
                    "chunk_id": chunk.id,
                    "document_id": document.id,
                    "user_id": document.user_id,
                    "vector": vector_weights,
                    "content": chunk.content
                })

            # 4. Stream to Qdrant Core Engine
            vector_service.upsert_embeddings(qdrant_payloads)
            logger.info(f"Document {document.id} successfully written into all systems.")
            return len(db_chunks)

        except Exception as e:
            db.rollback()
            logger.error(f"Ingestion pipeline failure: {str(e)}")
            raise RuntimeError(f"Pipeline execution fault: {str(e)}")

ingestion_service = IngestionService()