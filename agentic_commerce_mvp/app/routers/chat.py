"""
Chat Router - Handles real-time chat interactions with the commerce agent
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional, List
import structlog
from datetime import datetime

from app.agents.commerce_agent import CommerceAgent, AgentTask, LLMProvider, AgentResponse

logger = structlog.get_logger()

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat message request"""
    message: str
    user_id: str
    session_id: Optional[str] = None
    task: Optional[str] = "product_search"
    provider: Optional[str] = "openai"


class ChatResponse(BaseModel):
    """Chat message response"""
    message: str
    session_id: str
    timestamp: datetime
    data: Optional[dict] = None
    suggested_products: List[dict] = []
    next_action: Optional[str] = None
    confidence: float = 0.8


# Store active agent sessions (in production, use Redis)
active_sessions = {}


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    Send a message to the commerce agent and get a response

    Args:
        request: ChatRequest with user message and metadata

    Returns:
        ChatResponse with agent reply
    """
    try:
        # Get or create agent session
        session_key = f"{request.user_id}_{request.session_id or 'default'}"

        if session_key not in active_sessions:
            # Create new agent
            provider = LLMProvider(request.provider) if request.provider else LLMProvider.OPENAI
            active_sessions[session_key] = CommerceAgent(
                user_id=request.user_id,
                session_id=request.session_id or session_key,
                preferred_provider=provider
            )

        agent = active_sessions[session_key]

        # Determine task type
        task = AgentTask(request.task) if request.task else AgentTask.PRODUCT_SEARCH

        # Process message
        response: AgentResponse = await agent.process_message(
            user_message=request.message,
            task=task
        )

        return ChatResponse(
            message=response.message,
            session_id=session_key,
            timestamp=datetime.utcnow(),
            data=response.data,
            suggested_products=response.suggested_products,
            next_action=response.next_action,
            confidence=response.confidence
        )

    except Exception as e:
        logger.error("chat_message_failed", error=str(e), user_id=request.user_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def end_session(session_id: str, user_id: str):
    """
    End an agent session and clear conversation history

    Args:
        session_id: Session identifier
        user_id: User identifier

    Returns:
        Success message
    """
    try:
        session_key = f"{user_id}_{session_id}"

        if session_key in active_sessions:
            del active_sessions[session_key]
            logger.info("session_ended", session_id=session_id, user_id=user_id)
            return {"status": "success", "message": "Session ended"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("session_end_failed", error=str(e), session_id=session_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/history")
async def get_conversation_history(session_id: str, user_id: str):
    """
    Get conversation history for a session

    Args:
        session_id: Session identifier
        user_id: User identifier

    Returns:
        Conversation history
    """
    try:
        session_key = f"{user_id}_{session_id}"

        if session_key in active_sessions:
            agent = active_sessions[session_key]
            return {
                "session_id": session_id,
                "user_id": user_id,
                "history": agent.conversation_history
            }
        else:
            raise HTTPException(status_code=404, detail="Session not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("history_retrieval_failed", error=str(e), session_id=session_id)
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint for real-time chat
@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time bidirectional chat

    Usage:
        ws://localhost:8000/api/v1/chat/ws/user_123
    """
    await websocket.accept()

    # Create agent for this connection
    session_id = f"ws_{user_id}_{datetime.utcnow().timestamp()}"
    agent = CommerceAgent(
        user_id=user_id,
        session_id=session_id,
        preferred_provider=LLMProvider.OPENAI
    )

    logger.info("websocket_connected", user_id=user_id, session_id=session_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message = data.get("message", "")
            task_str = data.get("task", "product_search")

            if not message:
                await websocket.send_json({
                    "error": "Empty message"
                })
                continue

            # Process with agent
            task = AgentTask(task_str)
            response: AgentResponse = await agent.process_message(message, task)

            # Send response back
            await websocket.send_json({
                "message": response.message,
                "data": response.data,
                "suggested_products": response.suggested_products,
                "confidence": response.confidence,
                "timestamp": datetime.utcnow().isoformat()
            })

    except WebSocketDisconnect:
        logger.info("websocket_disconnected", user_id=user_id, session_id=session_id)
    except Exception as e:
        logger.error("websocket_error", error=str(e), user_id=user_id)
        await websocket.close()
