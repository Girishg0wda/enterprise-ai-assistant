import os
import uuid
import logging
from pathlib import Path

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

# ============================================================
# Shared Upload Directory
# ============================================================
BASE_DIR = Path("/app")
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class DocumentService:

    def _update_status(self, db: Session, doc: Document, status: DocumentStatus):
        """Update document processing status."""
        doc.status = status
        db.commit()
        db.refresh(doc)
        logger.info(
            f"[Lifecycle] Doc ID {doc.id} transitioned to state: {status.value}"
        )

    # ============================================================
    # Stage 1 - Upload
    # ============================================================
    def save_uploaded_document(
        self,
        db: Session,
        file: UploadFile,
        user: User
    ) -> Document:
        """
        Save uploaded document to disk and create DB record.
        Returns immediately.
        """

        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        target_file_path = UPLOAD_DIR / unique_filename

        file_size = 0

        try:
            with open(target_file_path, "wb") as buffer:
                while chunk := file.file.read(8192):
                    buffer.write(chunk)
                    file_size += len(chunk)

        except Exception as e:
            logger.error(f"Failed saving uploaded file: {e}")
            raise RuntimeError(f"Disk write failed: {e}")

        db_document = Document(
            user_id=user.id,
            filename=file.filename,
            file_path=str(target_file_path),
            file_size=file_size,
            content_type=file.content_type or "application/pdf",
            status=DocumentStatus.UPLOADED,
            extracted_text=""
        )

        db.add(db_document)
        db.commit()
        db.refresh(db_document)

        logger.info(
            f"🎉 Document {db_document.id} uploaded successfully."
        )

        return db_document

    # ============================================================
    # Stage 2 - Celery Processing
    # ============================================================
    def process_document_async_pipeline(
        self,
        db: Session,
        document_id: int
    ):
        """
        Complete ingestion pipeline.
        Executed inside Celery.
        """

        db_document = (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )

        if not db_document:
            logger.error(
                f"Document {document_id} not found."
            )
            return

        try:

            # ----------------------------------------------------
            # 1. Extract Text
            # ----------------------------------------------------
            self._update_status(
                db,
                db_document,
                DocumentStatus.EXTRACTING
            )

            extracted_text = pdf_service.extract_text(
                db_document.file_path
            )

            db_document.extracted_text = extracted_text

            self._update_status(
                db,
                db_document,
                DocumentStatus.TEXT_EXTRACTED
            )

            if not extracted_text.strip():
                self._update_status(
                    db,
                    db_document,
                    DocumentStatus.READY
                )
                return

            # ----------------------------------------------------
            # 2. Chunk Text
            # ----------------------------------------------------
            self._update_status(
                db,
                db_document,
                DocumentStatus.CHUNKING
            )

            chunks = chunk_service.split_text(extracted_text)

            if not chunks:
                self._update_status(
                    db,
                    db_document,
                    DocumentStatus.READY
                )
                return

            db_chunks = []

            for idx, content in enumerate(chunks):

                chunk = DocumentChunk(
                    document_id=db_document.id,
                    chunk_index=idx,
                    content=content,
                )

                db.add(chunk)
                db_chunks.append(chunk)

            db.commit()

            self._update_status(
                db,
                db_document,
                DocumentStatus.CHUNKED
            )

            # ----------------------------------------------------
            # 3. Generate Embeddings
            # ----------------------------------------------------
            self._update_status(
                db,
                db_document,
                DocumentStatus.EMBEDDING
            )

            vectors = embedding_service.generate_embeddings(
                [c.content for c in db_chunks]
            )

            # ----------------------------------------------------
            # 4. Store in Qdrant
            # ----------------------------------------------------
            self._update_status(
                db,
                db_document,
                DocumentStatus.INDEXING
            )

            payload = []

            for idx, chunk in enumerate(db_chunks):

                payload.append(
                    {
                        "chunk_id": chunk.id,
                        "document_id": db_document.id,
                        "document_name": db_document.filename,
                        "chunk_index": chunk.chunk_index,
                        "user_id": db_document.user_id,
                        "content": chunk.content,
                        "vector": vectors[idx],
                    }
                )

            vector_service.upsert_embeddings(payload)

            self._update_status(
                db,
                db_document,
                DocumentStatus.READY
            )

            logger.info(
                f"✅ Document {db_document.id} indexed successfully."
            )

        except Exception as e:

            logger.exception(
                f"❌ Pipeline failed for document {db_document.id}"
            )

            self._update_status(
                db,
                db_document,
                DocumentStatus.FAILED
            )

            raise

    # ============================================================
    # Fetch User Documents
    # ============================================================
    def get_user_documents(
        self,
        db: Session,
        user: User
    ) -> list[Document]:

        return (
            db.query(Document)
            .filter(Document.user_id == user.id)
            .all()
        )


document_service = DocumentService()