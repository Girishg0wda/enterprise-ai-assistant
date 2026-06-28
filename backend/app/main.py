from fastapi import FastAPI

from app.database.base import Base
from app.database.database import engine
from app.api.chat import router as chat_router
# Import all models
import app.models

from app.api.auth import router as auth_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Enterprise AI Knowledge Assistant",
    version="1.0.0"
)

app.include_router(auth_router)
app.include_router(chat_router)

@app.get("/")
def home():
    return {
        "message": "Enterprise AI Knowledge Assistant 🚀"
    }