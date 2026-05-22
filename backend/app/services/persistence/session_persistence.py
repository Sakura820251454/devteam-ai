import uuid
from datetime import datetime
from typing import Optional, Dict, List, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.models.core_db import SessionModel, MessageModel
from app.models.session import Session, SessionStatus, SessionPhase, Message, MessageType


class SessionPersistenceService:
    """会话/消息持久化服务 — CRUD for SessionModel + MessageModel"""

    def __init__(self):
        self._session_maker: Optional[async_sessionmaker[AsyncSession]] = None

    def initialize(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def _get_session(self) -> AsyncSession:
        if not self._session_maker:
            raise RuntimeError("SessionPersistenceService not initialized")
        return self._session_maker()

    async def load_all_sessions(self) -> Dict[str, Session]:
        """Load all sessions with their messages."""
        async with await self._get_session() as db:
            result = await db.execute(select(SessionModel))
            session_models = result.scalars().all()
            sessions: Dict[str, Session] = {}
            for sm in session_models:
                session = _session_from_model(sm)
                session.messages = await self._load_messages(db, sm.id)
                sessions[sm.id] = session
            return sessions

    async def _load_messages(self, db, session_id: str) -> List[Message]:
        result = await db.execute(
            select(MessageModel)
            .where(MessageModel.session_id == session_id)
            .order_by(MessageModel.timestamp.asc())
        )
        return [_message_from_model(m) for m in result.scalars().all()]

    async def save_session(self, session: Session) -> None:
        async with await self._get_session() as db:
            existing = await db.get(SessionModel, session.id)
            if existing:
                existing.title = session.title
                existing.project_id = session.project_id
                existing.status = session.status.value
                existing.phase = session.phase.value
                existing.participants = session.participants
                existing.token_budget = session.token_budget
                existing.token_used = session.token_used
                existing.ended_at = session.ended_at
            else:
                db.add(_model_from_session(session))
            await db.commit()

    async def save_message(self, message: Message) -> None:
        async with await self._get_session() as db:
            existing = await db.get(MessageModel, message.id)
            if not existing:
                db.add(_model_from_message(message))
                await db.commit()

    async def delete_session(self, session_id: str) -> None:
        async with await self._get_session() as db:
            model = await db.get(SessionModel, session_id)
            if model:
                await db.delete(model)
                await db.commit()
            # also delete messages
            msg_result = await db.execute(
                select(MessageModel).where(MessageModel.session_id == session_id)
            )
            for msg in msg_result.scalars().all():
                await db.delete(msg)
            await db.commit()


def _model_from_session(session: Session) -> SessionModel:
    return SessionModel(
        id=session.id,
        title=session.title,
        project_id=session.project_id,
        status=session.status.value,
        phase=session.phase.value,
        participants=session.participants,
        token_budget=session.token_budget,
        token_used=session.token_used,
        created_at=session.created_at,
        ended_at=session.ended_at,
    )


def _session_from_model(model: SessionModel) -> Session:
    return Session(
        id=model.id,
        title=model.title,
        project_id=model.project_id,
        status=SessionStatus(model.status),
        phase=SessionPhase(model.phase),
        participants=model.participants or [],
        messages=[],
        token_budget=model.token_budget or 100000,
        token_used=model.token_used or 0,
        created_at=model.created_at,
        ended_at=model.ended_at,
    )


def _model_from_message(message: Message) -> MessageModel:
    return MessageModel(
        id=message.id,
        session_id=message.session_id,
        sender_id=message.sender_id,
        sender_name=message.sender_name,
        content=message.content,
        message_type=message.message_type.value,
        metadata=message.metadata,
        timestamp=message.timestamp,
    )


def _message_from_model(model: MessageModel) -> Message:
    return Message(
        id=model.id,
        session_id=model.session_id,
        sender_id=model.sender_id,
        sender_name=model.sender_name,
        content=model.content,
        message_type=MessageType(model.message_type),
        timestamp=model.timestamp,
        metadata=model.metadata_json or {},
    )


session_persistence = SessionPersistenceService()
