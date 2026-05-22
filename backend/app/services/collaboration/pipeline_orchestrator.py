import asyncio
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Callable, Any
from enum import Enum

from app.models.agent import Agent
from app.models.task import TaskStatus, Priority, RiskLevel
from app.services.collaboration.project_service import project_service, ProjectPhase
from app.services.collaboration.task_board import task_board
from app.services.agent.agent_service import agent_service
from app.services.collaboration.message_bus import message_bus, Message, MessageType
from app.services.collaboration.speaking_controller import speaking_controller, SpeakingMode
from app.services.agent.agent_executor import agent_executor, ExecutionStatus
from app.core.llm import Message as LLMMessage
from app.services.llm.llm_service import llm_service
from app.services.shared.prompt_registry import registry
from app.models.agent_context import AgentContextFactory
from app.services.security.guard import security_guard, OperationType
from app.services.security.audit import audit_logger, AuditAction


class PipelineStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStage(str, Enum):
    REQUIREMENT_ANALYSIS = "requirement_analysis"
    TASK_BREAKDOWN = "task_breakdown"
    TASK_EXECUTION = "task_execution"
    REVIEW = "review"
    COMPLETED = "completed"


class Pipeline:
    def __init__(self):
        self.id: str = str(uuid.uuid4())
        self.project_id: str = ""
        self.name: str = ""
        self.status: PipelineStatus = PipelineStatus.IDLE
        self.current_stage: PipelineStage = PipelineStage.REQUIREMENT_ANALYSIS
        self.created_at: datetime = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.agents: List[str] = []
        self.task_ids: List[str] = []
        self.progress: float = 0.0
        self.logs: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {}
        self.paused: bool = False
        self.stop_requested: bool = False
        self.team_config: Dict[str, Any] = {}
        self.agent_roles: Dict[str, str] = {}  # agent_id -> inferred role label
        self._assignment_queue: List[str] = []  # FIFO queue for round-robin assignment

    def add_log(self, stage: str, message: str, level: str = "info") -> None:
        entry = {
            "stage": stage,
            "message": message,
            "level": level,
            "timestamp": datetime.now().isoformat()
        }
        self.logs.append(entry)

        # Persist to workspace log file on disk
        if self.project_id:
            try:
                from app.services.project.workspace_manager import workspace_manager
                workspace_manager.add_log(self.project_id, level, stage, message)
            except Exception:
                pass  # best-effort: don't break pipeline if workspace logging fails


class PipelineOrchestrator:
    def __init__(self):
        self._pipelines: Dict[str, Pipeline] = {}
        self._active_pipelines: Dict[str, str] = {}  # project_id -> pipeline_id
        self._execution_tasks: Dict[str, asyncio.Task] = {}
        self._human_intervention_queue: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._db = None

    def initialize(self, db_service) -> None:
        self._db = db_service

    async def load_all(self) -> None:
        if self._db:
            loaded = await self._db.load_all()
            for pid, pipeline in loaded.items():
                self._pipelines[pid] = pipeline
                if pipeline.status == PipelineStatus.RUNNING:
                    self._active_pipelines[pipeline.project_id] = pid

    async def create_pipeline(
        self,
        project_id: str,
        name: str,
        agent_ids: List[str],
        team_config: Dict[str, Any] = None,
    ) -> Pipeline:
        # 验证所有 Agent 均空闲，并分配到项目
        for agent_id in agent_ids:
            if not agent_service.assign_agent_to_project(agent_id, project_id):
                already_in = agent_service.get_agent_project(agent_id)
                raise ValueError(f"Agent {agent_id} 已在项目 {already_in} 中，无法分配到项目 {project_id}")

        async with self._lock:
            pipeline = Pipeline()
            pipeline.project_id = project_id
            pipeline.name = name
            pipeline.agents = agent_ids
            pipeline.team_config = team_config or {}

            # 使用 agent name 作为角色标签（配置阶段不预设职位）
            for agent_id in agent_ids:
                agent = agent_service.get_agent(agent_id)
                if agent:
                    pipeline.agent_roles[agent_id] = agent.get("name", agent_id)

            self._pipelines[pipeline.id] = pipeline
            self.add_log(f"流水线创建: {name}", "init")
            if self._db:
                await self._db.save(pipeline)
            return pipeline

    async def start_pipeline(self, pipeline_id: str) -> bool:
        async with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if not pipeline:
                return False

            if pipeline.status == PipelineStatus.RUNNING:
                return False

            project = project_service.get_project(pipeline.project_id)
            if not project:
                return False

            pipeline.status = PipelineStatus.RUNNING
            pipeline.started_at = datetime.now()
            pipeline.current_stage = PipelineStage.REQUIREMENT_ANALYSIS
            self._active_pipelines[pipeline.project_id] = pipeline_id

            asyncio.create_task(self._run_pipeline(pipeline_id))
            if self._db:
                await self._db.save(pipeline)
            return True

    async def _run_pipeline(self, pipeline_id: str) -> None:
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return

        project = project_service.get_project(pipeline.project_id)
        if not project:
            return

        try:
            pipeline.add_log("init", f"流水线启动，项目: {project.name}")

            # 确保 workspace 存在
            from app.services.project.workspace_manager import workspace_manager
            try:
                ws = workspace_manager.get_workspace(pipeline.project_id)
                if not ws:
                    workspace_manager.create_workspace(
                        project_id=pipeline.project_id,
                        name=project.name,
                        description=project.description or "",
                    )
                    pipeline.add_log("init", "Workspace 已创建")
            except Exception as e:
                pipeline.add_log("init", f"Workspace 创建失败: {e}", "warning")

            await self._stage_requirement_analysis(pipeline)
            if self._db:
                await self._db.save(pipeline)

            if pipeline.stop_requested:
                pipeline.status = PipelineStatus.FAILED
                self._cleanup_pipeline_agents(pipeline)
                if self._db:
                    await self._db.save(pipeline)
                return

            await self._stage_task_breakdown(pipeline, project)
            if self._db:
                await self._db.save(pipeline)

            if pipeline.stop_requested:
                pipeline.status = PipelineStatus.FAILED
                self._cleanup_pipeline_agents(pipeline)
                if self._db:
                    await self._db.save(pipeline)
                return

            await self._stage_task_execution(pipeline)
            if self._db:
                await self._db.save(pipeline)

            if pipeline.stop_requested:
                pipeline.status = PipelineStatus.FAILED
                self._cleanup_pipeline_agents(pipeline)
                if self._db:
                    await self._db.save(pipeline)
                return

            await self._stage_review(pipeline)

            pipeline.status = PipelineStatus.COMPLETED
            pipeline.completed_at = datetime.now()
            pipeline.current_stage = PipelineStage.COMPLETED

            await project_service.update_project(pipeline.project_id, status="completed")
            if self._db:
                await self._db.save(pipeline)

        except Exception as e:
            pipeline.status = PipelineStatus.FAILED
            pipeline.add_log("error", f"Pipeline failed: {str(e)}", "error")
            raise
        finally:
            self._cleanup_pipeline_agents(pipeline)
            self._active_pipelines.pop(pipeline.project_id, None)

    def _cleanup_pipeline_agents(self, pipeline: Pipeline) -> None:
        for agent_id in pipeline.agents:
            agent_service.release_agent_from_project(agent_id, pipeline.project_id)

    async def _stage_requirement_analysis(self, pipeline: Pipeline) -> None:
        pipeline.current_stage = PipelineStage.REQUIREMENT_ANALYSIS
        pipeline.add_log("requirement_analysis", "启动多 Agent 需求分析...")

        project = project_service.get_project(pipeline.project_id)
        if not project:
            return

        msg = Message(
            sender_id="system",
            sender_name="Pipeline",
            channel=f"project:{pipeline.project_id}",
            content=f"🔍 启动多 Agent 需求分析: {project.requirements[:200]}...",
            message_type=MessageType.SYSTEM
        )
        await message_bus.broadcast(msg)

        speaking_controller.set_mode(pipeline.id, SpeakingMode.PRIORITY_BASED)
        speaking_controller.set_token_budget(pipeline.id, 100000)

        # 选择参与分析的 agent（PM + 架构师优先）
        participants = self._select_stage_participants(pipeline, ["PM", "架构师"])

        if len(participants) < 2:
            # 不足 2 人 → 回退单 LLM
            pipeline.add_log("requirement_analysis", "参与讨论的 Agent 不足，回退到单 LLM 分析")
            return await self._single_llm_requirement_analysis(pipeline, project)

        try:
            result = await self._run_agent_discussion(
                pipeline=pipeline,
                stage_key="requirement_analysis",
                topic=f"分析项目需求: {project.name}",
                context={
                    "项目名称": project.name,
                    "项目描述": project.description or "无",
                    "需求内容": project.requirements or "无",
                    "分析角度": "需求完整性、技术可行性、潜在风险、改进建议、优先级建议",
                    "团队成员": ", ".join(
                        f"{pipeline.agent_roles.get(aid, aid)}" for aid in participants
                    ),
                },
                agent_ids=participants,
                max_rounds=2,
            )

            # 合并多 agent 观点为完整分析报告
            final_analysis = await self._merge_discussion_into_analysis(result, project)

            pipeline.context["requirement_analysis"] = final_analysis
            pipeline.context["requirement_discussion"] = {
                "transcript": [m.model_dump(mode='json') for m in result.transcript],
                "consensus": result.consensus_reached,
                "participants": participants,
            }

            # 保存需求分析报告到 workspace
            from app.services.project.workspace_manager import workspace_manager
            try:
                workspace_manager.add_artifact(
                    pipeline.project_id, "requirement_analysis",
                    "requirement_analysis.md", final_analysis,
                )
            except Exception:
                pass

            msg = Message(
                sender_id="system",
                sender_name="Pipeline",
                channel=f"project:{pipeline.project_id}",
                content=f"✅ 多 Agent 需求分析完成 ({len(result.transcript)} 条发言, {len(participants)} 人参与)",
                message_type=MessageType.SYSTEM
            )
            await message_bus.broadcast(msg)

            pipeline.add_log("requirement_analysis",
                f"多 Agent 分析完成: {len(result.transcript)} 条发言, 报告 {len(final_analysis)} 字符")

        except Exception as e:
            pipeline.add_log("requirement_analysis", f"Agent 讨论失败: {e}，回退到单 LLM", "warning")
            await self._single_llm_requirement_analysis(pipeline, project)

        pipeline.progress = 0.2

    async def _single_llm_requirement_analysis(self, pipeline: Pipeline, project) -> None:
        """单 LLM 需求分析的兜底方案"""
        analysis_prompt = self._build_requirement_analysis_prompt(project)
        try:
            response = await llm_service.chat(
                messages=[
                    LLMMessage(role="system", content=registry.render("collaboration.pipeline.requirement_analysis_system", {})),
                    LLMMessage(role="user", content=analysis_prompt),
                ],
                track_cost=True,
                task_id=pipeline.project_id,
            )
            pipeline.context["requirement_analysis"] = response.content
            pipeline.add_log("requirement_analysis", f"单 LLM 分析完成: {len(response.content)} 字符")
        except Exception as e:
            pipeline.add_log("requirement_analysis", f"分析失败: {str(e)}", "error")
            pipeline.context["requirement_analysis"] = f"Error: {str(e)}"

    async def _merge_discussion_into_analysis(self, discussion, project) -> str:
        """将多 agent 讨论记录合并为一份完整的需求分析报告"""
        transcript_text = "\n\n".join(
            f"### {dm.agent_name} ({dm.role_label})\n{dm.content}"
            for dm in discussion.transcript
        )

        try:
            response = await llm_service.chat(
                messages=[
                    LLMMessage(
                        role="system",
                        content=registry.render("collaboration.pipeline.merge_analysis_system", {}),
                    ),
                    LLMMessage(
                        role="user",
                        content=registry.render("collaboration.pipeline.merge_analysis", {
                            "project_name": project.name,
                            "project_description": project.description,
                            "requirements": project.requirements,
                            "transcript_text": transcript_text,
                        }),
                    ),
                ],
                track_cost=True,
                task_id=project.id,
            )
            return response.content
        except Exception as e:
            # 合并失败 → 直接拼接讨论记录
            return f"# 需求分析（多 Agent 讨论记录）\n\n{transcript_text}"

    def _build_requirement_analysis_prompt(self, project) -> str:
        return registry.render("collaboration.pipeline.requirement_analysis", {
            "project_name": project.name,
            "project_description": project.description,
            "requirements": project.requirements,
        })

    async def _stage_task_breakdown(self, pipeline: Pipeline, project) -> None:
        pipeline.current_stage = PipelineStage.TASK_BREAKDOWN
        pipeline.add_log("task_breakdown", "启动 LLM 任务拆解...")

        previous_analysis = pipeline.context.get("requirement_analysis", "")

        breakdown_prompt = self._build_task_breakdown_prompt(project, previous_analysis, pipeline)
        
        try:
            msg = Message(
                sender_id="system",
                sender_name="Pipeline",
                channel=f"project:{pipeline.project_id}",
                content="📋 正在使用AI拆解任务...",
                message_type=MessageType.SYSTEM
            )
            await message_bus.broadcast(msg)
            
            llm_messages = [
                LLMMessage(role="system", content=registry.render("collaboration.pipeline.task_breakdown_system", {})),
                LLMMessage(role="user", content=breakdown_prompt)
            ]
            
            response = await llm_service.chat(llm_messages, track_cost=True, task_id=pipeline.project_id)
            
            breakdown_result = response.content
            
            tasks = self._parse_task_breakdown(breakdown_result)

            # 第一遍：创建所有任务，建立 title→task_id 映射
            title_to_id: Dict[str, str] = {}
            created_tasks: List[tuple] = []  # (task_obj, task_data)
            for task_data in tasks:
                required_skills = task_data.get("required_skills", []) or []
                task = await task_board.create_task(
                    project_id=pipeline.project_id,
                    title=task_data["title"],
                    description=task_data["description"],
                    priority=Priority(task_data.get("priority", "medium")),
                    created_by="pipeline",
                    tags=[task_data.get("assigned_role", ""), task_data.get("phase", "development")]
                )
                # 将 required_skills 存入 task.metadata 供后续 trait 匹配
                if required_skills:
                    task.metadata["required_skills"] = required_skills
                    task.updated_at = datetime.now()
                    await task_board.update_task(
                        task.id,
                        project_id=pipeline.project_id,
                        metadata=task.metadata,
                    )

                title_to_id[task_data["title"]] = task.id
                created_tasks.append((task, task_data))
                pipeline.task_ids.append(task.id)

                await task_board.add_comment(
                    task.id,
                    f"Phase: {task_data.get('phase', 'development')}\n"
                    f"Acceptance Criteria:\n" + "\n".join(task_data.get('acceptance_criteria', [])),
                    "pipeline"
                )

            # 第二遍：解析依赖关系（将标题转为 task_id）
            for task, task_data in created_tasks:
                dep_titles = task_data.get("dependencies", []) or []
                dep_ids = [title_to_id[t] for t in dep_titles if t in title_to_id]
                if dep_ids:
                    task.dependencies = dep_ids
                    task.updated_at = datetime.now()
                    await task_board.update_task(
                        task.id,
                        project_id=pipeline.project_id,
                        dependencies=dep_ids,
                    )
            
            pipeline.context["task_breakdown"] = breakdown_result
            
            msg = Message(
                sender_id="system",
                sender_name="Pipeline",
                channel=f"project:{pipeline.project_id}",
                content=f"✅ 任务拆解完成，共 {len(tasks)} 个任务:",
                message_type=MessageType.SYSTEM
            )
            await message_bus.broadcast(msg)
            
            for i, task in enumerate(tasks, 1):
                msg = Message(
                    sender_id="system",
                    sender_name="Pipeline",
                    channel=f"project:{pipeline.project_id}",
                    content=f"  {i}. [{task['priority'].upper()}] {task['title']}",
                    message_type=MessageType.SYSTEM
                )
                await message_bus.broadcast(msg)
            
            pipeline.add_log("task_breakdown", f"任务拆解完成: 创建了 {len(tasks)} 个任务")
            
        except Exception as e:
            pipeline.add_log("task_breakdown", f"任务拆解失败: {str(e)}", "error")
            pipeline.context["task_breakdown"] = f"Error: {str(e)}"

        pipeline.progress = 0.4

    def _build_task_breakdown_prompt(self, project, previous_analysis: str, pipeline: Pipeline) -> str:
        agent_info = "\n".join([
            f"- {agent_id}: {agent_service.get_agent(agent_id).get('name', 'Agent') if agent_service.get_agent(agent_id) else 'Agent'}"
            for agent_id in pipeline.agents if agent_service.get_agent(agent_id)
        ]) if pipeline.agents else "可用Agent信息未配置"
        
        return registry.render("collaboration.pipeline.task_breakdown", {
            "project_name": project.name,
            "requirements": project.requirements,
            "previous_analysis": previous_analysis,
            "agent_info": agent_info,
        })

    def _parse_task_breakdown(self, breakdown_text: str) -> List[Dict[str, Any]]:
        import json
        import re
        
        json_match = re.search(r'\{[\s\S]*"tasks"[\s\S]*\}', breakdown_text)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return data.get("tasks", [])
            except json.JSONDecodeError:
                pass
        
        task_blocks = re.split(r'\n\d+\.\s+', breakdown_text)
        tasks = []
        
        for block in task_blocks:
            if not block.strip() or 'task' not in block.lower():
                continue
            
            lines = block.strip().split('\n')
            if not lines:
                continue
            
            title = lines[0].strip('[]- ').strip()
            description = '\n'.join(lines[1:]) if len(lines) > 1 else title
            
            task = {
                "title": title,
                "description": description,
                "assigned_role": self._infer_role(description),
                "priority": "medium",
                "phase": "development",
                "dependencies": [],
                "acceptance_criteria": []
            }
            
            if "[high]" in block.lower() or "[高]" in block:
                task["priority"] = "high"
            elif "[low]" in block.lower() or "[低]" in block:
                task["priority"] = "low"
            
            tasks.append(task)
        
        return tasks

    def _infer_role(self, description: str) -> str:
        desc_lower = description.lower()
        if any(keyword in desc_lower for keyword in ["前端", "界面", "UI", "frontend", "react", "vue"]):
            return "前端开发"
        elif any(keyword in desc_lower for keyword in ["后端", "API", "数据库", "backend", "server"]):
            return "后端开发"
        elif any(keyword in desc_lower for keyword in ["架构", "架构师", "architecture"]):
            return "架构师"
        elif any(keyword in desc_lower for keyword in ["测试", "测试", "test", "QA"]):
            return "测试工程师"
        return "后端开发"

    async def _stage_task_execution(self, pipeline: Pipeline) -> None:
        """DAG 并行执行阶段 — 拓扑排序 + 依赖阻塞 + 安全守卫"""
        pipeline.current_stage = PipelineStage.TASK_EXECUTION
        pipeline.add_log("task_execution", "启动 DAG 任务执行...")

        # 层级策略下确保有 coordinator
        await self._ensure_coordinator(pipeline)

        msg = Message(
            sender_id="system",
            sender_name="Pipeline",
            channel=f"project:{pipeline.project_id}",
            content="🚀 开始 DAG 并行执行任务...",
            message_type=MessageType.SYSTEM
        )
        await message_bus.broadcast(msg)

        # 审计日志
        audit_logger.log(
            action=AuditAction.TASK_EXECUTED,
            actor="pipeline",
            detail=f"Pipeline {pipeline.id} 开始执行 {len(pipeline.task_ids)} 个任务",
        )

        # 构建 DAG: task_id → Task 对象
        all_tasks: Dict[str, Any] = {}
        for task_id in pipeline.task_ids:
            task = task_board.get_task(task_id)
            if task:
                all_tasks[task_id] = task

        # 拓扑排序获取执行层级
        execution_levels = self._topological_sort(all_tasks)

        completed_tasks: set = set()
        failed_tasks: set = set()

        for level_idx, level in enumerate(execution_levels):
            if pipeline.paused or pipeline.stop_requested or security_guard.is_emergency:
                pipeline.add_log("task_execution", "执行已暂停/停止/紧急中断", "warning")
                break

            pipeline.add_log("task_execution",
                f"Level {level_idx + 1}/{len(execution_levels)}: {len(level)} tasks in parallel")

            # 并行执行当前层级的所有任务
            tasks_coroutines = []
            for task_id in level:
                if task_id in failed_tasks:
                    continue
                tasks_coroutines.append(
                    self._execute_single_task(pipeline, task_id, all_tasks, completed_tasks, failed_tasks)
                )

            if tasks_coroutines:
                results = await asyncio.gather(*tasks_coroutines, return_exceptions=True)
                for task_id, success in zip(
                    [tid for tid in level if tid not in failed_tasks],
                    results
                ):
                    if isinstance(success, Exception):
                        failed_tasks.add(task_id)
                        pipeline.add_log("task_execution",
                            f"Task {task_id} exception: {str(success)}", "error")
                    elif success:
                        completed_tasks.add(task_id)
                    else:
                        failed_tasks.add(task_id)

            # 更新进度
            total_tasks = len(pipeline.task_ids)
            done = len(completed_tasks) + len(failed_tasks)
            pipeline.progress = 0.4 + (0.4 * done / total_tasks) if total_tasks > 0 else 0.8

        # 汇总
        msg = Message(
            sender_id="system",
            sender_name="Pipeline",
            channel=f"project:{pipeline.project_id}",
            content=f"✅ DAG 执行完成: {len(completed_tasks)} 成功, {len(failed_tasks)} 失败",
            message_type=MessageType.SYSTEM
        )
        await message_bus.broadcast(msg)

        pipeline.progress = 0.8
        pipeline.add_log("task_execution",
            f"DAG execution completed: {len(completed_tasks)}/{len(pipeline.task_ids)} success")

    def _topological_sort(self, tasks: Dict[str, Any]) -> List[List[str]]:
        """
        Kahn 算法拓扑排序，返回按层级分组的任务列表
        每个层级内的任务可以并行执行
        """
        # 构建入度表和邻接表
        in_degree: Dict[str, int] = {}
        adjacency: Dict[str, List[str]] = {}

        for task_id in tasks:
            if task_id not in in_degree:
                in_degree[task_id] = 0
            if task_id not in adjacency:
                adjacency[task_id] = []

        for task_id, task in tasks.items():
            for dep_id in getattr(task, 'dependencies', []) or []:
                if dep_id in tasks:
                    adjacency.setdefault(dep_id, []).append(task_id)
                    in_degree[task_id] = in_degree.get(task_id, 0) + 1

        # BFS 拓扑排序
        levels = []
        current_level = [tid for tid in tasks if in_degree.get(tid, 0) == 0]

        while current_level:
            levels.append(current_level)
            next_level = []
            for tid in current_level:
                for neighbor in adjacency.get(tid, []):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_level.append(neighbor)
            current_level = next_level

        # 把未覆盖的任务追加到最后一层（循环依赖或已完成的）
        covered = set()
        for level in levels:
            covered.update(level)
        leftover = [tid for tid in tasks if tid not in covered]
        if leftover:
            levels.append(leftover)

        return levels

    async def _execute_single_task(
        self,
        pipeline: Pipeline,
        task_id: str,
        all_tasks: Dict[str, Any],
        completed_tasks: set,
        failed_tasks: set
    ) -> bool:
        """执行单个任务（含安全守卫检查）"""
        task = all_tasks.get(task_id)
        if not task:
            return False

        # 检查依赖是否满足
        deps = getattr(task, 'dependencies', []) or []
        for dep_id in deps:
            if dep_id in failed_tasks:
                await task_board.change_status(task_id, TaskStatus.CANCELLED, "pipeline")
                await task_board.add_comment(task_id, f"取消: 依赖任务 {dep_id} 失败", "pipeline")
                return False
            if dep_id not in completed_tasks:
                await task_board.change_status(task_id, TaskStatus.BLOCKED, "pipeline")
                await task_board.add_comment(task_id, f"阻塞: 等待依赖任务 {dep_id}", "pipeline")
                return False

        # 安全守卫检查
        risk_level = getattr(task, 'risk_level', RiskLevel.LOW)
        risk_check = security_guard.check_and_require_approval(
            OperationType.GENERATE_CODE,
            agent_id="pipeline"
        )

        # 高风险/严重操作需要审批
        task_approval = getattr(task, 'approval_required', False)
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL) and not task_approval:
            msg = Message(
                sender_id="security_guard",
                sender_name="SecurityGuard",
                channel=f"task:{task_id}",
                content=f"🔒 任务 '{task.title}' 风险级别 {risk_level.value} 需要人工审批",
                message_type=MessageType.SYSTEM
            )
            await message_bus.send_to_task(msg, task_id)
            await task_board.change_status(task_id, TaskStatus.BLOCKED, "security_guard")
            await task_board.add_comment(task_id, f"等待审批: 风险级别 {risk_level.value}", "security_guard")

            # 审计日志
            audit_logger.log(
                action=AuditAction.TASK_APPROVAL_REQUESTED,
                actor="security_guard",
                target=task_id,
                risk_level=risk_level.value,
                detail=f"任务 '{task.title}' 需要人工审批",
            )

            # 加入人工干预队列
            self._human_intervention_queue.append({
                "type": "approval_required",
                "task_id": task_id,
                "task_title": task.title,
                "risk_level": risk_level.value,
                "timestamp": datetime.now().isoformat()
            })
            return False

        # 分配 Agent
        agent_id = await self._assign_task_to_agent(task, pipeline)
        if not agent_id:
            await task_board.add_comment(task_id, "无可用Agent", "pipeline")
            return False

        # 通知
        msg = Message(
            sender_id="system",
            sender_name="Pipeline",
            channel=f"task:{task_id}",
            content=f"⚡ Agent {agent_id} 开始执行: {task.title} [风险: {risk_level.value}]",
            message_type=MessageType.SYSTEM
        )
        await message_bus.send_to_task(msg, task_id)

        # 执行
        try:
            result = await agent_executor.execute_task_with_agent(task_id, agent_id)
            success = result.get("success", False)

            # 记录断路器数据
            await security_guard.record_operation_result(
                agent_id=agent_id,
                operation=OperationType.GENERATE_CODE,
                success=success
            )

            # 审计日志
            audit_logger.log(
                action=AuditAction.TASK_EXECUTED,
                actor=agent_id,
                agent_id=agent_id,
                operation="execute_task",
                risk_level=risk_level.value,
                target=task_id,
                outcome="success" if success else "error",
                detail=f"Task '{task.title}': {'success' if success else 'failed'}",
            )

            if success:
                await task_board.change_status(task_id, TaskStatus.REVIEW, agent_id)
                pipeline.add_log("task_execution", f"任务「{task.title}」由 {agent_id} 完成")
            else:
                await task_board.change_status(task_id, TaskStatus.TODO, agent_id)
                await task_board.add_comment(task_id,
                    f"执行失败: {result.get('error', 'Unknown')}", "pipeline")
                pipeline.add_log("task_execution",
                    f"Task {task.title} failed: {result.get('error', '')}", "error")

            return success

        except Exception as e:
            # 断路器记录
            await security_guard.record_operation_result(
                agent_id=agent_id,
                operation=OperationType.GENERATE_CODE,
                success=False
            )

            pipeline.add_log("task_execution", f"任务 {task_id} 执行异常: {str(e)}", "error")
            await task_board.add_comment(task_id, f"执行异常: {str(e)}", "pipeline")

            audit_logger.log(
                action=AuditAction.TASK_EXECUTED,
                actor=agent_id,
                agent_id=agent_id,
                target=task_id,
                outcome="error",
                detail=str(e),
            )

            return False

    async def _assign_task_to_agent(self, task, pipeline: Pipeline) -> Optional[str]:
        """策略感知的 Agent 分配。核心流程：trait 匹配优先 → 队列兜底。"""
        if not pipeline.agents:
            return None
        if len(pipeline.agents) == 1:
            return pipeline.agents[0]

        strategy = pipeline.team_config.get("strategy", "auto")
        task_tags = set(task.tags)

        # 尝试 LLM trait 匹配（如果任务带有 required_skills）
        required_skills = task.metadata.get("required_skills", []) if task.metadata else []
        if required_skills:
            try:
                from app.services.agent.agent_trait_service import agent_trait_service
                matches = await agent_trait_service.match_task_to_agent(
                    required_skills, pipeline.agents
                )
                if matches and matches[0][1] > 0:
                    pipeline.add_log("task_execution",
                        f"Trait-matched task '{task.title}' to {matches[0][0]} (score={matches[0][1]:.2f})")
                    return matches[0][0]
            except Exception:
                pass  # trait 匹配失败 → 走队列兜底

        # 策略感知分配
        if strategy == "sequential":
            return self._assign_sequential(task_tags, pipeline)
        elif strategy == "hierarchical":
            return await self._assign_hierarchical(task_tags, pipeline)
        elif strategy == "discussion":
            return self._assign_discussion(task_tags, pipeline)
        else:  # "auto"
            return self._assign_best_match(task_tags, pipeline)

    def _assign_queue(self, pipeline: Pipeline) -> str:
        """FIFO 轮询队列 — 默认兜底策略。队首出列，推到队尾。"""
        if not pipeline._assignment_queue:
            pipeline._assignment_queue = list(pipeline.agents)
        if not pipeline._assignment_queue:
            pipeline._assignment_queue = list(pipeline.agents)

        agent_id = pipeline._assignment_queue.pop(0)
        pipeline._assignment_queue.append(agent_id)
        return agent_id

    def _assign_sequential(self, task_tags: set, pipeline: Pipeline) -> Optional[str]:
        """顺序策略：按角色标签匹配度分配，匹配不到走队列。"""
        best_agent = None
        best_score = -1

        for agent_id in pipeline.agents:
            role = pipeline.agent_roles.get(agent_id, "")
            score = sum(1 for tag in task_tags if role in tag or tag in role)
            if score > best_score:
                best_score = score
                best_agent = agent_id

        return best_agent if best_score > 0 else self._assign_queue(pipeline)

    async def _assign_hierarchical(self, task_tags: set, pipeline: Pipeline) -> Optional[str]:
        """层级委派策略：coordinator 优先，无 coordinator 时选 PM 型 agent，
        都没有时降级为顺序匹配。"""
        coordinator_id = pipeline.team_config.get("coordinatorId")
        elected = pipeline.context.get("elected_coordinator")
        effective_coordinator = coordinator_id or elected

        if effective_coordinator and effective_coordinator in pipeline.agents:
            return self._assign_sequential(task_tags, pipeline)

        # 查找 PM 型 agent
        for aid in pipeline.agents:
            if pipeline.agent_roles.get(aid, "") == "PM":
                return self._assign_sequential(task_tags, pipeline)

        # 没有 PM → 将在首次调用时触发选举（由调用方处理）
        return self._assign_sequential(task_tags, pipeline)

    def _assign_discussion(self, task_tags: set, pipeline: Pipeline) -> Optional[str]:
        """讨论策略：负载均衡分配。执行阶段不启动讨论（讨论在规划阶段进行）。
        此处用队列保证任务均匀分配。"""
        return self._assign_queue(pipeline)

    def _assign_best_match(self, task_tags: set, pipeline: Pipeline) -> Optional[str]:
        """最佳匹配策略：角色不预设，直接走队列分配。"""
        return self._assign_queue(pipeline)

    async def _ensure_coordinator(self, pipeline: Pipeline) -> None:
        """层级委派策略下，若无 PM 型 agent 且无手动指定的 coordinator，
        通过 agent 讨论选举一位。只在第一次调用时执行。"""
        strategy = pipeline.team_config.get("strategy", "")
        if strategy != "hierarchical":
            return

        coordinator_id = pipeline.team_config.get("coordinatorId")
        if coordinator_id and coordinator_id in pipeline.agents:
            return
        if "elected_coordinator" in pipeline.context:
            return

        # 没有预设 PM → 通过讨论选举 coordinator
        pipeline.add_log("task_execution",
            "No PM agent in team — running coordinator election...", "info")

        try:
            from app.services.collaboration.discussion_orchestrator import discussion_orchestrator

            project = project_service.get_project(pipeline.project_id)
            elected = await discussion_orchestrator.run_coordinator_election(
                pipeline_id=pipeline.id,
                project_id=pipeline.project_id,
                agent_ids=pipeline.agents,
                project_context={
                    "name": project.name if project else "",
                    "description": project.description if project else "",
                    "requirements": project.requirements if project else "",
                },
            )
            pipeline.context["elected_coordinator"] = elected
            pipeline.add_log("task_execution",
                f"Coordinator elected via discussion: {elected}", "info")
        except Exception as e:
            pipeline.add_log("task_execution",
                f"Coordinator election failed: {e}, using first agent", "warning")
            pipeline.context["elected_coordinator"] = pipeline.agents[0]

    async def _run_agent_discussion(
        self,
        pipeline: Pipeline,
        stage_key: str,
        topic: str,
        context: Dict[str, Any],
        agent_ids: List[str] = None,
        max_rounds: int = 2,
    ) -> "DiscussionResult":
        """在流水线阶段中运行一次 agent 讨论的便捷方法。"""
        from app.services.collaboration.discussion_orchestrator import (
            discussion_orchestrator, DiscussionMode
        )

        participant_ids = agent_ids or pipeline.agents
        if len(participant_ids) < 2:
            from app.services.collaboration.discussion_orchestrator import DiscussionResult, DiscussionMessage
            return DiscussionResult(
                topic=topic, concluded=False, consensus_reached=False,
                summary="不足 2 个 agent，无法进行讨论",
                participant_agents=participant_ids,
            )

        pipeline.add_log(stage_key,
            f"Starting agent discussion: {topic[:80]}... ({len(participant_ids)} agents)")

        result = await discussion_orchestrator.conduct_discussion(
            pipeline_id=pipeline.id,
            project_id=pipeline.project_id,
            topic=topic,
            context=context,
            agent_ids=participant_ids,
            mode=DiscussionMode.ROUND_ROBIN,
            max_rounds=max_rounds,
        )

        pipeline.add_log(stage_key,
            f"Discussion complete: {result.rounds_conducted} rounds, "
            f"{len(result.transcript)} messages, "
            f"consensus={'yes' if result.consensus_reached else 'no'}")

        return result

    def _select_stage_participants(
        self,
        pipeline: Pipeline,
        preferred_roles: List[str] = None,
    ) -> List[str]:
        """所有 agent 参与所有阶段——配置阶段不预设角色分工。"""
        return list(pipeline.agents)

    async def _stage_review(self, pipeline: Pipeline) -> None:
        pipeline.current_stage = PipelineStage.REVIEW
        pipeline.add_log("review", "启动审查阶段...")

        msg = Message(
            sender_id="system",
            sender_name="Pipeline",
            channel=f"project:{pipeline.project_id}",
            content="🔍 开始审核阶段...",
            message_type=MessageType.SYSTEM
        )
        await message_bus.broadcast(msg)

        completed_tasks = task_board.get_tasks_by_status(TaskStatus.REVIEW, project_id=pipeline.project_id)

        if not completed_tasks:
            pipeline.add_log("review", "无任务需要审查", "warning")
            msg = Message(
                sender_id="system",
                sender_name="Pipeline",
                channel=f"project:{pipeline.project_id}",
                content="🎉 项目完成！所有阶段都已完成。",
                message_type=MessageType.SYSTEM
            )
            await message_bus.broadcast(msg)
            pipeline.progress = 1.0
            return

        # 选择参与者（测试 + 架构师优先，确保多视角审查）
        participants = self._select_stage_participants(pipeline, ["测试工程师", "架构师"])

        if len(participants) < 2:
            # 单人审查 — 直接用 LLM
            review_result = await self._single_llm_review(pipeline, completed_tasks)
        else:
            # 多 Agent 审查讨论
            tasks_summary = self._build_tasks_summary_for_discussion(completed_tasks)
            try:
                result = await self._run_agent_discussion(
                    pipeline=pipeline,
                    stage_key="review",
                    topic=f"审查已完成的任务 — 项目: {pipeline.name}",
                    context={
                        "已完成任务": tasks_summary,
                        "审查角度": "完成度、代码质量、安全性、改进建议",
                    },
                    agent_ids=participants,
                    max_rounds=2,
                )
                review_result = await self._merge_discussion_into_review(result, completed_tasks)
                pipeline.context["review_discussion"] = {
                    "transcript": [m.model_dump(mode='json') for m in result.transcript],
                    "consensus": result.consensus_reached,
                    "participants": participants,
                }
            except Exception as e:
                pipeline.add_log("review", f"Agent 讨论失败: {e}，回退到单 LLM", "warning")
                review_result = await self._single_llm_review(pipeline, completed_tasks)

        pipeline.context["review"] = review_result

        # 保存审查报告到 workspace
        from app.services.project.workspace_manager import workspace_manager
        try:
            workspace_manager.add_artifact(
                pipeline.project_id, "review",
                "review_report.md", review_result,
            )
        except Exception:
            pass

        msg = Message(
            sender_id="system",
            sender_name="Pipeline",
            channel=f"project:{pipeline.project_id}",
            content=f"✅ 审核完成",
            message_type=MessageType.SYSTEM
        )
        await message_bus.broadcast(msg)

        pipeline.add_log("review", f"审查完成: {len(participants)} 位 Agent 参与")

        msg = Message(
            sender_id="system",
            sender_name="Pipeline",
            channel=f"project:{pipeline.project_id}",
            content="🎉 项目完成！所有阶段都已完成。",
            message_type=MessageType.SYSTEM
        )
        await message_bus.broadcast(msg)

        pipeline.progress = 1.0
        pipeline.add_log("review", "审查阶段结束")

    async def _single_llm_review(self, pipeline: Pipeline, completed_tasks) -> str:
        """单 LLM 审查的兜底方案"""
        review_prompt = self._build_review_prompt(completed_tasks)
        response = await llm_service.chat(
            messages=[
                LLMMessage(role="system", content=registry.render("collaboration.pipeline.review_system", {})),
                LLMMessage(role="user", content=review_prompt),
            ],
            track_cost=True,
            task_id=pipeline.project_id,
        )
        return response.content

    def _build_tasks_summary_for_discussion(self, completed_tasks) -> str:
        """构建审查讨论用的任务摘要"""
        return "\n".join(
            f"- [{task.priority.value.upper()}] {task.title}: {task.description[:200]}"
            for task in completed_tasks
        )

    async def _merge_discussion_into_review(self, discussion, completed_tasks) -> str:
        """将多 agent 审查讨论合并为一份审查报告"""
        transcript_text = "\n\n".join(
            f"### {dm.agent_name} ({dm.role_label})\n{dm.content}"
            for dm in discussion.transcript
        )

        tasks_text = self._build_tasks_summary_for_discussion(completed_tasks)

        response = await llm_service.chat(
            messages=[
                LLMMessage(
                    role="system",
                    content=registry.render("collaboration.pipeline.merge_review_system", {}),
                ),
                LLMMessage(
                    role="user",
                    content=registry.render("collaboration.pipeline.merge_review", {
                        "tasks_text": tasks_text,
                        "transcript_text": transcript_text,
                    }),
                ),
            ],
            track_cost=True,
            task_id=completed_tasks[0].project_id if completed_tasks else "",
        )
        return response.content

        pipeline.progress = 1.0
        pipeline.add_log("review", "审查阶段结束")

    def _build_review_prompt(self, completed_tasks) -> str:
        tasks_summary = "\n".join([
            f"- {task.title}: {task.description[:200]}"
            for task in completed_tasks
        ])
        
        return registry.render("collaboration.pipeline.review", {
            "tasks_summary": tasks_summary,
        })

    async def pause_pipeline(self, pipeline_id: str) -> bool:
        async with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if not pipeline or pipeline.status != PipelineStatus.RUNNING:
                return False

            pipeline.status = PipelineStatus.PAUSED
            pipeline.paused = True
            await agent_executor.pause_project(pipeline.project_id)
            speaking_controller.set_mode(pipeline_id, SpeakingMode.FREE_STYLE)

            pipeline.add_log("control", "流水线已暂停（人工干预）")
            if self._db:
                await self._db.save(pipeline)
            return True

    async def resume_pipeline(self, pipeline_id: str) -> bool:
        async with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if not pipeline or pipeline.status != PipelineStatus.PAUSED:
                return False

            pipeline.status = PipelineStatus.RUNNING
            pipeline.paused = False
            await agent_executor.resume_project(pipeline.project_id)
            speaking_controller.set_mode(pipeline_id, SpeakingMode.PRIORITY_BASED)

            pipeline.add_log("control", "流水线已恢复")
            if self._db:
                await self._db.save(pipeline)
            return True

    async def stop_pipeline(self, pipeline_id: str) -> bool:
        async with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if not pipeline:
                return False

            pipeline.stop_requested = True
            pipeline.status = PipelineStatus.FAILED
            self._cleanup_pipeline_agents(pipeline)
            self._active_pipelines.pop(pipeline.project_id, None)

            pipeline.add_log("control", "流水线已停止（人工干预）")
            if self._db:
                await self._db.save(pipeline)
            return True

    async def intervene(
        self,
        pipeline_id: str,
        message: str,
        agent_id: Optional[str] = None
    ) -> None:
        async with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if not pipeline:
                return

            self._human_intervention_queue.append({
                "message": message,
                "agent_id": agent_id,
                "timestamp": datetime.now().isoformat()
            })

            msg = Message(
                sender_id="human",
                sender_name="Human",
                recipients=[agent_id] if agent_id else [],
                content=f"[Human Intervention] {message}",
                message_type=MessageType.ACTION
            )

            if agent_id:
                await message_bus.send_private(msg)
            else:
                await message_bus.broadcast(msg)

            pipeline.add_log("intervention", f"人工干预: {message}")

    def get_pipeline(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return None

        return {
            "id": pipeline.id,
            "project_id": pipeline.project_id,
            "name": pipeline.name,
            "status": pipeline.status.value,
            "current_stage": pipeline.current_stage.value,
            "progress": pipeline.progress,
            "agents": pipeline.agents,
            "task_count": len(pipeline.task_ids),
            "created_at": pipeline.created_at.isoformat(),
            "started_at": pipeline.started_at.isoformat() if pipeline.started_at else None,
            "completed_at": pipeline.completed_at.isoformat() if pipeline.completed_at else None,
            "logs": pipeline.logs[-50:],
            "context": pipeline.context
        }

    def list_pipelines(self) -> List[Dict[str, Any]]:
        return [self.get_pipeline(pid) for pid in self._pipelines.keys()]

    def get_active_pipeline(self, project_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if project_id:
            pipeline_id = self._active_pipelines.get(project_id)
            if pipeline_id:
                return self.get_pipeline(pipeline_id)
            return None
        # 向后兼容：返回第一个活跃 pipeline
        for pipeline_id in self._active_pipelines.values():
            return self.get_pipeline(pipeline_id)
        return None

    def list_pipelines_by_project(self, project_id: str) -> List[Dict[str, Any]]:
        return [
            self.get_pipeline(pid)
            for pid, p in self._pipelines.items()
            if p.project_id == project_id
        ]

    def get_intervention_queue(self) -> List[Dict[str, Any]]:
        return self._human_intervention_queue.copy()

    def add_log(self, message: str, stage: str = "general", level: str = "info") -> None:
        for pipeline in self._pipelines.values():
            pipeline.add_log(stage, message, level)


pipeline_orchestrator = PipelineOrchestrator()
