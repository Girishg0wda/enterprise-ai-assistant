import time
import logging
from typing import Generator
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.database import get_db 
from app.models.user import User
from app.services.search_service import search_service
from app.services.prompt_service import prompt_service 
from app.services.memory_service import memory_service            
from app.services.conversation_service import conversation_service  
from app.services.semantic_memory_service import semantic_memory_service 
from app.services.cache_service import response_cache_service
from app.services.llm.provider_factory import ProviderFactory

router = APIRouter(prefix="/chat", tags=["Grounded Conversation Engine"])
logger = logging.getLogger(__name__)

# Instantiated globally at the module scope level to avoid initialization costs per request
try:
    llm_provider = ProviderFactory.create()
    logger.info("Successfully initialized production abstract LLM runtime engine.")
except Exception as e:
    logger.critical(f"Critical System Core Abort: ProviderFactory failed initialization: {str(e)}")
    llm_provider = None

class ChatRequest(BaseModel):
    conversation_id: int 
    message: str

@router.post("/stream")
async def stream_rag_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Guarding execution context via unified interface layer state
    if not llm_provider:
        raise HTTPException(
            status_code=500, 
            detail="Inference execution engine factory completely unconfigured or unhealthy."
        )

    request_start_time = time.perf_counter()
    current_role = getattr(current_user, "role", "Engineer")

    try:
        # 1. ⚡ QUICK INTERCEPT CACHE LOOKUP LAYER
        cached_answer = response_cache_service.get_cached_response(request.message, current_role)
        
        if cached_answer:
            total_cache_duration = time.perf_counter() - request_start_time
            logger.info(
                f"\n⚡ === PRODUCTION CACHE HIT PROFILE METRICS ===\n"
                f"⏱️ Absolute Request Loop     : {total_cache_duration:.4f}s\n"
                f"📈 Efficiency Metric          : Bypass Vector Match & LLM Inference Clusters\n"
                f"================================================="
            )
            
            # Persist logs to message history table
            conversation_service.save_message(db, request.conversation_id, current_user.id, "user", request.message)
            conversation_service.save_message(db, request.conversation_id, current_user.id, "assistant", cached_answer)
            
            def stream_cached_payload() -> Generator[str, None, None]:
                yield cached_answer
                
            return StreamingResponse(stream_cached_payload(), media_type="text/plain")

        # -----------------------------------------------------------------
        # CACHE MISS LOOP: Normal Pipeline Flow Continues
        # -----------------------------------------------------------------
        conversation_service.save_message(db, request.conversation_id, current_user.id, "user", request.message)

        # 2. RETRIEVAL LAYER WITH ACCESS ROLES INJECTED
        retraw_start = time.perf_counter()
        matched_chunks = search_service.search_similar_chunks(
            query_text=request.message, user_id=current_user.id, user_role=current_role, limit=5
        )
        retrieval_duration = time.perf_counter() - retraw_start

        context_chunks = [
            {
                "content": chunk.content, 
                "score": chunk.score, 
                "document_id": chunk.document_id, 
                "document_name": chunk.document_name, 
                "chunk_index": chunk.chunk_index
            } for chunk in matched_chunks
        ]
        
        # De-duplicate incoming context segments cleanly
        seen_citations = set()
        unique_sources = []
        for chunk in context_chunks:
            citation_key = (chunk["document_id"], chunk["chunk_index"])
            if citation_key not in seen_citations:
                seen_citations.add(citation_key)
                unique_sources.append(chunk)

        # 3. SEMANTIC MEMORY RECALL LAYER
        memory_recall_start = time.perf_counter()
        recalled_memories = semantic_memory_service.recall_relevant_memories(
            user_id=current_user.id, query_text=request.message, limit=3
        )
        memory_recall_duration = time.perf_counter() - memory_recall_start

        # 4. SHORT-TERM MEMORY BUFFER LAYER
        mem_start = time.perf_counter()
        sliding_history = memory_service.get_sliding_window_history(db, request.conversation_id, limit=10)
        memory_duration = time.perf_counter() - mem_start

        # 5. PROMPT MATRIX PROFILING LAYER
        augmented_payload = prompt_service.build_chat_messages(
            current_question=request.message, 
            retrieved_chunks=context_chunks, 
            history_messages=sliding_history, 
            semantic_memories=recalled_memories,
            user_name=current_user.username if hasattr(current_user, 'username') else "Girisha"
        )

        total_prompt_characters = sum(len(msg["content"]) for msg in augmented_payload)
        estimated_input_tokens = total_prompt_characters // 4

        # 6. INFERENCE & STREAMING ABSTRACT INTERFACE GENERATOR LAYER
        def abstract_stream_generator() -> Generator[str, None, None]:
            full_assistant_response = ""
            ttft_duration = None  
            token_count = 0
            inference_start = time.perf_counter()

            try:
                # Abstract generation execution call via runtime interface injection
                chat_stream = llm_provider.generate_stream(messages=augmented_payload, temperature=0.2)
                
                for token in chat_stream:
                    if token:
                        if ttft_duration is None:
                            ttft_duration = time.perf_counter() - inference_start
                        token_count += 1
                        full_assistant_response += token
                        yield token
                
                # Append formatted citation footprints at the terminal side of the generator pipeline
                sources_footer = ""
                if unique_sources:
                    sources_footer += "\n\n📚 **Sources:**\n"
                    for idx, src in enumerate(unique_sources, start=1):
                        sources_footer += f"{idx}. {src['document_name']} (Chunk {src['chunk_index']} | Match: {int(src['score'] * 100)}%)\n"
                    yield sources_footer

                complete_payload_text = full_assistant_response + sources_footer
                total_inference_duration = time.perf_counter() - inference_start
                total_request_duration = time.perf_counter() - request_start_time
                tokens_per_sec = token_count / total_inference_duration if total_inference_duration > 0 else 0

                logger.info(
                    f"\n📊 === PRODUCTION OBSERVED TELEMETRY METRICS ===\n"
                    f"⏱️ Document Retrieval Latency: {retrieval_duration:.4f}s\n"
                    f"⏱️ Memory Recall Latency     : {memory_recall_duration:.4f}s\n"
                    f"⏱️ Context Pull Latency      : {memory_duration:.4f}s\n"
                    f"⏱️ Time to First Token(TTFT) : {ttft_duration:.4f}s\n"
                    f"⏱️ LLM Stream Ingestion      : {total_inference_duration:.4f}s\n"
                    f"⏱️ Absolute Request Loop     : {total_request_duration:.4f}s\n"
                    f"⚡ Generation Velocity       : {tokens_per_sec:.1f} tokens/sec\n"
                    f"📈 Total Input Size          : ~{estimated_input_tokens} prompt tokens\n"
                    f"================================================="
                )

                # Post-inference serialization metrics capture sequences
                conversation_service.save_message(db, request.conversation_id, current_user.id, "assistant", complete_payload_text)
                semantic_memory_service.store_memory_turn(user_id=current_user.id, conversation_id=request.conversation_id, user_msg=request.message, assistant_msg=full_assistant_response)
                response_cache_service.set_cached_response(query_text=request.message, user_role=current_role, response_text=complete_payload_text)

            except Exception as stream_err:
                logger.error(f"Abstract inference connection segment fault: {str(stream_err)}")
                yield f"\n[Inference Stream Failure: {str(stream_err)}]"

        return StreamingResponse(abstract_stream_generator(), media_type="text/plain")

    except Exception as e:
        logger.error(f"RAG telemetry orchestrator sequence crashed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Knowledge retrieval metrics loop failure: {str(e)}")