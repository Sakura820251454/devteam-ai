import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from app.services.execution.task_persistence_service import task_persistence_service
from app.services.shared.prompt_registry import registry

logger = logging.getLogger(__name__)


class CheckpointManager:
    """检查点管理器 — 封装检查点的保存、加载和恢复上下文构建"""

    async def save_checkpoint(
        self,
        task_id: str,
        step_index: int,
        step_name: str,
        messages_snapshot: List[Dict[str, Any]],
        partial_result: str,
        agent_state: Optional[Dict[str, Any]] = None,
    ) -> str:
        """在完成一个步骤后保存检查点"""
        context = {
            "messages_snapshot": messages_snapshot[-10:],
        }
        extra_data = {
            "timestamp": datetime.now().isoformat(),
            "agent_state": agent_state or {},
        }

        checkpoint_id = await task_persistence_service.save_checkpoint(
            task_id=task_id,
            step_index=step_index,
            step_name=step_name,
            context=context,
            partial_result=partial_result,
            extra_data=extra_data,
        )
        logger.debug(f"Checkpoint saved: task={task_id}, step={step_index}, id={checkpoint_id}")
        return checkpoint_id

    async def load_checkpoint(self, task_id: str) -> Optional[Dict[str, Any]]:
        """加载任务的最新检查点"""
        return await task_persistence_service.load_latest_checkpoint(task_id)

    async def list_checkpoints(self, task_id: str) -> List[Dict[str, Any]]:
        """列出任务的所有检查点"""
        return await task_persistence_service.list_checkpoints(task_id)

    def build_resume_context(self, checkpoint: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
        """从检查点构建恢复执行所需的上下文"""
        partial = checkpoint.get("partial_result", "")
        messages = checkpoint.get("context", {}).get("messages_snapshot", [])
        step_name = checkpoint.get("step_name", "")
        step_index = checkpoint.get("step_index", 0)

        resume_prompt = registry.render("execution.checkpoint.resume_context", {
            "step_index": step_index + 1,
            "step_name": step_name,
            "partial": partial,
        })

        return resume_prompt, messages


checkpoint_manager = CheckpointManager()
