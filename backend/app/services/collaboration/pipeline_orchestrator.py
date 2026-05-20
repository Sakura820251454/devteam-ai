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

    def add_log(self, stage: str, message: str, level: str = "info") -> None:
        self.logs.append({
            "stage": stage,
            "message": message,
            "level": level,
            "timestamp": datetime.now().isoformat()
        })


class PipelineOrchestrator:
    def __init__(self):
        self._pipelines: Dict[str, Pipeline] = {}
        self._active_pipelines: Dict[str, str] = {}  # project_id -> pipeline_id
        self._execution_tasks: Dict[str, asyncio.Task] = {}
        self._human_intervention_queue: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def create_pipeline(
        self,
        project_id: str,
        name: str,
        agent_ids: List[str]
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

            self._pipelines[pipeline.id] = pipeline
            self.add_log(f"Pipeline created: {name}", "init")
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
            return True

    async def _run_pipeline(self, pipeline_id: str) -> None:
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return

        project = project_service.get_project(pipeline.project_id)
        if not project:
            return

        try:
            pipeline.add_log("init", f"Pipeline started for project: {project.name}")

            await self._stage_requirement_analysis(pipeline)

            if pipeline.stop_requested:
                pipeline.status = PipelineStatus.FAILED
                self._cleanup_pipeline_agents(pipeline)
                return

            await self._stage_task_breakdown(pipeline, project)

            if pipeline.stop_requested:
                pipeline.status = PipelineStatus.FAILED
                self._cleanup_pipeline_agents(pipeline)
                return

            await self._stage_task_execution(pipeline)

            if pipeline.stop_requested:
                pipeline.status = PipelineStatus.FAILED
                self._cleanup_pipeline_agents(pipeline)
                return

            await self._stage_review(pipeline)

            pipeline.status = PipelineStatus.COMPLETED
            pipeline.completed_at = datetime.now()
            pipeline.current_stage = PipelineStage.COMPLETED

            project_service.update_project(pipeline.project_id, status="completed")

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
        pipeline.add_log("requirement_analysis", "Starting requirement analysis with LLM...")
        
        project = project_service.get_project(pipeline.project_id)
        if not project:
            return

        msg = Message(
            sender_id="system",
            sender_name="Pipeline",
            channel=f"project:{pipeline.project_id}",
            content=f"🔍 开始使用AI分析需求: {project.requirements[:200]}...",
            message_type=MessageType.SYSTEM
        )
        await message_bus.broadcast(msg)

        speaking_controller.set_mode(pipeline.id, SpeakingMode.PRIORITY_BASED)
        speaking_controller.set_token_budget(pipeline.id, 100000)

        analysis_prompt = self._build_requirement_analysis_prompt(project)
        
        try:
            llm_messages = [
                LLMMessage(role="system", content="你是一位资深产品经理，擅长深入分析需求，发现潜在问题和改进机会。"),
                LLMMessage(role="user", content=analysis_prompt)
            ]
            
            response = await llm_service.chat(llm_messages, track_cost=True, task_id=pipeline.project_id)
            
            analysis_result = response.content
            
            pipeline.context["requirement_analysis"] = analysis_result
            
            msg = Message(
                sender_id="system",
                sender_name="Pipeline",
                channel=f"project:{pipeline.project_id}",
                content=f"✅ 需求分析完成:\n{analysis_result[:500]}...",
                message_type=MessageType.SYSTEM
            )
            await message_bus.broadcast(msg)
            
            pipeline.add_log("requirement_analysis", f"Analysis complete: {len(analysis_result)} chars")
            
        except Exception as e:
            pipeline.add_log("requirement_analysis", f"Analysis failed: {str(e)}", "error")
            pipeline.context["requirement_analysis"] = f"Error: {str(e)}"

        pipeline.progress = 0.2

    def _build_requirement_analysis_prompt(self, project) -> str:
        return f"""请分析以下项目需求:

项目名称: {project.name}
项目描述: {project.description}
需求内容: {project.requirements}

请从以下角度进行分析:
1. 需求完整性 - 是否清晰、无歧义
2. 技术可行性 - 技术上是否可行
3. 潜在风险 - 可能遇到的问题
4. 改进建议 - 更好的实现方式
5. 优先级建议 - 哪些是核心功能、哪些是辅助功能

请给出详细分析报告。"""

    async def _stage_task_breakdown(self, pipeline: Pipeline, project) -> None:
        pipeline.current_stage = PipelineStage.TASK_BREAKDOWN
        pipeline.add_log("task_breakdown", "Starting task breakdown with LLM...")

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
                LLMMessage(role="system", content="""你是一位经验丰富的项目经理，擅长将复杂需求拆解为可执行的具体任务。
每个任务应该:
- 清晰明确、可独立完成
- 有明确的验收标准
- 合理的工作量估计
- 明确的依赖关系

请按以下JSON格式输出任务列表:
{
  "tasks": [
    {
      "title": "任务标题",
      "description": "任务详细描述",
      "assigned_role": "后端开发/前端开发/架构师/测试",
      "priority": "high/medium/low",
      "phase": "design/development/testing",
      "dependencies": ["前置任务标题"],
      "acceptance_criteria": ["验收标准1", "验收标准2"]
    }
  ],
  "summary": "整体拆解说明"
}"""),
                LLMMessage(role="user", content=breakdown_prompt)
            ]
            
            response = await llm_service.chat(llm_messages, track_cost=True, task_id=pipeline.project_id)
            
            breakdown_result = response.content
            
            tasks = self._parse_task_breakdown(breakdown_result)
            
            for task_data in tasks:
                task = task_board.create_task(
                    project_id=pipeline.project_id,
                    title=task_data["title"],
                    description=task_data["description"],
                    priority=Priority(task_data.get("priority", "medium")),
                    created_by="pipeline",
                    tags=[task_data.get("assigned_role", ""), task_data.get("phase", "development")]
                )
                pipeline.task_ids.append(task.id)
                
                task_board.add_comment(
                    task.id,
                    f"Phase: {task_data.get('phase', 'development')}\n"
                    f"Acceptance Criteria:\n" + "\n".join(task_data.get('acceptance_criteria', [])),
                    "pipeline"
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
            
            pipeline.add_log("task_breakdown", f"Breakdown complete: {len(tasks)} tasks created")
            
        except Exception as e:
            pipeline.add_log("task_breakdown", f"Breakdown failed: {str(e)}", "error")
            pipeline.context["task_breakdown"] = f"Error: {str(e)}"

        pipeline.progress = 0.4

    def _build_task_breakdown_prompt(self, project, previous_analysis: str, pipeline: Pipeline) -> str:
        agent_info = "\n".join([
            f"- {agent_id}: {agent_service.get_agent(agent_id).get('name', 'Agent') if agent_service.get_agent(agent_id) else 'Agent'}"
            for agent_id in pipeline.agents if agent_service.get_agent(agent_id)
        ]) if pipeline.agents else "可用Agent信息未配置"
        
        return f"""基于以下项目需求，请拆解具体任务:

项目名称: {project.name}
需求内容: {project.requirements}

前期分析结果:
{previous_analysis}

可用团队成员:
{agent_info}

请拆解出具体可执行的任务列表。"""

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
        pipeline.add_log("task_execution", "Starting DAG-based task execution...")

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
                pipeline.add_log("task_execution", "Execution paused/stopped/emergency", "warning")
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
                task_board.change_status(task_id, TaskStatus.CANCELLED, "pipeline")
                task_board.add_comment(task_id, f"取消: 依赖任务 {dep_id} 失败", "pipeline")
                return False
            if dep_id not in completed_tasks:
                task_board.change_status(task_id, TaskStatus.BLOCKED, "pipeline")
                task_board.add_comment(task_id, f"阻塞: 等待依赖任务 {dep_id}", "pipeline")
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
            task_board.change_status(task_id, TaskStatus.BLOCKED, "security_guard")
            task_board.add_comment(task_id, f"等待审批: 风险级别 {risk_level.value}", "security_guard")

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
            task_board.add_comment(task_id, "无可用Agent", "pipeline")
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
                task_board.change_status(task_id, TaskStatus.REVIEW, agent_id)
                pipeline.add_log("task_execution", f"Task {task.title} completed by {agent_id}")
            else:
                task_board.change_status(task_id, TaskStatus.TODO, agent_id)
                task_board.add_comment(task_id,
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

            pipeline.add_log("task_execution", f"Task {task_id} error: {str(e)}", "error")
            task_board.add_comment(task_id, f"执行异常: {str(e)}", "pipeline")

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
        task_tags = set(task.tags)
        
        role_priority = {
            "前端开发": 1,
            "后端开发": 2,
            "架构师": 3,
            "测试工程师": 4,
            "PM": 5
        }
        
        for agent_id in pipeline.agents:
            agent = agent_service.get_agent(agent_id)
            if not agent:
                continue
            
            agent_type = agent.get("type", "")
            
            for tag in task_tags:
                if any(role in agent_type or role in tag for role in role_priority.keys()):
                    return agent_id
        
        return pipeline.agents[0] if pipeline.agents else None

    async def _stage_review(self, pipeline: Pipeline) -> None:
        pipeline.current_stage = PipelineStage.REVIEW
        pipeline.add_log("review", "Starting review stage...")

        msg = Message(
            sender_id="system",
            sender_name="Pipeline",
            channel=f"project:{pipeline.project_id}",
            content="🔍 开始审核阶段...",
            message_type=MessageType.SYSTEM
        )
        await message_bus.broadcast(msg)

        completed_tasks = task_board.get_tasks_by_status(TaskStatus.REVIEW, project_id=pipeline.project_id)
        
        if completed_tasks:
            review_prompt = self._build_review_prompt(completed_tasks)
            
            try:
                llm_messages = [
                    LLMMessage(role="system", content="你是一位资深技术专家，擅长代码审查和质量把控。"),
                    LLMMessage(role="user", content=review_prompt)
                ]
                
                response = await llm_service.chat(llm_messages, track_cost=True, task_id=pipeline.project_id)
                
                review_result = response.content
                
                pipeline.context["review"] = review_result
                
                msg = Message(
                    sender_id="system",
                    sender_name="Pipeline",
                    channel=f"project:{pipeline.project_id}",
                    content=f"✅ 审核完成:\n{review_result[:500]}...",
                    message_type=MessageType.SYSTEM
                )
                await message_bus.broadcast(msg)
                
                pipeline.add_log("review", "Review complete")
                
            except Exception as e:
                pipeline.add_log("review", f"Review failed: {str(e)}", "error")
        else:
            pipeline.add_log("review", "No tasks to review", "warning")

        msg = Message(
            sender_id="system",
            sender_name="Pipeline",
            channel=f"project:{pipeline.project_id}",
            content="🎉 项目完成！所有阶段都已完成。",
            message_type=MessageType.SYSTEM
        )
        await message_bus.broadcast(msg)

        pipeline.progress = 1.0
        pipeline.add_log("review", "Review completed")

    def _build_review_prompt(self, completed_tasks) -> str:
        tasks_summary = "\n".join([
            f"- {task.title}: {task.description[:200]}"
            for task in completed_tasks
        ])
        
        return f"""请审核以下已完成的任务:

{tasks_summary}

请从以下角度进行审核:
1. 完成度 - 是否满足所有需求
2. 代码质量 - 是否有明显问题
3. 潜在风险 - 是否存在安全隐患
4. 改进建议 - 如何进一步优化

请给出审核报告和改进建议。"""

    async def pause_pipeline(self, pipeline_id: str) -> bool:
        async with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if not pipeline or pipeline.status != PipelineStatus.RUNNING:
                return False

            pipeline.status = PipelineStatus.PAUSED
            pipeline.paused = True
            await agent_executor.pause_project(pipeline.project_id)
            speaking_controller.set_mode(pipeline_id, SpeakingMode.FREE_STYLE)

            pipeline.add_log("control", "Pipeline paused by human intervention")
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

            pipeline.add_log("control", "Pipeline resumed")
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

            pipeline.add_log("control", "Pipeline stopped by human intervention")
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

            pipeline.add_log("intervention", f"Human intervened: {message}")

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
            "logs": pipeline.logs[-20:],
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
