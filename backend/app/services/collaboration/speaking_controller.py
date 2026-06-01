import asyncio
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from pydantic import BaseModel, Field


class SpeakingMode(str, Enum):
    SEQUENTIAL = "sequential"
    ROUND_ROBIN = "round_robin"
    PRIORITY_BASED = "priority_based"
    FREE_STYLE = "free_style"


class SpeakingTurn(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    agent_name: str
    priority: int = 0
    is_user: bool = False
    created_at: datetime = Field(default_factory=datetime.now)


class TokenBudget(BaseModel):
    session_id: str
    total_budget: int
    used_tokens: int = 0
    warning_threshold: float = 0.8

    def remaining(self) -> int:
        return self.total_budget - self.used_tokens

    def usage_ratio(self) -> float:
        if self.total_budget == 0:
            return 0
        return self.used_tokens / self.total_budget

    def is_exhausted(self) -> bool:
        return self.remaining() <= 0

    def is_warning(self) -> bool:
        return self.usage_ratio() >= self.warning_threshold


class AgentSpeakingConfig(BaseModel):
    agent_id: str
    min_interval_seconds: float = 2.0
    max_messages_per_minute: int = 10
    priority: int = 0
    max_tokens_per_message: Optional[int] = None


@dataclass
class RateLimitEntry:
    count: int = 0
    window_start: datetime = field(default_factory=datetime.now)


class SpeakingController:
    def __init__(self):
        self._queues: Dict[str, List[SpeakingTurn]] = {}
        self._token_budgets: Dict[str, TokenBudget] = {}
        self._agent_configs: Dict[str, AgentSpeakingConfig] = {}
        self._rate_limits: Dict[str, RateLimitEntry] = {}
        self._current_speaker: Dict[str, Optional[str]] = {}
        self._speaking_mode: Dict[str, SpeakingMode] = {}
        self._lock = asyncio.Lock()
        self._turn_handlers: Dict[str, List[Callable]] = {}

    def set_mode(self, session_id: str, mode: SpeakingMode) -> None:
        self._speaking_mode[session_id] = mode
        if mode == SpeakingMode.ROUND_ROBIN:
            self._queues[session_id] = []

    def get_mode(self, session_id: str) -> SpeakingMode:
        return self._speaking_mode.get(session_id, SpeakingMode.FREE_STYLE)

    def set_token_budget(self, session_id: str, total_budget: int) -> TokenBudget:
        budget = TokenBudget(session_id=session_id, total_budget=total_budget)
        self._token_budgets[session_id] = budget
        return budget

    def get_token_budget(self, session_id: str) -> Optional[TokenBudget]:
        return self._token_budgets.get(session_id)

    def consume_tokens(self, session_id: str, tokens: int) -> bool:
        budget = self._token_budgets.get(session_id)
        if not budget:
            return True
        if budget.is_exhausted():
            return False
        budget.used_tokens = min(budget.used_tokens + tokens, budget.total_budget)
        return True

    def get_remaining_tokens(self, session_id: str) -> int:
        budget = self._token_budgets.get(session_id)
        return budget.remaining() if budget else -1

    def set_agent_config(self, agent_id: str, config: AgentSpeakingConfig) -> None:
        self._agent_configs[agent_id] = config

    def get_agent_config(self, agent_id: str) -> Optional[AgentSpeakingConfig]:
        return self._agent_configs.get(agent_id)

    def _check_rate_limit(self, agent_id: str) -> bool:
        config = self._agent_configs.get(agent_id)
        if not config:
            return True

        now = datetime.now()
        if agent_id not in self._rate_limits:
            self._rate_limits[agent_id] = RateLimitEntry()

        entry = self._rate_limits[agent_id]
        window = timedelta(minutes=1)
        if now - entry.window_start > window:
            entry.count = 0
            entry.window_start = now

        if entry.count >= config.max_messages_per_minute:
            return False

        entry.count += 1
        return True

    async def request_speak(
        self,
        session_id: str,
        agent_id: str,
        agent_name: str,
        priority: int = 0,
        is_user: bool = False
    ) -> Optional[SpeakingTurn]:
        config = self._agent_configs.get(agent_id)
        if config and not self._check_rate_limit(agent_id):
            return None

        mode = self.get_mode(session_id)
        if mode == SpeakingMode.FREE_STYLE:
            turn = SpeakingTurn(
                agent_id=agent_id,
                agent_name=agent_name,
                priority=priority,
                is_user=is_user
            )
            await self._notify_turn(turn)
            return turn

        if mode in [SpeakingMode.SEQUENTIAL, SpeakingMode.ROUND_ROBIN]:
            queue = self._queues.setdefault(session_id, [])
            turn = SpeakingTurn(
                agent_id=agent_id,
                agent_name=agent_name,
                priority=priority,
                is_user=is_user
            )
            queue.append(turn)
            if mode == SpeakingMode.ROUND_ROBIN:
                if len(queue) == 1:
                    await self._notify_turn(turn)
            return turn

        if mode == SpeakingMode.PRIORITY_BASED:
            queue = self._queues.setdefault(session_id, [])
            turn = SpeakingTurn(
                agent_id=agent_id,
                agent_name=agent_name,
                priority=priority,
                is_user=is_user
            )
            queue.append(turn)
            queue.sort(key=lambda t: (-t.priority, t.created_at))
            await self._notify_turn(queue[0])
            return turn

        return None

    async def _notify_turn(self, turn: SpeakingTurn) -> None:
        session_id = self._get_session_for_agent(turn.agent_id)
        if session_id and session_id in self._turn_handlers:
            for handler in self._turn_handlers[session_id]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(turn)
                    else:
                        handler(turn)
                except Exception:
                    pass

    def _get_session_for_agent(self, agent_id: str) -> Optional[str]:
        for session_id, queue in self._queues.items():
            if any(t.agent_id == agent_id for t in queue):
                return session_id
        return None

    async def next_turn(self, session_id: str) -> Optional[SpeakingTurn]:
        async with self._lock:
            queue = self._queues.get(session_id, [])
            if not queue:
                return None

            mode = self.get_mode(session_id)
            if mode == SpeakingMode.SEQUENTIAL:
                turn = queue.pop(0)
                return turn

            if mode == SpeakingMode.ROUND_ROBIN:
                if queue:
                    turn = queue.pop(0)
                    return turn
                return None

            if mode == SpeakingMode.PRIORITY_BASED:
                queue.sort(key=lambda t: (-t.priority, t.created_at))
                if queue:
                    return queue.pop(0)
                return None

            return None

    async def skip_turn(self, session_id: str, turn_id: str) -> bool:
        async with self._lock:
            queue = self._queues.get(session_id, [])
            for i, turn in enumerate(queue):
                if turn.id == turn_id:
                    queue.pop(i)
                    return True
            return False

    async def clear_queue(self, session_id: str) -> int:
        async with self._lock:
            queue = self._queues.get(session_id, [])
            count = len(queue)
            self._queues[session_id] = []
            return count

    def get_queue(self, session_id: str) -> List[SpeakingTurn]:
        return self._queues.get(session_id, []).copy()

    def get_queue_length(self, session_id: str) -> int:
        return len(self._queues.get(session_id, []))

    def register_turn_handler(self, session_id: str, handler: Callable) -> None:
        handlers = self._turn_handlers.setdefault(session_id, [])
        handlers.append(handler)

    def unregister_turn_handler(self, session_id: str, handler: Callable) -> None:
        if session_id in self._turn_handlers:
            if handler in self._turn_handlers[session_id]:
                self._turn_handlers[session_id].remove(handler)

    def is_speaking(self, session_id: str) -> bool:
        return self._current_speaker.get(session_id) is not None

    def get_current_speaker(self, session_id: str) -> Optional[str]:
        return self._current_speaker.get(session_id)

    def set_current_speaker(self, session_id: str, agent_id: Optional[str]) -> None:
        self._current_speaker[session_id] = agent_id

    def force_stop_speaking(self, session_id: str) -> None:
        self._current_speaker[session_id] = None

    def cleanup_session(self, session_id: str) -> None:
        if session_id in self._queues:
            del self._queues[session_id]
        if session_id in self._token_budgets:
            del self._token_budgets[session_id]
        if session_id in self._speaking_mode:
            del self._speaking_mode[session_id]
        if session_id in self._current_speaker:
            del self._current_speaker[session_id]
        if session_id in self._turn_handlers:
            del self._turn_handlers[session_id]

    def cleanup_project_sessions(self, project_id: str) -> None:
        """清理与项目相关的所有会话（通过 session_id 前缀匹配 project:{project_id}）"""
        prefix = f"project:{project_id}"
        all_sessions = set(self._queues.keys()) | set(self._token_budgets.keys()) | set(self._speaking_mode.keys())
        for session_id in all_sessions:
            if session_id.startswith(prefix) or session_id == project_id:
                self.cleanup_session(session_id)


speaking_controller = SpeakingController()
