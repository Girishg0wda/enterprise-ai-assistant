import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.database.base import Base
from app.database.database import engine
import app.models


from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.search import router as search_router # 🚀 

from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)

# Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing enterprise vector storage cluster indexes...")
    try:
        vector_service.create_collection() 
    except Exception as e:
        logger.critical(f"Failed configuring Qdrant container topology: {str(e)}")
    yield

app = FastAPI(
    title="Enterprise AI Knowledge Assistant",
    version="1.0.0",
    lifespan=lifespan 
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(search_router) 

@app.get("/")
def home():
    return {
        "message": "Enterprise AI Knowledge Assistant"
    }