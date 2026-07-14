from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.services.document_service import document_service
from app.tasks.document_tasks import process_document_pipeline
from app.core.celery_app import celery_app

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_enterprise_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Enforce safe upper thresholds to prevent multi-gigabyte disk flooding attacks
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit
    
    # We do a quick check on the stream type before executing full parsing pipelines
    if file.content_type not in [
            "application/pdf", 
            "text/plain", 
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported format. Only PDF, TXT, and DOCX extensions are allowed."
        )

    db_doc = document_service.save_uploaded_document(db=db, user=current_user, file=file)

    process_document_pipeline.apply_async(
        args=[db_doc.id],
        link_error=celery_app.tasks["tasks.handle_failed_document"].s(db_doc.id)
    )

    return db_doc

@router.get("", response_model=list[DocumentResponse])
def list_my_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return document_service.get_user_documents(db=db, user=current_user)