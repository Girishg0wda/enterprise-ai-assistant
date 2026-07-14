import enum
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, String, Integer, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class DocumentStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    EXTRACTING = "EXTRACTING"        
    TEXT_EXTRACTED = "TEXT_EXTRACTED"
    CHUNKING = "CHUNKING"             
    CHUNKED = "CHUNKED"
    EMBEDDING = "EMBEDDING"           
    INDEXING = "INDEXING"
    RETRYING = "RETRYING"
    READY = "READY"
    FAILED = "FAILED"

if TYPE_CHECKING:
    from app.models.user import User 
    from app.models.document_chunk import DocumentChunk

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(
        primary_key=True, 
        index=True
    )
    
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    filename: Mapped[str] = mapped_column(
        String(255), 
        nullable=False
    )
    
    file_path: Mapped[str] = mapped_column(
        String(512), 
        nullable=False
    )
    
    file_size: Mapped[int] = mapped_column(
        Integer, 
        nullable=False
    )
    
    content_type: Mapped[str] = mapped_column(
        String(100), 
        nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow
    )

    user: Mapped["User"] = relationship(
        "User", 
        back_populates="documents"
    )

    extracted_text: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow
    )

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, native_enum=False),
        default=DocumentStatus.UPLOADED,
        nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow
    )

    user: Mapped["User"] = relationship(
        "User", 
        back_populates="documents"
    )

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", 
        back_populates="document", 
        cascade="all, delete-orphan"
    )