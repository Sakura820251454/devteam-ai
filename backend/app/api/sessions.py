from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel
from app.services import agent_service
from app.models import Session, SessionStatus


router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    title: str = "新会话"
    participant_ids: List[str] = None


class SessionResponse(BaseModel):
    id: str
    title: str
    status: str
    participants: List[str]
    message_count: int
    token_used: int
    created_at: str
    
    @classmethod
    def from_session(cls, session: Session):
        return cls(
            id=session.id,
            title=session.title,
            status=session.status.value,
            participants=session.participants,
            message_count=len(session.messages),
            token_used=session.token_used,
            created_at=session.created_at.isoformat()
        )


class SendMessageRequest(BaseModel):
    agent_id: str
    message: str


@router.post("", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest = None):
    if request:
        session = await agent_service.create_session(
            title=request.title,
            participant_ids=request.participant_ids
        )
    else:
        session = await agent_service.create_session()
    return SessionResponse.from_session(session)


@router.get("", response_model=List[SessionResponse])
async def list_sessions():
    return [SessionResponse.from_session(session) for session in agent_service.list_sessions()]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    session = agent_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse.from_session(session)


@router.get("/{session_id}/messages")
async def get_messages(session_id: str):
    session = agent_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return [
        {
            "id": msg.id,
            "sender_id": msg.sender_id,
            "sender_name": msg.sender_name,
            "content": msg.content,
            "type": msg.message_type.value,
            "timestamp": msg.timestamp.isoformat()
        }
        for msg in session.messages
    ]


@router.post("/{session_id}/pause")
async def pause_session(session_id: str):
    session = agent_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = SessionStatus.PAUSED
    return {"message": "Session paused"}


@router.post("/{session_id}/resume")
async def resume_session(session_id: str):
    session = agent_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = SessionStatus.ACTIVE
    return {"message": "Session resumed"}


@router.post("/{session_id}/end")
async def end_session(session_id: str):
    session = agent_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = SessionStatus.ENDED
    return {"message": "Session ended"}
