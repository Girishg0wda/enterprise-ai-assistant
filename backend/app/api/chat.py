import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from groq import Groq

from app.api.auth import get_current_user
from app.models.user import User
from app.services.search_service import search_service
from app.services.prompt_service import prompt_service # 🚀 Clean instance import
from app.core.config import settings                   # 🚀 Import centralized configuration

router = APIRouter(prefix="/chat", tags=["Grounded Conversation Engine"])
logger = logging.getLogger(__name__)

# Initialize Groq Client securely using centralized configuration managers
# Checks against mock strings and empty initializations automatically
if settings.GROQ_API_KEY and settings.GROQ_API_KEY != "mock-key-for-development" and settings.GROQ_API_KEY.strip() != "":
    logger.info("Initializing connection layer to live Groq cluster engines.")
    groq_client = Groq(api_key=settings.GROQ_API_KEY)
else:
    logger.warning("Groq API token signature unconfigured. Falling back to deactivated interface state.")
    groq_client = None

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []

@router.post("/stream")
async def stream_rag_chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Complete Live RAG Orchestrator Endpoint:
    Question -> Query Embedding -> Qdrant Context Search -> Prompt Builder v2 -> Groq Streaming Inference
    """
    if not groq_client:
        logger.error("Groq API execution requested but inference cluster connection layer is unconfigured.")
        raise HTTPException(status_code=500, detail="Inference cluster connection not configured.")

    try:
        logger.info(f"[RAG Engine] Incoming question from User ID {current_user.id}: '{request.message}'")

        # 1. RETRIEVAL LAYER: Search Qdrant for top 5 closest text blocks
        matched_chunks = search_service.search_similar_chunks(
            query_text=request.message,
            user_id=current_user.id,
            limit=5
        )

        # Convert schema result objects back to dictionaries for the prompt builder
        context_chunks = [
            {"content": chunk.content, "score": chunk.score}
            for chunk in matched_chunks
        ]
        logger.info(f"[RAG Engine] Extracted {len(context_chunks)} semantic context fragments from vector workspace.")

        # Convert Pydantic history objects to standard dictionary payloads
        formatted_history = [
            {"role": h.role, "content": h.content} 
            for h in request.history
        ]

        # 2. PROMPT BUILDER V2 LAYER: Assemble the secure grounded message matrix
        # Sourced through imported prompt_service wrapper using your plural function signature name
        augmented_payload = prompt_service.build_chat_messages(
            current_question=request.message,
            retrieved_chunks=context_chunks,
            history_messages=formatted_history,
            user_name=current_user.username if hasattr(current_user, 'username') else "Girisha"
        )

        # 3. INFERENCE LAYER: Request standard completion stream from Groq
        def groq_stream_generator():
            try:
                chat_completion = groq_client.chat.completions.create(
                    model=settings.GROQ_MODEL, # 🚀 Pulls cleanly from your settings ('llama-3.3-70b-versatile')
                    messages=augmented_payload,
                    temperature=0.2,            # Low temperature to prioritize data accuracy over creativity
                    stream=True
                )
                for chunk in chat_completion:
                    token = chunk.choices[0].delta.content
                    if token:
                        yield token
            except Exception as stream_err:
                logger.error(f"Inference streaming anomaly: {str(stream_err)}")
                yield f"\n[Inference Stream Error: {str(stream_err)}]"

        return StreamingResponse(groq_stream_generator(), media_type="text/plain")

    except Exception as e:
        logger.error(f"RAG orchestrator processing sequence crashed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Knowledge retrieval loop failure: {str(e)}")