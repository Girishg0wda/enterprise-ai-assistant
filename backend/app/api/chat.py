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
from app.services.conversation_service import conversation_service  
from app.services.semantic_memory_service import semantic_memory_service 
from app.services.cache_service import response_cache_service
from app.services.agent.orchestrator import agent_orchestrator

router = APIRouter(prefix="/chat", tags=["Grounded Conversation Engine"])
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    conversation_id: int 
    message: str

@router.post("/stream")
async def stream_agent_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
                f"📈 Efficiency Metric          : Bypass Agent Planner & Tool Execution Loops\n"
                f"================================================="
            )
            
            # Persist logs to message history table
            conversation_service.save_message(db, request.conversation_id, current_user.id, "user", request.message)
            conversation_service.save_message(db, request.conversation_id, current_user.id, "assistant", cached_answer)
            
            def stream_cached_payload() -> Generator[str, None, None]:
                yield cached_answer
                
            return StreamingResponse(stream_cached_payload(), media_type="text/plain")

        # -----------------------------------------------------------------
        # CACHE MISS LOOP: Run the Agent Orchestrator Framework
        # -----------------------------------------------------------------
        conversation_service.save_message(db, request.conversation_id, current_user.id, "user", request.message)

        # 2. TRIGGER REASONING & TOOL EXECUTION LOOP
        agent_start_time = time.perf_counter()
        agent_output = agent_orchestrator.run_agent_execution_loop(
            query_text=request.message,
            user_id=current_user.id,
            user_role=current_role
        )
        agent_duration = time.perf_counter() - agent_start_time

        # 3. STREAM WRAPPER FOR GENERATOR COMPATIBILITY
        def agent_stream_generator() -> Generator[str, None, None]:
            inference_start = time.perf_counter()
            try:
                # The response yields directly from the evaluated tool outcome matrix
                yield agent_output

                total_inference_duration = time.perf_counter() - inference_start
                total_request_duration = time.perf_counter() - request_start_time

                logger.info(
                    f"\n📊 === PRODUCTION OBSERVED TELEMETRY METRICS ===\n"
                    f"⏱️ Agent Orchestrator Loop   : {agent_duration:.4f}s\n"
                    f"⏱️ Stream Ingestion Latency   : {total_inference_duration:.4f}s\n"
                    f"⏱️ Absolute Request Loop     : {total_request_duration:.4f}s\n"
                    f"================================================="
                )

                # Post-inference serialization metrics capture sequences
                conversation_service.save_message(db, request.conversation_id, current_user.id, "assistant", agent_output)
                semantic_memory_service.store_memory_turn(user_id=current_user.id, conversation_id=request.conversation_id, user_msg=request.message, assistant_msg=agent_output)
                
                # 🛡️ CONDITIONAL CACHE GUARD
                is_error_response = any(indicator in agent_output.lower() for indicator in [
                    "not recognized or supported by explicit safety profiles",
                    "exception", 
                    "error:", 
                    "failure"
                ])

                if not is_error_response:
                    response_cache_service.set_cached_response(
                        query_text=request.message, 
                        user_role=current_role, 
                        response_text=agent_output
                    )
                else:
                    logger.warning("⚠️ [Cache System] Skipping cache write: Response matches a tool failure or safety violation profile.")

            except Exception as stream_err:
                logger.error(f"Agent inference connection segment fault: {str(stream_err)}")
                yield f"\n[Agent Stream Failure: {str(stream_err)}]"

        return StreamingResponse(agent_stream_generator(), media_type="text/plain")

    except Exception as e:
        logger.error(f"Agent architecture orchestrator sequence crashed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Agent runtime metrics loop failure: {str(e)}")