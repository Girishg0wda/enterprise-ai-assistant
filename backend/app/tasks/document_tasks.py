import logging
from app.core.celery_app import celery_app
from app.database.database import SessionLocal 
from app.services.document_service import document_service
from app.models.document import Document, DocumentStatus

logger = logging.getLogger(__name__)

@celery_app.task(
    name="tasks.process_document_pipeline", 
    bind=True, 
    max_retries=3
)
def process_document_pipeline(self, document_id: int):
    """
    Decoupled Background Task Worker Loop with Automatic Backoff Retry,
    State Tracking, and Structural Error Logging.
    """
    current_attempt = self.request.retries + 1
    logger.info(f"🚀 [Worker] Ingestion process loop execution - Attempt {current_attempt}/4 for Document ID {document_id}")
    
    db = SessionLocal()
    try:
        # 1. Trigger the ingestion services
        document_service.process_document_async_pipeline(db, document_id)
        
        # 2. Clear out any residual historical error logs on ultimate success boundary
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.error_message = None
            db.commit()
            
        logger.info(f"✨ [Worker] Successfully processed and indexed Document ID {document_id}")
        
    except Exception as exc:
        error_msg = str(exc)
        doc = db.query(Document).filter(Document.id == document_id).first()
        
        # Check if we have more retries left in the bank
        if self.request.retries < self.max_retries:
            # Calculate the exact requested delay steps: 30s -> 60s -> 120s
            delay_mapping = {0: 30, 1: 60, 2: 120}
            countdown = delay_mapping.get(self.request.retries, 60)
            
            logger.warning(
                f"⚠️ [Retry {current_attempt}/3] Document {document_id} failed. "
                f"Reason: '{error_msg}'. Retrying in {countdown} seconds..."
            )
            
            if doc:
                doc.status = DocumentStatus.RETRYING
                doc.error_message = error_msg
                db.commit()
                
            db.close()
            raise self.retry(exc=exc, countdown=countdown)
        else:
            # All retries exhausted—mark as permanently FAILED
            logger.error(f"❌ Document {document_id} marked FAILED. Retries completely exhausted.")
            if doc:
                doc.status = DocumentStatus.FAILED
                doc.error_message = f"Retries exhausted. Final error: {error_msg}"
                db.commit()
                
    finally:
        if 'db' in locals() and db:
            db.close()


@celery_app.task(name="tasks.handle_failed_document")
def handle_failed_document(document_id: int):
    """Handle failed document ingestion by updating the status and logging the failure."""
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(f"Failed callback invoked for missing Document ID {document_id}")
            return

        doc.status = DocumentStatus.FAILED
        doc.error_message = "Ingestion failed after Celery retries. Please inspect worker logs."
        db.commit()
        logger.error(f"❌ [Failure Callback] Document ID {document_id} marked FAILED by link_error callback.")
    except Exception as exc:
        logger.error(f"Failed to execute handle_failed_document callback for Document ID {document_id}: {exc}")
    finally:
        db.close()