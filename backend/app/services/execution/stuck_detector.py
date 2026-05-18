import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class StuckDetector:
    """卡死检测器 — 基于心跳分析检测卡死的任务"""

    def __init__(
        self,
        heartbeat_threshold_seconds: float = 120.0,
        check_interval_seconds: float = 30.0
    ):
        self._heartbeat_threshold = heartbeat_threshold_seconds
        self._check_interval = check_interval_seconds
        self._monitor_task: Optional[asyncio.Task] = None
        self._running: bool = False

    async def start_monitoring(self) -> None:
        if self._running:
            return
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(f"StuckDetector started (threshold={self._heartbeat_threshold}s, interval={self._check_interval}s)")

    async def stop_monitoring(self) -> None:
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        logger.info("StuckDetector stopped")

    async def _monitor_loop(self) -> None:
        while self._running:
            try:
                stuck_tasks = await self.check_stuck_tasks()
                for stuck in stuck_tasks:
                    await self._handle_stuck_task(stuck)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in stuck detection loop")
            await asyncio.sleep(self._check_interval)

    async def check_stuck_tasks(self) -> List[Dict[str, Any]]:
        from app.services.agent.agent_executor import agent_executor

        stuck = []
        now = datetime.now()
        threshold = timedelta(seconds=self._heartbeat_threshold)

        running = agent_executor.get_running_tasks()
        for exec_status in running:
            if exec_status.get("status") != "running":
                continue

            last_heartbeat = exec_status.get("last_heartbeat")
            if last_heartbeat is None:
                started_at = exec_status.get("started_at")
                if started_at:
                    started = datetime.fromisoformat(started_at)
                    if now - started > threshold:
                        stuck.append({
                            "task_id": exec_status["task_id"],
                            "agent_id": exec_status.get("agent_id", "unknown"),
                            "reason": "no_heartbeat_ever",
                            "elapsed_seconds": (now - started).total_seconds(),
                            "current_step": exec_status.get("current_step", 0),
                            "total_steps": exec_status.get("total_steps", 1),
                        })
                continue

            if isinstance(last_heartbeat, str):
                last_heartbeat = datetime.fromisoformat(last_heartbeat)

            elapsed = (now - last_heartbeat).total_seconds()
            if elapsed > self._heartbeat_threshold:
                stuck.append({
                    "task_id": exec_status["task_id"],
                    "agent_id": exec_status.get("agent_id", "unknown"),
                    "reason": "heartbeat_timeout",
                    "elapsed_seconds": elapsed,
                    "last_heartbeat": last_heartbeat.isoformat() if isinstance(last_heartbeat, datetime) else str(last_heartbeat),
                    "current_step": exec_status.get("current_step", 0),
                    "total_steps": exec_status.get("total_steps", 1),
                })

        return stuck

    async def _handle_stuck_task(self, stuck: Dict[str, Any]) -> None:
        from app.services.collaboration.task_board import task_board
        from app.services.collaboration.message_bus import message_bus, Message, MessageType

        task_id = stuck["task_id"]
        agent_id = stuck["agent_id"]
        step_info = f"{stuck.get('current_step', 0)}/{stuck.get('total_steps', 1)}"
        elapsed = stuck.get("elapsed_seconds", 0)

        logger.warning(
            f"Stuck task detected: {task_id} (agent={agent_id}, "
            f"step={step_info}, elapsed={elapsed:.0f}s, reason={stuck['reason']})"
        )

        task_board.add_comment(
            task_id,
            f"[卡死检测] 任务已 {elapsed:.0f} 秒无响应 "
            f"(agent: {agent_id}, 步骤: {step_info})",
            "stuck_detector"
        )

        await message_bus.broadcast(Message(
            sender_id="stuck_detector",
            sender_name="Stuck Detector",
            content=f"任务 {task_id} (agent: {agent_id}) 疑似卡死 - {elapsed:.0f}秒无响应",
            message_type=MessageType.SYSTEM
        ))

    @property
    def is_running(self) -> bool:
        return self._running


stuck_detector = StuckDetector()
