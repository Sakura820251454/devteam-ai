from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel
from app.services import agent_service


router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    agent_id: str
    session_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    agent_id: str
    session_id: str


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        response = await agent_service.agent_chat(
            agent_id=request.agent_id,
            session_id=request.session_id,
            user_message=request.message
        )
        return ChatResponse(
            response=response,
            agent_id=request.agent_id,
            session_id=request.session_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    async def generate():
        try:
            async for chunk in agent_service.agent_chat_stream(
                agent_id=request.agent_id,
                session_id=request.session_id,
                user_message=request.message
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except ValueError as e:
            yield f"data: [ERROR] {str(e)}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
    
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
