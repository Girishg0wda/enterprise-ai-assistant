import os
import uuid
import logging
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.models.user import User

from app.services.pdf_service import pdf_service
from app.services.chunk_service import chunk_service
from app.services.embedding_service import embedding_service
from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)

class DocumentService:
    def _update_status(self, db: Session, doc: Document, status: DocumentStatus):
        doc.status = status
        db.commit()
        db.refresh(doc)
        logger.info(f"[Lifecycle] Doc ID {doc.id} transitioned to state: {status.value}")

    def save_uploaded_document(self, db: Session, file: UploadFile, user: User) -> Document:
        """🚀 STAGE 1: Fast Synchronous Save. Returns 201 immediately."""
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

        db_document = Document(
            user_id=user.id,
            filename=file.filename,
            file_path=target_file_path,
            file_size=file_size,
            content_type=file.content_type or "application/pdf",
            status=DocumentStatus.UPLOADED,
            extracted_text=""
        )
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        logger.info(f"🎉 Created Document Entry {db_document.id}. Status: {db_document.status.value}")
        return db_document

    def process_document_async_pipeline(self, db: Session, document_id: int):
        """⚙️ STAGE 2: Deep Asynchronous Pipeline. Executed inside the Celery Worker thread context."""
        db_document = db.query(Document).filter(Document.id == document_id).first()
        if not db_document:
            logger.error(f"Async pipeline invoked for non-existent Document ID {document_id}")
            return

        try:
            # 1. TEXT EXTRACTION STAGE
            self._update_status(db, db_document, DocumentStatus.EXTRACTING)
            extracted_text = pdf_service.extract_text(db_document.file_path)
            db_document.extracted_text = extracted_text
            self._update_status(db, db_document, DocumentStatus.TEXT_EXTRACTED)

            if not extracted_text or not extracted_text.strip():
                self._update_status(db, db_document, DocumentStatus.READY)
                return

            # 2. CHUNKING STAGE
            self._update_status(db, db_document, DocumentStatus.CHUNKING)
            text_chunks = chunk_service.split_text(db_document.extracted_text)
            
            if not text_chunks:
                self._update_status(db, db_document, DocumentStatus.READY)
                return
                
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
            self._update_status(db, db_document, DocumentStatus.CHUNKED)

            # 3. EMBEDDING GENERATION STAGE
            self._update_status(db, db_document, DocumentStatus.EMBEDDING)
            raw_texts_list = [c.content for c in db_chunks]
            vectors_batch = embedding_service.generate_embeddings(raw_texts_list)

            # 4. QDRANT INDEXING STAGE
            self._update_status(db, db_document, DocumentStatus.INDEXING)
            qdrant_payload_points = []
            for idx, chunk in enumerate(db_chunks):
                qdrant_payload_points.append({
                    "chunk_id": chunk.id,
                    "document_id": db_document.id,
                    "document_name": db_document.filename,
                    "chunk_index": chunk.chunk_index,
                    "user_id": db_document.user_id,
                    "content": chunk.content,
                    "vector": vectors_batch[idx]
                })

            vector_service.upsert_embeddings(qdrant_payload_points)
            self._update_status(db, db_document, DocumentStatus.READY)

        except Exception as pipeline_error:
            logger.error(f"❌ Ingestion pipeline execution crash on Doc ID {db_document.id}: {str(pipeline_error)}")
            self._update_status(db, db_document, DocumentStatus.FAILED)
            raise pipeline_error

    def get_user_documents(self, db: Session, user: User) -> list[Document]:
        """Fetch all documents belonging explicitly to the current user context."""
        return db.query(Document).filter(Document.user_id == user.id).all()

document_service = DocumentService()