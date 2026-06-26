from fastapi import FastAPI

from app.api.test_db import router

app = FastAPI(
    title="Enterprise AI Knowledge Assistant",
    version="1.0.0"
)

app.include_router(router)


@app.get("/")
def home():
    return {
        "message": "Enterprise AI Knowledge Assistant 🚀"
    }