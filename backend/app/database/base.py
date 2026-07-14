from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import create_engine  
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

from app.models.user import User
from app.models.document import Document
from app.models.document_chunk import DocumentChunk

engine = create_engine(
    settings.DATABASE_URL,
    echo=True
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()