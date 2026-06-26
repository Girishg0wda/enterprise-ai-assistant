from fastapi import FastAPI

app = FastAPI(
    title="Enterprise AI Knowledge Assistant",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "message": "Welcome to Enterprise AI Knowledge Assistant 🚀"
    }