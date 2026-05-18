import asyncio
import json
import re
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Callable, Any
from enum import Enum

from app.models.agent import AgentStatus
from app.models.task import Task, TaskStatus
from app.services.collaboration.task_board import task_board
from app.services.collaboration.message_bus import message_bus, Message, MessageType
from app.services.collaboration.speaking_controller import speaking_controller, SpeakingMode
from app.services.agent.agent_service import agent_service
from app.core.llm import Message as LLMMessage
from app.services.llm.llm_service import llm_service
from app.services.execution.task_persistence_service import task_persistence_service
from app.services.execution.checkpoint_manager import checkpoint_manager

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentExecutor:
    def __init__(self):
        self._running_tasks: Dict[str, Dict[str, Any]] = {}
        self._agent_tasks: Dict[str, str] = {}
        self._execution_handlers: Dict[str, Callable] = {}
        self._async_task_handles: Dict[str, asyncio.Task] = {}
        self._cancellation_tokens: Dict[str, asyncio.Event] = {}
        self._lock = asyncio.Lock()
        self._global_paused: bool = False
        self._step_timeout: float = 120.0

    async def assign_task(
        self,
        task_id: str,
        agent_id: str,
        agent_execute_fn: Callable
    ) -> bool:
        async with self._lock:
            task = task_board.get_task(task_id)
            if not task:
                return False

            if task.status not in [TaskStatus.TODO, TaskStatus.BACKLOG]:
                return False

            self._agent_tasks[agent_id] = task_id
            self._running_tasks[task_id] = {
                "agent_id": agent_id,
                "execute_fn": agent_execute_fn,
                "status": ExecutionStatus.IDLE,
                "started_at": None,
                "completed_at": None,
                "last_heartbeat": None,
                "current_step": 0,
                "total_steps": 1,
            }

            task_board.assign_agents(task_id, [agent_id])
            return True

    async def start_execution(self, task_id: str) -> bool:
        async with self._lock:
            execution = self._running_tasks.get(task_id)
            if not execution:
                return False

            if self._global_paused:
                execution["status"] = ExecutionStatus.PAUSED
                return False

            execution["status"] = ExecutionStatus.RUNNING
            execution["started_at"] = datetime.now()

            task = task_board.get_task(task_id)
            if task:
                try:
                    task_board.change_status(task_id, TaskStatus.IN_PROGRESS, "system")
                except ValueError:
                    pass

            cancellation_token = asyncio.Event()
            self._cancellation_tokens[task_id] = cancellation_token
            task_handle = asyncio.create_task(
                self._execute_task(task_id, cancellation_token)
            )
            self._async_task_handles[task_id] = task_handle
            return True

    async def _execute_task(self, task_id: str, cancellation_token: asyncio.Event) -> None:
        execution = self._running_tasks.get(task_id)
        if not execution:
            return

        task = task_board.get_task(task_id)
        if not task:
            return

        msg = Message(
            sender_id="system",
            sender_name="System",
            channel=f"task:{task_id}",
            content=f"Agent {execution['agent_id']} 开始执行任务: {task.title}",
            message_type=MessageType.SYSTEM
        )
        await message_bus.send_to_task(msg, task_id)

        try:
            if cancellation_token.is_set():
                raise asyncio.CancelledError("Task cancelled before execution")

            result = await execution["execute_fn"](task)

            if result.get("success", False):
                execution["status"] = ExecutionStatus.COMPLETED
                task_board.change_status(task_id, TaskStatus.REVIEW, "system")
                task_board.add_comment(task_id, f"任务完成: {result.get('summary', '')}", "system")
            else:
                execution["status"] = ExecutionStatus.FAILED
                task_board.add_comment(task_id, f"任务失败: {result.get('error', 'Unknown error')}", "system")

        except asyncio.CancelledError:
            execution["status"] = ExecutionStatus.PAUSED
            task_board.add_comment(task_id, "任务被暂停/取消", "system")
            task_board.change_status(task_id, TaskStatus.PAUSED, "system")

        except Exception as e:
            execution["status"] = ExecutionStatus.FAILED
            task_board.add_comment(task_id, f"执行异常: {str(e)}", "system")

        finally:
            execution["completed_at"] = datetime.now()
            self._async_task_handles.pop(task_id, None)
            self._cancellation_tokens.pop(task_id, None)

    async def execute_task_with_agent(self, task_id: str, agent_id: str) -> Dict[str, Any]:
        task = task_board.get_task(task_id)
        if not task:
            return {"success": False, "error": "Task not found"}

        agent = agent_service.get_agent(agent_id)
        if not agent:
            return {"success": False, "error": "Agent not found"}

        cancellation_token = asyncio.Event()
        self._cancellation_tokens[task_id] = cancellation_token

        self._running_tasks[task_id] = {
            "agent_id": agent_id,
            "status": ExecutionStatus.RUNNING,
            "started_at": datetime.now(),
            "last_heartbeat": datetime.now(),
            "current_step": 0,
            "total_steps": 1,
        }

        task_board.change_status(task_id, TaskStatus.IN_PROGRESS, agent_id)

        msg = Message(
            sender_id=agent_id,
            sender_name=agent.get("name", "Agent"),
            channel=f"task:{task_id}",
            content=f"开始执行任务: {task.title}",
            message_type=MessageType.SYSTEM
        )
        await message_bus.send_to_task(msg, task_id)

        try:
            if cancellation_token.is_set():
                raise asyncio.CancelledError("Task cancelled before execution")

            checkpoint = await checkpoint_manager.load_checkpoint(task_id)
            if checkpoint and checkpoint.get("step_index", 0) > 0:
                result = await self._execute_task_with_steps(
                    task, agent, cancellation_token, start_from_step=checkpoint["step_index"]
                )
            else:
                result = await self._execute_task_with_steps(
                    task, agent, cancellation_token, start_from_step=0
                )

            if result.get("success", False):
                task_board.change_status(task_id, TaskStatus.REVIEW, agent_id)
                self._running_tasks[task_id]["status"] = ExecutionStatus.COMPLETED
                return result
            else:
                self._running_tasks[task_id]["status"] = ExecutionStatus.FAILED
                return result

        except asyncio.CancelledError:
            self._running_tasks[task_id]["status"] = ExecutionStatus.PAUSED
            task_board.add_comment(task_id, "任务被暂停/取消", "system")
            task_board.change_status(task_id, TaskStatus.PAUSED, "system")
            return {"success": False, "error": "Task cancelled", "paused": True}

        except Exception as e:
            self._running_tasks[task_id]["status"] = ExecutionStatus.FAILED
            task_board.add_comment(task_id, f"执行失败: {str(e)}", agent_id)
            return {"success": False, "error": str(e)}

        finally:
            self._cancellation_tokens.pop(task_id, None)

    async def _execute_task_with_steps(
        self,
        task: Task,
        agent: Dict[str, Any],
        cancellation_token: asyncio.Event,
        start_from_step: int = 0
    ) -> Dict[str, Any]:
        task_id = task.id
        agent_id = agent.get("id", "unknown")
        execution = self._running_tasks.get(task_id, {})

        steps = await self._plan_task_steps(task, agent)
        if not steps:
            return await self._fallback_single_execution(task, agent, cancellation_token)

        total_steps = len(steps)
        execution["total_steps"] = total_steps
        execution["current_step"] = start_from_step

        await task_persistence_service.save_execution(
            task_id=task_id,
            agent_id=agent_id,
            status="running",
            total_steps=total_steps,
            current_step_index=start_from_step,
        )

        accumulated_output = ""
        system_prompt = agent.get("system_prompt", "你是一个专业的开发团队成员。")

        for step_idx in range(start_from_step, total_steps):
            if cancellation_token.is_set():
                raise asyncio.CancelledError("Task cancelled at step boundary")

            step = steps[step_idx]
            step_name = step.get("name", f"步骤 {step_idx + 1}")
            execution["current_step"] = step_idx
            self._send_heartbeat(task_id)

            task_board.add_comment(
                task_id,
                f"[{step_idx + 1}/{total_steps}] 执行步骤: {step_name}",
                agent_id
            )

            step_prompt = self._build_step_prompt(task, step, accumulated_output, step_idx, total_steps)
            llm_messages = [
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=step_prompt)
            ]

            try:
                response = await llm_service.chat(
                    llm_messages,
                    agent=None,
                    track_cost=True,
                    task_id=task_id,
                    timeout=self._step_timeout,
                    cancellation_token=cancellation_token
                )

                step_result = response.content
                accumulated_output += f"\n\n## 步骤 {step_idx + 1}: {step_name}\n{step_result}"

                await self._save_checkpoint(task_id, step_idx, step_name, llm_messages, accumulated_output)
                await task_persistence_service.update_heartbeat(task_id, step_idx, total_steps)
                self._send_heartbeat(task_id)

            except asyncio.TimeoutError:
                await self._save_checkpoint(task_id, step_idx, step_name, llm_messages, accumulated_output)
                raise

        execution["current_step"] = total_steps
        execution["total_steps"] = total_steps
        self._send_heartbeat(task_id)

        return {
            "success": True,
            "result": accumulated_output,
            "summary": self._summarize_task_result(task.title, accumulated_output)
        }

    async def _plan_task_steps(self, task: Task, agent: Dict[str, Any]) -> List[Dict[str, Any]]:
        planning_prompt = f"""请将以下任务分解为 3-8 个具体的执行步骤。每个步骤应独立可执行、有明确的产出。

任务标题: {task.title}
任务描述: {task.description}

请严格按以下 JSON 格式输出（不要输出其他内容）:
{{
  "steps": [
    {{
      "name": "步骤名称",
      "description": "此步骤要做什么",
      "expected_output": "此步骤的预期产出"
    }}
  ]
}}"""

        try:
            llm_messages = [
                LLMMessage(role="system", content="你是一个任务规划专家。请将复杂任务拆解为具体执行步骤。只输出 JSON。"),
                LLMMessage(role="user", content=planning_prompt)
            ]
            response = await llm_service.chat(llm_messages, track_cost=True, task_id=task.id, timeout=30.0)
            steps = self._parse_steps_from_response(response.content)
            if steps and len(steps) >= 1:
                return steps
        except Exception as e:
            logger.warning(f"Step planning failed for task {task.id}: {e}")

        return []

    def _parse_steps_from_response(self, response_text: str) -> List[Dict[str, Any]]:
        json_match = re.search(r'\{[\s\S]*"steps"[\s\S]*\}', response_text)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return data.get("steps", [])
            except json.JSONDecodeError:
                pass

        lines = response_text.strip().split("\n")
        steps = []
        for line in lines:
            match = re.match(r'^\d+[\.\)]\s*(.+)', line.strip())
            if match:
                steps.append({"name": match.group(1), "description": "", "expected_output": ""})

        return steps

    def _build_step_prompt(
        self,
        task: Task,
        step: Dict[str, Any],
        accumulated_output: str,
        step_idx: int,
        total_steps: int
    ) -> str:
        step_name = step.get("name", f"步骤 {step_idx + 1}")
        step_desc = step.get("description", "")
        expected = step.get("expected_output", "")

        prompt = f"""执行以下任务的第 {step_idx + 1}/{total_steps} 步:

任务: {task.title}
步骤: {step_name}
步骤说明: {step_desc}
预期产出: {expected}
"""

        if accumulated_output:
            prompt += f"""
前序步骤已完成的工作:
{accumulated_output}

请基于以上已完成的工作，继续执行当前步骤。不要重复已完成的内容。
"""
        else:
            prompt += "\n这是第一个步骤，请从头开始执行。\n"

        return prompt

    async def _save_checkpoint(
        self,
        task_id: str,
        step_index: int,
        step_name: str,
        messages: List[LLMMessage],
        partial_result: str
    ) -> None:
        try:
            await checkpoint_manager.save_checkpoint(
                task_id=task_id,
                step_index=step_index,
                step_name=step_name,
                messages_snapshot=[m.to_dict() for m in messages],
                partial_result=partial_result,
            )
            await task_persistence_service.save_execution(
                task_id=task_id,
                agent_id=self._running_tasks.get(task_id, {}).get("agent_id", ""),
                status="running",
                current_step_index=step_index,
                accumulated_result=partial_result,
            )
        except Exception as e:
            logger.warning(f"Failed to save checkpoint for task {task_id}: {e}")

    async def _fallback_single_execution(
        self,
        task: Task,
        agent: Dict[str, Any],
        cancellation_token: asyncio.Event
    ) -> Dict[str, Any]:
        execution_prompt = self._build_task_execution_prompt(task, agent)
        system_prompt = agent.get("system_prompt", "你是一个专业的开发团队成员，擅长完成各种开发任务。")

        llm_messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=execution_prompt)
        ]

        response = await llm_service.chat(
            llm_messages,
            agent=None,
            track_cost=True,
            task_id=task.id,
            timeout=self._step_timeout,
            cancellation_token=cancellation_token
        )

        if cancellation_token.is_set():
            raise asyncio.CancelledError("Task cancelled after LLM response")

        result_content = response.content
        task_board.add_comment(task.id, f"执行结果:\n{result_content}", agent.get("id", "system"))

        return {
            "success": True,
            "result": result_content,
            "summary": self._summarize_task_result(task.title, result_content)
        }

    def _build_task_execution_prompt(self, task: Task, agent: Dict[str, Any]) -> str:
        return f"""请执行以下任务:

任务标题: {task.title}
任务描述: {task.description}

任务标签: {', '.join(task.tags) if task.tags else '无'}

请根据任务描述和你的角色，完成任务并给出详细的执行结果。

如果需要编写代码，请提供完整的代码实现。
如果需要设计架构，请提供详细的架构说明。
如果需要分析问题，请提供深入的分析报告。

请确保：
1. 严格按照任务描述执行
2. 提供具体的实现方案
3. 说明关键的设计决策
4. 给出可能的改进建议

执行完成后，请总结任务完成情况。"""

    def _summarize_task_result(self, task_title: str, result: str) -> str:
        if len(result) > 500:
            return f"{task_title}: {result[:200]}..."
        return f"{task_title}: {result}"

    async def pause_execution(self, task_id: str) -> bool:
        async with self._lock:
            execution = self._running_tasks.get(task_id)
            if not execution:
                return False

            execution["status"] = ExecutionStatus.PAUSED

            if task_id in self._cancellation_tokens:
                self._cancellation_tokens[task_id].set()

            if task_id in self._async_task_handles:
                self._async_task_handles[task_id].cancel()

            task = task_board.get_task(task_id)
            if task:
                task_board.change_status(task_id, TaskStatus.PAUSED, "system")
            return True

    async def resume_execution(self, task_id: str) -> bool:
        async with self._lock:
            execution = self._running_tasks.get(task_id)
            if not execution:
                db_execution = await task_persistence_service.load_execution(task_id)
                if db_execution:
                    execution = {
                        "agent_id": db_execution["agent_id"],
                        "status": ExecutionStatus(db_execution["status"]),
                        "started_at": db_execution["started_at"],
                        "last_heartbeat": db_execution["last_heartbeat"],
                        "current_step": db_execution["current_step_index"],
                        "total_steps": db_execution["total_steps"],
                    }
                    self._running_tasks[task_id] = execution
                else:
                    return False

            if execution["status"] not in [ExecutionStatus.PAUSED, ExecutionStatus.FAILED]:
                return False

            execution["status"] = ExecutionStatus.RUNNING
            self._send_heartbeat(task_id)

            cancellation_token = asyncio.Event()
            self._cancellation_tokens[task_id] = cancellation_token
            task_handle = asyncio.create_task(
                self._execute_task(task_id, cancellation_token)
            )
            self._async_task_handles[task_id] = task_handle
            return True

    async def cancel_execution(self, task_id: str) -> bool:
        async with self._lock:
            execution = self._running_tasks.get(task_id)
            if not execution:
                return False

            execution["status"] = ExecutionStatus.CANCELLED

            if task_id in self._cancellation_tokens:
                self._cancellation_tokens[task_id].set()

            if task_id in self._async_task_handles:
                self._async_task_handles[task_id].cancel()

            task = task_board.get_task(task_id)
            if task:
                try:
                    task_board.change_status(task_id, TaskStatus.CANCELLED, "system")
                except ValueError:
                    try:
                        task_board.change_status(task_id, TaskStatus.BLOCKED, "system")
                        task_board.change_status(task_id, TaskStatus.CANCELLED, "system")
                    except ValueError:
                        pass

            agent_id = execution["agent_id"]
            if agent_id in self._agent_tasks:
                del self._agent_tasks[agent_id]

            self._async_task_handles.pop(task_id, None)
            self._cancellation_tokens.pop(task_id, None)
            return True

    async def pause_all(self) -> None:
        async with self._lock:
            self._global_paused = True
            for task_id, execution in self._running_tasks.items():
                if execution["status"] == ExecutionStatus.RUNNING:
                    execution["status"] = ExecutionStatus.PAUSED
                    if task_id in self._cancellation_tokens:
                        self._cancellation_tokens[task_id].set()
                    if task_id in self._async_task_handles:
                        self._async_task_handles[task_id].cancel()
                    task = task_board.get_task(task_id)
                    if task:
                        task_board.change_status(task_id, TaskStatus.PAUSED, "system")

    async def resume_all(self) -> None:
        async with self._lock:
            self._global_paused = False
            for task_id, execution in self._running_tasks.items():
                if execution["status"] == ExecutionStatus.PAUSED:
                    await self.start_execution(task_id)

    def get_execution_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        execution = self._running_tasks.get(task_id)
        if not execution:
            return None

        return {
            "task_id": task_id,
            "agent_id": execution["agent_id"],
            "status": execution["status"].value,
            "started_at": execution["started_at"].isoformat() if execution["started_at"] else None,
            "completed_at": execution["completed_at"].isoformat() if execution["completed_at"] else None,
            "last_heartbeat": execution.get("last_heartbeat").isoformat() if execution.get("last_heartbeat") else None,
            "current_step": execution.get("current_step", 0),
            "total_steps": execution.get("total_steps", 1),
        }

    def _send_heartbeat(self, task_id: str) -> None:
        execution = self._running_tasks.get(task_id)
        if execution:
            execution["last_heartbeat"] = datetime.now()

    def get_agent_current_task(self, agent_id: str) -> Optional[str]:
        return self._agent_tasks.get(agent_id)

    def get_running_tasks(self) -> List[Dict[str, Any]]:
        return [
            self.get_execution_status(task_id)
            for task_id in self._running_tasks.keys()
            if self.get_execution_status(task_id)
        ]

    def is_global_paused(self) -> bool:
        return self._global_paused


agent_executor = AgentExecutor()
