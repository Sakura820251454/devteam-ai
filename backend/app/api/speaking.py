from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel, Field

from app.services.collaboration.speaking_controller import SpeakingMode, speaking_controller


router = APIRouter(prefix="/api/speaking", tags=["发言控制"])


class SetModeRequest(BaseModel):
    session_id: str
    mode: SpeakingMode


class SetBudgetRequest(BaseModel):
    session_id: str
    total_budget: int


class RequestSpeakRequest(BaseModel):
    session_id: str
    agent_id: str
    agent_name: str
    priority: int = 0


class SetAgentConfigRequest(BaseModel):
    agent_id: str
    min_interval_seconds: float = 2.0
    max_messages_per_minute: int = 10
    priority: int = 0
    max_tokens_per_message: Optional[int] = None


class SpeakingTurnResponse(BaseModel):
    id: str
    agent_id: str
    agent_name: str
    priority: int
    is_user: bool


class TokenBudgetResponse(BaseModel):
    session_id: str
    total_budget: int
    used_tokens: int
    remaining: int
    usage_ratio: float
    is_exhausted: bool
    is_warning: bool


@router.post("/mode")
async def set_mode(request: SetModeRequest):
    speaking_controller.set_mode(request.session_id, request.mode)
    return {
        "session_id": request.session_id,
        "mode": request.mode.value
    }


@router.get("/mode/{session_id}")
async def get_mode(session_id: str):
    mode = speaking_controller.get_mode(session_id)
    return {
        "session_id": session_id,
        "mode": mode.value
    }


@router.post("/budget")
async def set_budget(request: SetBudgetRequest):
    budget = speaking_controller.set_token_budget(
        request.session_id,
        request.total_budget
    )
    return TokenBudgetResponse(
        session_id=budget.session_id,
        total_budget=budget.total_budget,
        used_tokens=budget.used_tokens,
        remaining=budget.remaining(),
        usage_ratio=budget.usage_ratio(),
        is_exhausted=budget.is_exhausted(),
        is_warning=budget.is_warning()
    )


@router.get("/budget/{session_id}")
async def get_budget(session_id: str):
    budget = speaking_controller.get_token_budget(session_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return TokenBudgetResponse(
        session_id=budget.session_id,
        total_budget=budget.total_budget,
        used_tokens=budget.used_tokens,
        remaining=budget.remaining(),
        usage_ratio=budget.usage_ratio(),
        is_exhausted=budget.is_exhausted(),
        is_warning=budget.is_warning()
    )


@router.post("/consume")
async def consume_tokens(session_id: str, tokens: int):
    success = speaking_controller.consume_tokens(session_id, tokens)
    return {
        "success": success,
        "remaining": speaking_controller.get_remaining_tokens(session_id)
    }


@router.post("/request-speak")
async def request_speak(request: RequestSpeakRequest):
    turn = await speaking_controller.request_speak(
        session_id=request.session_id,
        agent_id=request.agent_id,
        agent_name=request.agent_name,
        priority=request.priority
    )
    if not turn:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded or session not found"
        )
    return SpeakingTurnResponse(
        id=turn.id,
        agent_id=turn.agent_id,
        agent_name=turn.agent_name,
        priority=turn.priority,
        is_user=turn.is_user
    )


@router.post("/next/{session_id}")
async def next_turn(session_id: str):
    turn = await speaking_controller.next_turn(session_id)
    if not turn:
        return {"turn": None, "message": "No more turns in queue"}
    return SpeakingTurnResponse(
        id=turn.id,
        agent_id=turn.agent_id,
        agent_name=turn.agent_name,
        priority=turn.priority,
        is_user=turn.is_user
    )


@router.post("/skip/{session_id}/{turn_id}")
async def skip_turn(session_id: str, turn_id: str):
    success = await speaking_controller.skip_turn(session_id, turn_id)
    return {"success": success}


@router.post("/clear/{session_id}")
async def clear_queue(session_id: str):
    count = await speaking_controller.clear_queue(session_id)
    return {"cleared": count}


@router.get("/queue/{session_id}")
async def get_queue(session_id: str):
    queue = speaking_controller.get_queue(session_id)
    return {
        "session_id": session_id,
        "length": len(queue),
        "queue": [
            SpeakingTurnResponse(
                id=t.id,
                agent_id=t.agent_id,
                agent_name=t.agent_name,
                priority=t.priority,
                is_user=t.is_user
            )
            for t in queue
        ]
    }


@router.post("/agent-config")
async def set_agent_config(request: SetAgentConfigRequest):
    from app.services.collaboration.speaking_controller import AgentSpeakingConfig
    config = AgentSpeakingConfig(
        agent_id=request.agent_id,
        min_interval_seconds=request.min_interval_seconds,
        max_messages_per_minute=request.max_messages_per_minute,
        priority=request.priority,
        max_tokens_per_message=request.max_tokens_per_message
    )
    speaking_controller.set_agent_config(request.agent_id, config)
    return {"status": "ok", "agent_id": request.agent_id}


@router.get("/agent-config/{agent_id}")
async def get_agent_config(agent_id: str):
    config = speaking_controller.get_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config


@router.get("/status/{session_id}")
async def get_status(session_id: str):
    return {
        "session_id": session_id,
        "is_speaking": speaking_controller.is_speaking(session_id),
        "current_speaker": speaking_controller.get_current_speaker(session_id),
        "queue_length": speaking_controller.get_queue_length(session_id),
        "mode": speaking_controller.get_mode(session_id).value,
        "remaining_tokens": speaking_controller.get_remaining_tokens(session_id)
    }


@router.post("/stop/{session_id}")
async def force_stop(session_id: str):
    speaking_controller.force_stop_speaking(session_id)
    return {"status": "ok"}


@router.post("/cleanup/{session_id}")
async def cleanup(session_id: str):
    speaking_controller.cleanup_session(session_id)
    return {"status": "ok"}
