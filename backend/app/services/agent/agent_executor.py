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
from app.services.project.workspace_manager import workspace_manager
from app.services.shared.prompt_registry import registry

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
        self._project_paused: Dict[str, bool] = {}
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

            task = task_board.get_task(task_id)
            project_id = task.project_id if task else ""
            if project_id and self._project_paused.get(project_id, False):
                execution["status"] = ExecutionStatus.PAUSED
                return False

            execution["status"] = ExecutionStatus.RUNNING
            execution["started_at"] = datetime.now()

            task = task_board.get_task(task_id)
            if task:
                try:
                    await task_board.change_status(task_id, TaskStatus.IN_PROGRESS, "system")
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
                await task_board.change_status(task_id, TaskStatus.REVIEW, "system")
                await task_board.add_comment(task_id, f"任务完成: {result.get('summary', '')}", "system")
            else:
                execution["status"] = ExecutionStatus.FAILED
                await task_board.add_comment(task_id, f"任务失败: {result.get('error', 'Unknown error')}", "system")

        except asyncio.CancelledError:
            execution["status"] = ExecutionStatus.PAUSED
            await task_board.add_comment(task_id, "任务被暂停/取消", "system")
            await task_board.change_status(task_id, TaskStatus.PAUSED, "system")

        except Exception as e:
            execution["status"] = ExecutionStatus.FAILED
            await task_board.add_comment(task_id, f"执行异常: {str(e)}", "system")

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

        # 验证 Agent 属于该任务所在项目
        task_project = task.project_id
        if task_project:
            agent_project = agent_service.get_agent_project(agent_id)
            if agent_project and agent_project != task_project:
                return {"success": False, "error": f"Agent {agent_id} 属于项目 {agent_project}，无法执行项目 {task_project} 的任务"}

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

        # 状态转换: BACKLOG -> TODO -> IN_PROGRESS
        if task.status == TaskStatus.BACKLOG:
            await task_board.change_status(task_id, TaskStatus.TODO, agent_id)
        await task_board.change_status(task_id, TaskStatus.IN_PROGRESS, agent_id)

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
                await task_board.change_status(task_id, TaskStatus.REVIEW, agent_id)
                self._running_tasks[task_id]["status"] = ExecutionStatus.COMPLETED
                return result
            else:
                self._running_tasks[task_id]["status"] = ExecutionStatus.FAILED
                return result

        except asyncio.CancelledError:
            self._running_tasks[task_id]["status"] = ExecutionStatus.PAUSED
            await task_board.add_comment(task_id, "任务被暂停/取消", "system")
            await task_board.change_status(task_id, TaskStatus.PAUSED, "system")
            return {"success": False, "error": "Task cancelled", "paused": True}

        except Exception as e:
            self._running_tasks[task_id]["status"] = ExecutionStatus.FAILED
            await task_board.add_comment(task_id, f"执行失败: {str(e)}", agent_id)
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

            await task_board.add_comment(
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

                # 提取代码块写入 workspace（按任务名去重，每次覆盖旧版）
                self._save_artifacts_from_response(task, step_result)

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
        planning_prompt = registry.render("agent.executor.plan_steps", {
            "task_title": task.title,
            "task_description": task.description,
        })

        try:
            llm_messages = [
                LLMMessage(role="system", content=registry.render("agent.executor.plan_steps_system", {})),
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
        step_index = step_idx + 1

        if accumulated_output:
            return registry.render("agent.executor.step_prompt.continue", {
                "task_title": task.title,
                "step_index": step_index,
                "total_steps": total_steps,
                "step_name": step_name,
                "step_description": step_desc,
                "expected_output": expected,
                "accumulated_output": accumulated_output,
            })
        else:
            return registry.render("agent.executor.step_prompt.first", {
                "task_title": task.title,
                "step_index": step_index,
                "total_steps": total_steps,
                "step_name": step_name,
                "step_description": step_desc,
                "expected_output": expected,
            })

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
        system_prompt = agent.get("system_prompt") or registry.render("agent.executor.fallback_system", {})

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
        self._save_artifacts_from_response(task, result_content, task.title.replace(" ", "_"))
        await task_board.add_comment(task.id, f"执行结果:\n{result_content}", agent.get("id", "system"))

        return {
            "success": True,
            "result": result_content,
            "summary": self._summarize_task_result(task.title, result_content)
        }

    def _build_task_execution_prompt(self, task: Task, agent: Dict[str, Any]) -> str:
        task_tags = ", ".join(task.tags) if task.tags else "无"
        return registry.render("agent.executor.task_execution", {
            "task_title": task.title,
            "task_description": task.description,
            "task_tags": task_tags,
        })

    def _summarize_task_result(self, task_title: str, result: str) -> str:
        if len(result) > 500:
            return f"{task_title}: {result[:200]}..."
        return f"{task_title}: {result}"

    @staticmethod
    def _save_artifacts_from_response(task, response_text: str) -> None:
        """从 LLM 响应中提取代码块，写入项目 workspace。

        文件名基于任务标题 + 代码内容（类名/函数名）组合生成。
        同一步骤重试时，相同文件名自然覆盖旧版，不会留下迭代残渣。
        不同步骤产生不同文件（不同类/函数名），互不干扰。
        """
        import re

        project_id = getattr(task, "project_id", None)
        if not project_id:
            return

        code_blocks = re.findall(r"```(\w*)\n(.*?)```", response_text, re.DOTALL)
        if not code_blocks:
            return

        from app.services.project.workspace_manager import workspace_manager

        ext_map = {
            "python": ".py", "py": ".py",
            "javascript": ".js", "js": ".js", "jsx": ".jsx",
            "typescript": ".ts", "ts": ".ts", "tsx": ".tsx",
            "html": ".html", "css": ".css", "scss": ".scss",
            "json": ".json", "yaml": ".yaml", "yml": ".yml",
            "sql": ".sql", "sh": ".sh", "bash": ".sh",
            "dockerfile": "", "docker": "",
            "markdown": ".md", "md": ".md",
        }

        # Sanitize task title for use in filenames
        task_title = getattr(task, "title", "unknown") or "unknown"
        safe_title = re.sub(r'[\s\\/:*?"<>|]+', '_', task_title).strip('_')

        stage_key = "coding"

        for i, (lang, code) in enumerate(code_blocks):
            code = code.strip()
            if not code:
                continue
            lang_lower = lang.strip().lower()
            ext = ext_map.get(lang_lower, ".txt")

            # Try to extract a meaningful name from the code block
            code_name = _extract_code_name(code, lang_lower)
            if code_name:
                filename = f"{safe_title}_{code_name}{ext}"
            elif len(code_blocks) == 1:
                filename = f"{safe_title}{ext}"
            else:
                filename = f"{safe_title}_{i + 1}{ext}"

            try:
                workspace_manager.add_artifact(project_id, stage_key, filename, code)
            except Exception as e:
                logger.warning(f"Failed to save artifact {filename}: {e}")


def _extract_code_name(code: str, lang: str) -> str:
    """从代码块中提取有意义的名称（类名或函数名）作为文件名片段。"""
    import re

    if lang in ("python", "py"):
        m = re.search(r'class\s+(\w+)', code)
        if m:
            return m.group(1).lower()
        m = re.search(r'def\s+(\w+)', code)
        if m:
            return m.group(1).lower()

    if lang in ("typescript", "ts", "tsx", "javascript", "js", "jsx"):
        m = re.search(r'(?:export\s+)?class\s+(\w+)', code)
        if m:
            return m.group(1).lower()
        m = re.search(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)', code)
        if m:
            return m.group(1).lower()
        m = re.search(r'(?:const|let|var)\s+(\w+)\s*=', code)
        if m:
            return m.group(1).lower()

    return ""

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

    async def pause_project(self, project_id: str) -> None:
        async with self._lock:
            self._project_paused[project_id] = True
            for task_id, execution in self._running_tasks.items():
                if execution["status"] == ExecutionStatus.RUNNING:
                    task = task_board.get_task(task_id)
                    if task and task.project_id == project_id:
                        execution["status"] = ExecutionStatus.PAUSED
                        if task_id in self._cancellation_tokens:
                            self._cancellation_tokens[task_id].set()
                        if task_id in self._async_task_handles:
                            self._async_task_handles[task_id].cancel()
                        task_board.change_status(task_id, TaskStatus.PAUSED, "system")

    async def resume_project(self, project_id: str) -> None:
        async with self._lock:
            self._project_paused[project_id] = False
            for task_id, execution in self._running_tasks.items():
                if execution["status"] == ExecutionStatus.PAUSED:
                    task = task_board.get_task(task_id)
                    if task and task.project_id == project_id:
                        await self.start_execution(task_id)

    async def pause_all(self) -> None:
        """向后兼容：暂停所有项目的执行"""
        async with self._lock:
            for task_id, execution in self._running_tasks.items():
                if execution["status"] == ExecutionStatus.RUNNING:
                    task = task_board.get_task(task_id)
                    pid = task.project_id if task else ""
                    self._project_paused[pid] = True
                    execution["status"] = ExecutionStatus.PAUSED
                    if task_id in self._cancellation_tokens:
                        self._cancellation_tokens[task_id].set()
                    if task_id in self._async_task_handles:
                        self._async_task_handles[task_id].cancel()
                    if task:
                        task_board.change_status(task_id, TaskStatus.PAUSED, "system")

    async def resume_all(self) -> None:
        """向后兼容：恢复所有项目的执行"""
        async with self._lock:
            for pid in list(self._project_paused.keys()):
                self._project_paused[pid] = False
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
        return any(self._project_paused.values())

    def is_project_paused(self, project_id: str) -> bool:
        return self._project_paused.get(project_id, False)

    # ========== 可执行反馈 (Executable Feedback) ==========

    def _build_feedback_context(
        self,
        task: Task,
        agent: Dict[str, Any],
        error_info: str = "",
    ) -> str:
        """
        构建可执行反馈上下文。
        基于 MetaGPT 的"可执行反馈"理念：agent 出错时不是瞎猜，
        而是对照公共历史文档和消息，基于共享上下文修正。
        """
        parts = []
        project_id = getattr(task, 'project_id', '')

        if not project_id:
            return ""

        # 1. 获取项目元数据（stage 顺序、产出物要求）
        try:
            workspace = workspace_manager.get_workspace(project_id)
            if workspace:
                stages = workspace.get("stages", [])
                template = workspace.get("template", {})

                if stages:
                    stage_order = [s.get("key", s.get("label", "")) for s in stages]

                    # 当前任务所属阶段
                    current_stage = getattr(task, 'stage', '')
                    if not current_stage and hasattr(task, 'tags'):
                        for tag in task.tags:
                            if tag in stage_order:
                                current_stage = tag
                                break

                    parts.append("## 项目阶段与产出物要求")
                    for s in stages:
                        sk = s.get("key", s.get("label", ""))
                        marker = " ← 当前阶段" if sk == current_stage else ""
                        expected = s.get("expected_artifact", "")
                        parts.append(f"- **{s.get('label', sk)}**{marker}: 产出物={expected or '待定'}")

                    # 2. 前置阶段产出物
                    if current_stage and stage_order:
                        try:
                            prereq_artifacts = workspace_manager.get_prerequisite_artifacts(
                                project_id, current_stage, stage_order
                            )
                            if prereq_artifacts:
                                parts.append("\n## 前置阶段产出物（供参考）")
                                for stage_key, files in prereq_artifacts.items():
                                    stage_label = next(
                                        (s.get("label", stage_key) for s in stages if s.get("key") == stage_key),
                                        stage_key,
                                    )
                                    parts.append(f"\n### {stage_label}")
                                    for fname, content in files.items():
                                        parts.append(f"**{fname}**:\n```\n{content[:2000]}\n```")
                        except Exception:
                            pass

                    # 3. 前置阶段消息摘要
                    if current_stage and stage_order:
                        try:
                            prereq_msgs = message_bus.get_prerequisite_context(
                                project_id, current_stage, stage_order
                            )
                            if prereq_msgs:
                                parts.append("\n## 前置阶段讨论摘要（最近 10 条）")
                                for msg in prereq_msgs[-10:]:
                                    sender = msg.metadata.get("sender_name", msg.sender_name)
                                    content_preview = msg.content[:300]
                                    parts.append(f"- **{sender}**: {content_preview}")
                        except Exception:
                            pass
        except Exception:
            pass

        # 4. 当前任务历史记录
        try:
            history = getattr(task, 'status_history', []) or []
            if history:
                parts.append("\n## 当前任务历史记录（最近 5 条）")
                for h in history[-5:]:
                    entry = f"{h.get('timestamp', '')} [{h.get('by', 'system')}] {h.get('from', '')}→{h.get('to', '')}"
                    parts.append(f"- {entry}")
        except Exception:
            pass

        # 5. 错误信息
        if error_info:
            parts.append(f"\n## 上次执行错误\n{error_info[:1000]}")

        if parts:
            parts.insert(0, "## 可执行反馈上下文\n请基于以下上下文修正执行方案，不要猜测：")

        return "\n".join(parts)

    async def execute_task_with_feedback(
        self,
        task_id: str,
        agent_id: str,
    ) -> Dict[str, Any]:
        """
        带可执行反馈的任务执行。
        首次执行失败后，收集上下文自动重试一次。
        """
        task = task_board.get_task(task_id)
        agent = agent_service.get_agent(agent_id) if agent_id else None

        # 首次执行
        result = await self.execute_task_with_agent(task_id, agent_id)

        if result.get("success", False) or result.get("paused", False):
            return result

        # 首次失败 → 收集反馈上下文 → 注入提示词 → 重试
        if task and agent:
            error_info = result.get("error", "Unknown error")
            feedback_context = self._build_feedback_context(task, agent, error_info)

            if feedback_context:
                task_board.add_comment(task_id, "首次执行失败，正在基于共享上下文重试...", "system")

                # 将反馈上下文注入到任务描述中用于重试
                original_desc = task.description or ""
                enhanced_desc = f"{original_desc}\n\n{feedback_context}"

                # 临时修改描述以便重试时使用上下文
                try:
                    task.description = enhanced_desc
                    retry_result = await self.execute_task_with_agent(task_id, agent_id)
                    task.description = original_desc  # 恢复

                    if retry_result.get("success", False):
                        task_board.add_comment(task_id, "基于上下文反馈重试成功", "system")
                    else:
                        task_board.add_comment(
                            task_id,
                            f"重试仍失败: {retry_result.get('error', 'Unknown')}",
                            "system",
                        )
                    return retry_result
                except Exception:
                    task.description = original_desc  # 确保恢复

        return result


agent_executor = AgentExecutor()
