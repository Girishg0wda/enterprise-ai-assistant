import os
import uuid
import logging
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User

# 🚀 The Decoupled Components of our Orchestra
from app.services.pdf_service import pdf_service
from app.services.chunk_service import chunk_service
from app.services.embedding_service import embedding_service
from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)

class DocumentService:
    def save_uploaded_document(self, db: Session, file: UploadFile, user: User) -> Document:
        """
        The Master Conductor Flow:
        Upload File ──> PDF Service ──> Chunk Service ──> Embedding Service ──> Vector Service
        """
        # 1. Secure physical file delivery to disk storage
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)

        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        target_file_path = os.path.join(upload_dir, unique_filename)
        
        file_size = 0
        try:
            with open(target_file_path, "wb") as buffer:
                while content_block := file.file.read(8192):
                    buffer.write(content_block)
                    file_size += len(content_block)
        except Exception as e:
            logger.error(f"Failed committing binary write-stream to disk: {str(e)}")
            raise RuntimeError(f"Disk file write failure: {str(e)}")

        # 2. Extract plain text (PDF Service)
        logger.info(f"[Orchestrator] Step 1/5: Extracting text from PDF: {file.filename}")
        extracted_text = pdf_service.extract_text(target_file_path)

        # 3. Create the parent document entity in PostgreSQL
        db_document = Document(
            user_id=user.id,
            filename=file.filename,
            file_path=target_file_path,
            file_size=file_size,
            content_type=file.content_type or "application/pdf",
            extracted_text=extracted_text
        )
        db.add(db_document)
        db.commit()
        db.refresh(db_document)

        # Stop early if there is no structural text to process
        if not db_document.extracted_text or not db_document.extracted_text.strip():
            logger.warning(f"Document {db_document.id} was processed but contains no extractable text.")
            return db_document

        try:
            # 4. Break down text into logical paragraph chunks (Chunk Service)
            logger.info(f"[Orchestrator] Step 2/5: Chunking text for Doc ID: {db_document.id}")
            text_chunks = chunk_service.split_text(db_document.extracted_text)
            
            if not text_chunks:
                return db_document

            # 5. Bulk commit text slices to PostgreSQL to generate permanent IDs
            logger.info(f"[Orchestrator] Step 3/5: Saving {len(text_chunks)} tracking rows to Postgres")
            db_chunks = []
            for index, content in enumerate(text_chunks):
                chunk_record = DocumentChunk(
                    document_id=db_document.id,
                    chunk_index=index,
                    content=content
                )
                db.add(chunk_record)
                db_chunks.append(chunk_record)
            
            db.commit()
            for chunk in db_chunks:
                db.refresh(chunk)

            # 6. Convert text strings into dense vector arrays in one batch (Embedding Service)
            logger.info(f"[Orchestrator] Step 4/5: Generating high-speed batch vectors")
            raw_texts_list = [c.content for c in db_chunks]
            vectors_batch = embedding_service.generate_embeddings(raw_texts_list)

            # 7. Map text variables and vector arrays together into unified payloads
            qdrant_payload_points = []
            for idx, chunk in enumerate(db_chunks):
                qdrant_payload_points.append({
                    "chunk_id": chunk.id,
                    "document_id": db_document.id,
                    "user_id": db_document.user_id,
                    "content": chunk.content,
                    "vector": vectors_batch[idx]  # Directly aligns with index positions
                })

            # 8. Push final structures into Qdrant index graphs (Vector Service)
            logger.info(f"[Orchestrator] Step 5/5: Streaming vector payloads to Qdrant cluster")
            vector_service.upsert_embeddings(qdrant_payload_points)
            
            logger.info(f"🎉 [Orchestrator] Success! Doc ID {db_document.id} is live and immediately searchable.")

        except Exception as pipeline_error:
            # Catch background indexing failures so the core document entry stays valid
            logger.error(f"❌ Ingestion pipeline orchestration error: {str(pipeline_error)}")

        return db_document

document_service = DocumentService()