import asyncio
import logging
import traceback
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

logger = logging.getLogger(__name__)


class PipelineStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


# 合法的状态转移路径
_ALLOWED_TRANSITIONS: dict[PipelineStatus, set[PipelineStatus]] = {
    PipelineStatus.IDLE:      {PipelineStatus.RUNNING, PipelineStatus.FAILED},
    PipelineStatus.RUNNING:   {PipelineStatus.PAUSED, PipelineStatus.COMPLETED, PipelineStatus.FAILED},
    PipelineStatus.PAUSED:    {PipelineStatus.RUNNING, PipelineStatus.FAILED},
    PipelineStatus.COMPLETED: set(),       # 终态
    PipelineStatus.FAILED:    {PipelineStatus.RUNNING},  # 允许重启
}


class IllegalStateTransition(Exception):
    """非法的状态转移。"""
    def __init__(self, current: PipelineStatus, target: PipelineStatus):
        super().__init__(f"非法的状态转移: {current.value} → {target.value}")


# Standard stage keys — used as stage_handler lookup, not to restrict what stages can exist.
# User-confirmed stages drive the pipeline; these are just the known handler bindings.
STAGE_REQUIREMENT_ANALYSIS = "requirement_analysis"
STAGE_TASK_BREAKDOWN = "task_breakdown"


class Pipeline:
    def __init__(self):
        self.id: str = str(uuid.uuid4())
        self.project_id: str = ""
        self.name: str = ""
        self.status: PipelineStatus = PipelineStatus.IDLE
        self.current_stage: str = ""  # set to stages[0]["key"] once stages are confirmed
        self.created_at: datetime = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.agents: List[str] = []
        self.task_ids: List[str] = []
        self.progress: float = 0.0
        self.logs: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {}
        self.stop_requested: bool = False
        self.team_config: Dict[str, Any] = {}
        self.agent_roles: Dict[str, str] = {}  # agent_id -> inferred role label
        self.stages: List[Dict[str, Any]] = []
        self._assignment_queue: List[str] = []  # FIFO queue for round-robin assignment
        self._human_intervention_queue: List[Dict[str, Any]] = []  # queue for user intervention requests
        self.project_type: str = "development"  # 项目类型（research/content/development/analysis/design）

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

    @staticmethod
    def transition(pipeline: Pipeline, new_status: PipelineStatus) -> None:
        """执行 Pipeline 状态转移，合法性校验。

        非法的转移路径会抛出 IllegalStateTransition。
        这是修改 pipeline.status 的唯一入口。
        """
        allowed = _ALLOWED_TRANSITIONS.get(pipeline.status, set())
        if new_status not in allowed:
            raise IllegalStateTransition(pipeline.status, new_status)
        old_status = pipeline.status
        pipeline.status = new_status
        if old_status != new_status:
            pipeline.add_log("control",
                f"状态转移: {old_status.value} → {new_status.value}", "debug")

    async def load_all(self) -> None:
        if self._db:
            loaded = await self._db.load_all()
            for pid, pipeline in loaded.items():
                self._pipelines[pid] = pipeline
                if pipeline.status == PipelineStatus.RUNNING:
                    self._active_pipelines[pipeline.project_id] = pid

    async def update_pipeline_stages(
        self, pipeline_id: str, stages: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Update pipeline stages in memory and DB. Returns project_id if found."""
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return None
        pipeline.stages = stages
        if self._db:
            await self._db.save(pipeline)
        return pipeline.project_id

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

            # 检测项目类型以指导后续任务拆解
            project = project_service.get_project(project_id)
            if project and project.requirements:
                try:
                    from app.services.task.task_analyzer import task_analyzer
                    analysis = await task_analyzer.analyze(project.requirements)
                    pipeline.context["project_type_analysis"] = {
                        "domain": analysis.domain,
                        "task_type": analysis.task_type,
                        "complexity": analysis.complexity,
                        "breakdown": analysis.breakdown,
                        "summary": analysis.analysis_summary,
                    }
                    pipeline.project_type = self._domain_to_project_type(analysis.domain)
                    pipeline.add_log("init",
                        f"项目类型检测: domain={analysis.domain}, type={analysis.task_type}, "
                        f"project_type={pipeline.project_type}")
                except Exception as e:
                    pipeline.add_log("init", f"项目类型检测失败，使用默认值(development): {e}", "warning")

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

            if not pipeline.context.get("stages_confirmed"):
                pipeline.add_log("init", "阶段未确认，无法启动", "error")
                return False

            project = project_service.get_project(pipeline.project_id)
            if not project:
                return False

            self.transition(pipeline, PipelineStatus.RUNNING)
            pipeline.started_at = pipeline.started_at or datetime.now()
            self._active_pipelines[pipeline.project_id] = pipeline_id

            task = asyncio.create_task(self._run_pipeline(pipeline_id))
            self._execution_tasks[pipeline_id] = task
            if self._db:
                await self._db.save(pipeline)
            return True

    def _stage_index(self, pipeline, stage_key: str) -> int:
        """Return the index of stage_key in pipeline.stages, or -1 if not found."""
        for i, s in enumerate(pipeline.stages):
            if s.get("key") == stage_key:
                return i
        return -1

    def _resume_from_stage(self, pipeline, stage_idx: int) -> None:
        """Mark all stages before stage_idx as completed for resume support."""
        for i in range(stage_idx):
            key = pipeline.stages[i].get("key", "")
            if key:
                self._update_stage_status(pipeline, key, "completed")

    async def _run_pipeline(self, pipeline_id: str) -> None:
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return

        project = project_service.get_project(pipeline.project_id)
        if not project:
            return

        try:
            agent_names = []
            for aid in pipeline.agents:
                a = agent_service.get_agent(aid)
                agent_names.append(a.get("name", aid) if a else aid)

            confirmed_stages = pipeline.stages or []
            if not confirmed_stages:
                pipeline.add_log("init", "无确认阶段，流水线中止", "error")
                self.transition(pipeline, PipelineStatus.FAILED)
                self._cleanup_pipeline_agents(pipeline)
                if self._db:
                    await self._db.save(pipeline)
                return

            stage_labels = [s.get("label", s.get("key", "")) for s in confirmed_stages]
            pipeline.add_log("init",
                f"流水线启动 — 项目: {project.name}, Agent: {agent_names}, "
                f"阶段({len(confirmed_stages)}): {stage_labels}")

            # Ensure workspace exists
            from app.services.project.workspace_manager import workspace_manager
            try:
                ws = workspace_manager.get_workspace(pipeline.project_id)
                if not ws:
                    workspace_manager.create_workspace(
                        project_id=pipeline.project_id,
                        name=project.name,
                        description=project.description or "",
                        stages=confirmed_stages,
                    )
                    pipeline.add_log("init", "Workspace 已创建")
            except Exception as e:
                pipeline.add_log("init", f"Workspace 创建失败: {e}", "warning")

            # Determine resume position
            start_idx = 0
            if pipeline.current_stage:
                idx = self._stage_index(pipeline, pipeline.current_stage)
                if idx >= 0:
                    start_idx = idx
                    self._resume_from_stage(pipeline, start_idx)
                    pipeline.add_log("init",
                        f"从阶段「{pipeline.current_stage}」(#{start_idx + 1}/{len(confirmed_stages)}) 恢复执行")

            # Auto-run requirement analysis + task breakdown if needed before execution stages
            has_requirement_stage = any(
                s.get("key") == STAGE_REQUIREMENT_ANALYSIS for s in confirmed_stages
            )
            has_breakdown_stage = any(
                s.get("key") == STAGE_TASK_BREAKDOWN for s in confirmed_stages
            )
            if not has_requirement_stage and not has_breakdown_stage and not pipeline.task_ids:
                pipeline.add_log("init", "自动触发需求分析（未在阶段列表中）")
                if not pipeline.context.get("requirement_analysis"):
                    await self._stage_requirement_analysis(pipeline)
                # 需求分析阶段可能触发 _handle_ask_user 设置 paused=True，
                # 此时应继续推进到任务拆解，不应在此阻塞
                if pipeline.status == PipelineStatus.PAUSED and not pipeline.stop_requested:
                    pipeline.add_log("init", "需求分析产生的用户提问已记录，继续推进任务拆解")
                    self.transition(pipeline, PipelineStatus.RUNNING)
                pipeline.add_log("init", "自动触发任务拆解（未在阶段列表中）")
                if not pipeline.context.get("task_breakdown"):
                    await self._stage_task_breakdown(pipeline, project)
                await project_service.advance_phase(pipeline.project_id)
                if self._db:
                    await self._db.save(pipeline)
            elif not has_requirement_stage and not pipeline.context.get("requirement_analysis"):
                pipeline.add_log("init", "自动触发需求分析（未在阶段列表中）")
                await self._stage_requirement_analysis(pipeline)
                if pipeline.status == PipelineStatus.PAUSED and not pipeline.stop_requested:
                    self.transition(pipeline, PipelineStatus.RUNNING)
                await self._stage_task_breakdown(pipeline, project)
                await project_service.advance_phase(pipeline.project_id)
                if self._db:
                    await self._db.save(pipeline)

            # Iterate through confirmed stages
            total_stages = len(confirmed_stages)
            for i in range(start_idx, total_stages):
                if pipeline.stop_requested or pipeline.status == PipelineStatus.PAUSED:
                    break

                stage_def = confirmed_stages[i]
                key = stage_def.get("key", f"stage_{i}")
                label = stage_def.get("label", key)

                pipeline.current_stage = key
                self._update_stage_status(pipeline, key, "active")
                pipeline.progress = i / total_stages if total_stages > 0 else 0
                pipeline.add_log(key, f"阶段「{label}」开始 ({i + 1}/{total_stages})")

                if key == STAGE_REQUIREMENT_ANALYSIS:
                    if pipeline.context.get("requirement_analysis"):
                        pipeline.add_log(key, "使用已保存的需求分析结果，跳过执行")
                    else:
                        await self._stage_requirement_analysis(pipeline)
                    self._update_stage_status(pipeline, key, "completed")

                elif key == STAGE_TASK_BREAKDOWN:
                    if pipeline.context.get("task_breakdown") and pipeline.task_ids:
                        pipeline.add_log(key, f"使用已保存的任务分解（{len(pipeline.task_ids)} 个任务），跳过执行")
                        if not pipeline.stages:
                            await self._rebuild_stages_from_tasks(pipeline)
                    else:
                        await self._stage_task_breakdown(pipeline, project)
                    self._update_stage_status(pipeline, key, "completed")
                    await project_service.advance_phase(pipeline.project_id)

                else:
                    # Execution stage: run tasks tagged with this stage key
                    await self._stage_task_execution(pipeline, stage_key=key)
                    # 将该阶段产出物组装到 src/ 目录
                    try:
                        from app.services.project.workspace_manager import workspace_manager
                        assembled = workspace_manager.assemble_artifacts_to_src(pipeline.project_id)
                        if assembled:
                            pipeline.add_log(key, f"产出物已组装到 src/: {len(assembled)} 文件")
                    except Exception as e:
                        pipeline.add_log(key, f"src 组装失败: {e}", "warning")
                    self._update_stage_status(pipeline, key, "completed")

                if self._db:
                    await self._db.save(pipeline)

            # After all stages: final review gate
            if not pipeline.stop_requested and pipeline.status != PipelineStatus.PAUSED:
                await self._stage_review(pipeline)

                if pipeline.status != PipelineStatus.FAILED:
                    self.transition(pipeline, PipelineStatus.COMPLETED)
                    pipeline.completed_at = datetime.now()
                    pipeline.current_stage = "completed"
                    pipeline.progress = 1.0
                    await project_service.update_project(pipeline.project_id, status="completed")
                if self._db:
                    await self._db.save(pipeline)

            # Trigger learning cycle — pipeline 完成即用户需求完成（大任务），触发复盘
            if pipeline.status == PipelineStatus.COMPLETED:
                try:
                    await self._trigger_learning_cycle(pipeline)
                except Exception as e:
                    pipeline.add_log("learning", f"学习闭环执行失败: {e}", "warning")

        except asyncio.CancelledError:
            pipeline.add_log("control", "流水线任务被取消（用户关闭项目）", "info")
            if self._db:
                await self._db.save(pipeline)
            raise
        except Exception as e:
            self.transition(pipeline, PipelineStatus.FAILED)
            tb = traceback.format_exc()
            pipeline.add_log("error", f"流水线异常终止 — {str(e)}\n{tb[-500:]}", "error")
            if self._db:
                await self._db.save(pipeline)
            raise
        finally:
            if pipeline.status != PipelineStatus.PAUSED:
                self._cleanup_pipeline_agents(pipeline)
                self._active_pipelines.pop(pipeline.project_id, None)
            self._execution_tasks.pop(pipeline_id, None)

    def _cleanup_pipeline_agents(self, pipeline: Pipeline) -> None:
        for agent_id in pipeline.agents:
            agent_service.release_agent_from_project(agent_id, pipeline.project_id)

    async def _stage_requirement_analysis(self, pipeline: Pipeline) -> None:
        pipeline.current_stage = STAGE_REQUIREMENT_ANALYSIS
        self._update_stage_status(pipeline, STAGE_REQUIREMENT_ANALYSIS, "active")

        project = project_service.get_project(pipeline.project_id)
        if not project:
            return

        # 选择参与分析的 agent（PM + 架构师优先）
        participants = self._select_stage_participants(pipeline, ["PM", "架构师"])
        participant_names = [pipeline.agent_roles.get(aid, aid) for aid in participants]

        # 根据项目类型调整分析角度
        project_type = getattr(pipeline, 'project_type', 'development')
        if project_type == "research":
            analysis_angles = "信息完整性、分析深度、潜在偏差、改进建议、优先级建议"
        elif project_type == "content":
            analysis_angles = "内容完整性、受众匹配度、潜在问题、改进建议、优先级建议"
        elif project_type == "analysis":
            analysis_angles = "数据完整性、分析方法、潜在偏差、改进建议、优先级建议"
        else:
            analysis_angles = "需求完整性、技术可行性、潜在风险、改进建议、优先级建议"

        pipeline.add_log("requirement_analysis",
            f"需求分析启动 — 参与者({len(participants)}): {participant_names}, "
            f"需求: {project.requirements[:150]}...")

        if len(participants) < 2:
            pipeline.add_log("requirement_analysis",
                f"参与者不足(仅{len(participants)}人，需>=2)，回退到单 LLM 分析", "warning")
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
                    "分析角度": analysis_angles,
                    "团队成员": ", ".join(
                        f"{pipeline.agent_roles.get(aid, aid)}" for aid in participants
                    ),
                },
                agent_ids=participants,
                max_rounds=2,
            )

            # 先保存分析上下文，供 merge 使用
            pipeline.context["analysis_angles"] = analysis_angles
            pipeline.context["project_type"] = project_type

            # 合并多 agent 观点为完整分析报告
            final_analysis = await self._merge_discussion_into_analysis(result, project, pipeline)

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
                logger.warning("保存需求分析产物到工作区失败", exc_info=True)

            msg = Message(
                sender_id="system",
                sender_name="Pipeline",
                channel=f"project:{pipeline.project_id}",
                content=f"✅ 多 Agent 需求分析完成 ({len(result.transcript)} 条发言, {len(participants)} 人参与)",
                message_type=MessageType.SYSTEM
            )
            await message_bus.broadcast(msg)

            pipeline.add_log("requirement_analysis",
                f"需求分析完成 — 讨论{len(result.transcript)}条发言, "
                f"共识: {result.consensus_reached}, 报告{len(final_analysis)}字符")

            # 检查是否需要用户澄清
            clarification_questions = self._extract_clarification_questions(
                result, final_analysis
            )
            if clarification_questions:
                for q in clarification_questions:
                    pipeline._human_intervention_queue.append({
                        "type": "question_for_user",
                        "task_id": None,
                        "task_title": "需求分析",
                        "agent_name": "讨论组",
                        "question": q,
                        "context": f"项目: {project.name}",
                        "options": "",
                        "timestamp": datetime.now().isoformat(),
                    })
                self.transition(pipeline, PipelineStatus.PAUSED)
                pipeline.add_log("requirement_analysis",
                    f"发现 {len(clarification_questions)} 个需要用户澄清的问题，暂停等待答复",
                    "warning")

        except Exception as e:
            tb = traceback.format_exc()
            pipeline.add_log("requirement_analysis",
                f"Agent 讨论异常: {e}，回退到单 LLM\n{tb[-300:]}", "warning")
            await self._single_llm_requirement_analysis(pipeline, project)

        pipeline.progress = 0.2

    async def _single_llm_requirement_analysis(self, pipeline: Pipeline, project) -> None:
        """单 LLM 需求分析的兜底方案"""
        project_type = getattr(pipeline, 'project_type', 'development')
        analysis_angles = pipeline.context.get("analysis_angles", "")
        analyst_role = self._analyst_role_for_type(project_type)
        analysis_prompt = self._build_requirement_analysis_prompt(project, analysis_angles)
        try:
            response = await llm_service.chat(
                messages=[
                    LLMMessage(role="system", content=registry.render("collaboration.pipeline.requirement_analysis_system", {"analyst_role": analyst_role})),
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

    async def _merge_discussion_into_analysis(self, discussion, project, pipeline: Pipeline = None) -> str:
        """将多 agent 讨论记录合并为一份完整的需求分析报告"""
        transcript_text = "\n\n".join(
            f"### {dm.agent_name} ({dm.role_label})\n{dm.content}"
            for dm in discussion.transcript
        )

        project_type = getattr(pipeline, 'project_type', 'development') if pipeline else 'development'
        analysis_angles = pipeline.context.get("analysis_angles", "") if pipeline else ""
        analyst_role = self._analyst_role_for_type(project_type)

        # 按项目类型覆盖合并报告的章节要求
        if project_type == "research":
            merge_sections = (
                "1. 信息完整性分析\n"
                "2. 分析深度与视角评估\n"
                "3. 潜在偏差与盲区\n"
                "4. 改进建议\n"
                "5. 优先级建议"
            )
        elif project_type == "content":
            merge_sections = (
                "1. 内容完整性分析\n"
                "2. 受众匹配度评估\n"
                "3. 潜在问题\n"
                "4. 改进建议\n"
                "5. 优先级建议"
            )
        else:
            merge_sections = (
                "1. 需求完整性分析\n"
                "2. 技术可行性分析\n"
                "3. 潜在风险\n"
                "4. 改进建议\n"
                "5. 优先级建议"
            )

        try:
            # 直接用项目类型感知的角色和结构，不依赖 registry 变量渲染
            system_content = (
                f"你是一位{analyst_role}。请将以下多 Agent 讨论合并为一份完整的需求分析报告。"
                f"保留所有有价值的分歧和不同视角。"
                f"遵循第一性原理：分析角度要与项目类型匹配，不做过度分析。"
            )

            response = await llm_service.chat(
                messages=[
                    LLMMessage(role="system", content=system_content),
                    LLMMessage(
                        role="user",
                        content=registry.render("collaboration.pipeline.merge_analysis", {
                            "project_name": project.name,
                            "project_description": project.description,
                            "requirements": project.requirements,
                            "transcript_text": transcript_text,
                            "analysis_angles": merge_sections,
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

    def _build_requirement_analysis_prompt(self, project, analysis_angles: str = "") -> str:
        if not analysis_angles:
            analysis_angles = "1. 需求完整性\n2. 技术可行性\n3. 潜在风险\n4. 改进建议\n5. 优先级建议"
        return registry.render("collaboration.pipeline.requirement_analysis", {
            "project_name": project.name,
            "project_description": project.description,
            "requirements": project.requirements,
            "analysis_angles": analysis_angles,
        })

    async def _stage_task_breakdown(self, pipeline: Pipeline, project) -> None:
        pipeline.current_stage = STAGE_TASK_BREAKDOWN

        previous_analysis = pipeline.context.get("requirement_analysis", "")
        prev_len = len(previous_analysis)
        pipeline.add_log("task_breakdown",
            f"任务拆解启动 — 需求分析长度: {prev_len}字符, Agent: {len(pipeline.agents)}个")

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
            
            exec_stages = [
                s for s in (pipeline.stages or [])
                if s.get("key") not in (STAGE_REQUIREMENT_ANALYSIS, STAGE_TASK_BREAKDOWN)
            ]
            tasks = self._parse_task_breakdown(breakdown_result, exec_stages)

            # 诊断：记录被自动修正 phase 的任务
            auto_fixed = [t for t in tasks if t.pop("_phase_auto_fixed", None)]
            if auto_fixed:
                names = ", ".join(t["title"] for t in auto_fixed)
                pipeline.add_log("task_breakdown",
                    f"⚠ {len(auto_fixed)} 个任务的 phase 值无效，已自动分配: {names}", "warning")

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
                    tags=[task_data.get("assigned_role", ""), task_data.get("phase", "execution")]
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
            
            # 汇总任务信息用于日志
            priority_counts = {}
            for t in tasks:
                p = t.get('priority', 'medium')
                priority_counts[p] = priority_counts.get(p, 0) + 1
            dep_count = sum(1 for t in tasks if t.get('dependencies'))

            pipeline.add_log("task_breakdown",
                f"任务拆解完成 — 共{len(tasks)}个任务 "
                f"(优先级分布: {priority_counts}, 含依赖: {dep_count}个)")

            # 逐任务日志
            for i, task in enumerate(tasks, 1):
                pipeline.add_log("task_breakdown",
                    f"  [{i}/{len(tasks)}] [{task.get('priority', 'medium').upper()}] {task['title']} "
                    f"— 角色: {task.get('assigned_role', '未指定')}, "
                    f"依赖: {task.get('dependencies', [])}",
                    "debug")

            # 任务已按确认阶段分配 phase 标签，pipeline.stages 保持不变
            exec_stages = [
                s.get("label", s.get("key", ""))
                for s in pipeline.stages
                if s.get("key") not in (STAGE_REQUIREMENT_ANALYSIS, STAGE_TASK_BREAKDOWN)
            ]
            pipeline.add_log("task_breakdown",
                f"任务已分配至阶段: {exec_stages}", "debug")

        except Exception as e:
            tb = traceback.format_exc()
            pipeline.add_log("task_breakdown",
                f"任务拆解失败: {str(e)}\n{tb[-400:]}", "error")
            pipeline.context["task_breakdown"] = f"Error: {str(e)}"

        pipeline.progress = 0.4

    def _build_task_breakdown_prompt(self, project, previous_analysis: str, pipeline: Pipeline) -> str:
        agent_info = "\n".join([
            f"- {agent_id}: {agent_service.get_agent(agent_id).get('name', 'Agent') if agent_service.get_agent(agent_id) else 'Agent'}"
            for agent_id in pipeline.agents if agent_service.get_agent(agent_id)
        ]) if pipeline.agents else "可用Agent信息未配置"

        project_type = getattr(pipeline, 'project_type', 'development')
        type_analysis = pipeline.context.get("project_type_analysis", {})
        type_guide = self._build_type_guide(project_type, type_analysis)

        # Build stage guide from confirmed stages (exclude meta-stages)
        exec_stages = [
            s for s in (pipeline.stages or [])
            if s.get("key") not in (STAGE_REQUIREMENT_ANALYSIS, STAGE_TASK_BREAKDOWN)
        ]
        stage_guide = ""
        if exec_stages:
            stage_labels = ", ".join(
                f'"{s.get("key")}"({s.get("label", "")})' for s in exec_stages
            )
            stage_guide = (
                f"\n## 阶段约束\n"
                f"请仅使用以下阶段作为任务的 phase 值：{stage_labels}\n"
                f"每个任务的 phase 必须是上述阶段之一，不要自行创造新阶段。"
            )

        return registry.render("collaboration.pipeline.task_breakdown", {
            "project_name": project.name,
            "requirements": project.requirements,
            "previous_analysis": previous_analysis,
            "agent_info": agent_info,
            "project_type_guide": type_guide,
            "stage_guide": stage_guide,
        })

    @staticmethod
    def _build_type_guide(project_type: str, analysis: dict) -> str:
        """根据项目类型生成任务拆解的指导指令。"""
        domain = analysis.get("domain", "")
        task_type = analysis.get("task_type", "")

        if project_type == "research":
            return (
                "\n## 项目类型：研究调研型（" + domain + "/" + task_type + "）\n"
                "这是研究调研任务，不是软件开发项目。\n"
                "任务应 ONLY 包含以下三类：\n"
                "  1. 信息收集 — 搜索、收集、整理相关资料和数据\n"
                "  2. 分析整理 — 梳理信息，提炼关键发现，对比分析\n"
                "  3. 报告撰写 — 撰写结构化的最终调研报告\n\n"
                "禁止事项：\n"
                "  - 不要生成编码任务（不要写代码、不要建管道、不要开发工具）\n"
                "  - 不要生成 Dashboard/前端开发任务\n"
                "  - 不要生成 API 设计或数据库设计任务\n"
                "  - 不要生成运维/部署任务\n\n"
                "assigned_role 必须使用研究/内容角色(如调研分析、内容撰写、信息检索)，\n"
                "不能使用后端开发、前端开发、测试工程师等开发角色。\n"
                "phase 应使用 analysis 或 delivery，不要用 coding 或 execution。"
            )
        elif project_type == "content":
            return (
                "\n## 项目类型：内容创作型（" + domain + "/" + task_type + "）\n"
                "这是内容创作任务，不是软件开发项目。\n"
                "任务应 ONLY 包含：\n"
                "  1. 内容策划 — 确定框架、大纲和风格\n"
                "  2. 内容撰写 — 撰写具体内容\n"
                "  3. 审核修改 — 校对、优化和完善\n\n"
                "禁止生成任何开发任务。角色应为内容角色。"
            )
        elif project_type == "analysis":
            return (
                "\n## 项目类型：数据分析型（" + domain + "/" + task_type + "）\n"
                "这是数据分析任务。\n"
                "任务应包括：数据收集→数据清洗→分析建模→结果呈现。\n"
                "仅在必要时编写数据处理/分析脚本，不要生成全栈开发任务。"
            )
        elif project_type == "design":
            return (
                "\n## 项目类型：设计策划型（" + domain + "/" + task_type + "）\n"
                "这是设计/策划任务。\n"
                "任务应包括：分析→构思→设计→评审。"
            )
        else:  # development (default)
            return (
                "\n## 项目类型：软件开发\n"
                "按标准开发流程拆解：需求分析→设计→编码→测试→部署。"
            )

    def _parse_task_breakdown(self, breakdown_text: str, valid_exec_stages: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        import re
        from app.services.shared.json_extractor import extract_and_validate, JSONExtractionError, JSONValidationError
        from app.services.shared.validation import TaskBreakdownResult

        valid_phases = []
        if valid_exec_stages:
            valid_phases = [s.get("key", "") for s in valid_exec_stages if s.get("key")]

        # 优先使用统一的 JSON 提取 + Pydantic 校验
        try:
            result = extract_and_validate(breakdown_text, TaskBreakdownResult)
            tasks = [t.model_dump() for t in result.tasks]
            return self._fixup_task_phases(tasks, valid_phases)
        except (JSONExtractionError, JSONValidationError):
            pass  # 回退到正则分块解析

        # Fallback: 按编号分块解析（保留对非标准格式的兼容）
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

            infer_phase = self._infer_phase_from_text(
                block, valid_phases, valid_exec_stages
            )

            task = {
                "title": title,
                "description": description,
                "assigned_role": self._infer_role(description),
                "priority": "medium",
                "phase": infer_phase or "execution",
                "dependencies": [],
                "acceptance_criteria": []
            }

            if "[high]" in block.lower() or "[高]" in block:
                task["priority"] = "high"
            elif "[low]" in block.lower() or "[低]" in block:
                task["priority"] = "low"

            tasks.append(task)

        return self._fixup_task_phases(tasks, valid_phases)

    def _infer_phase_from_text(
        self, text: str, valid_phases: List[str], valid_stages: List[Dict[str, Any]] = None
    ) -> str:
        """Try to match task text against valid stage labels/keys to infer phase."""
        text_lower = text.lower()
        if valid_stages:
            for s in valid_stages:
                key = s.get("key", "")
                label = s.get("label", "")
                if key and key.lower() in text_lower:
                    return key
                if label and label in text:
                    return key
        if valid_phases:
            for p in valid_phases:
                if p.lower() in text_lower:
                    return p
        return ""

    def _fixup_task_phases(
        self, tasks: List[Dict[str, Any]], valid_phases: List[str]
    ) -> List[Dict[str, Any]]:
        """Validate and fix task phase values to match valid stage keys.
        Returns the (possibly modified) task list."""
        if not valid_phases:
            return tasks

        for i, task in enumerate(tasks):
            original = task.get("phase", "")
            if original and original in valid_phases:
                continue  # OK, matches a stage key

            # Invalid or missing phase — assign based on task index vs stage count
            stage_idx = i % len(valid_phases)
            corrected = valid_phases[stage_idx]
            task["phase"] = corrected
            task["_phase_auto_fixed"] = True  # marker for caller diagnostic logging

        return tasks

    def _infer_role(self, description: str) -> str:
        desc_lower = description.lower()
        if any(keyword in desc_lower for keyword in ["调研", "研究", "分析", "research", "报告", "调查"]):
            return "调研分析"
        elif any(keyword in desc_lower for keyword in ["数据", "统计", "可视化", "data", "图表"]):
            return "数据分析"
        elif any(keyword in desc_lower for keyword in ["文案", "写作", "撰写", "文档", "内容", "翻译"]):
            return "内容撰写"
        elif any(keyword in desc_lower for keyword in ["查询", "检索", "搜索", "查找", "信息", "资料"]):
            return "信息检索"
        elif any(keyword in desc_lower for keyword in ["设计", "方案", "规划", "架构", "architecture"]):
            return "方案设计"
        elif any(keyword in desc_lower for keyword in ["前端", "界面", "UI", "frontend", "react", "vue"]):
            return "前端开发"
        elif any(keyword in desc_lower for keyword in ["后端", "API", "数据库", "backend", "server"]):
            return "后端开发"
        elif any(keyword in desc_lower for keyword in ["测试", "test", "QA", "质量", "验证"]):
            return "质量审核"
        return "通用执行"

    async def _stage_task_execution(self, pipeline: Pipeline, stage_key: str = None) -> None:
        """DAG 并行执行阶段 — 拓扑排序 + 依赖阻塞 + 安全守卫。
        当 stage_key 指定时，仅执行 tags 中包含该 key 的任务。
        """
        # 层级策略下确保有 coordinator
        await self._ensure_coordinator(pipeline)

        # 构建 DAG: task_id → Task 对象，按 stage_key 过滤
        all_tasks: Dict[str, Any] = {}
        for task_id in pipeline.task_ids:
            task = task_board.get_task(task_id)
            if task:
                # 按阶段过滤：仅执行属于当前阶段的任务
                if stage_key:
                    task_tags = getattr(task, 'tags', []) or []
                    if stage_key not in task_tags:
                        continue
                all_tasks[task_id] = task

        # 防御性检查：stage_key 过滤后 0 个任务，但 pipeline 有未完成任务
        if stage_key and not all_tasks and pipeline.task_ids:
            # 收集现有任务的 tags 用于诊断
            unmatched_tags = set()
            for task_id in pipeline.task_ids:
                task = task_board.get_task(task_id)
                if task:
                    for t in (getattr(task, 'tags', []) or []):
                        unmatched_tags.add(t)
            pipeline.add_log("task_execution",
                f"阶段「{stage_key}」未匹配到任何任务！"
                f"现有任务 tags: {sorted(unmatched_tags)}，阶段 key: {stage_key}"
                f" — 可能原因: AI 返回的 phase 值与阶段 key 不匹配",
                "warning")

        # 拓扑排序获取执行层级
        execution_levels = self._topological_sort(all_tasks)

        # 恢复时：预填充已完成/失败的任务
        completed_tasks: set = set()
        failed_tasks: set = set()
        pre_completed = 0
        pre_failed = 0
        for task_id, task in all_tasks.items():
            status = getattr(task, 'status', None)
            if status in (TaskStatus.DONE, TaskStatus.REVIEW):
                completed_tasks.add(task_id)
                pre_completed += 1
            elif status == TaskStatus.CANCELLED:
                failed_tasks.add(task_id)
                pre_failed += 1

        pipeline.add_log("task_execution",
            f"DAG 任务执行启动 — 总任务: {len(pipeline.task_ids)}, "
            f"DAG层级: {len(execution_levels)}, "
            f"已恢复完成: {pre_completed}, 已恢复失败: {pre_failed}, "
            f"待执行: {len(pipeline.task_ids) - pre_completed - pre_failed}")

        for level_idx, level in enumerate(execution_levels):
            if pipeline.status == PipelineStatus.PAUSED or pipeline.stop_requested or security_guard.is_emergency:
                pipeline.add_log("task_execution", "执行已暂停/停止/紧急中断", "warning")
                break

            level_tasks_info = []
            for tid in level:
                t = all_tasks.get(tid)
                title = getattr(t, 'title', tid) if t else tid
                status = getattr(t, 'status', '?') if t else '?'
                level_tasks_info.append(f"{title[:30]}({status.value if hasattr(status, 'value') else status})")
            pipeline.add_log("task_execution",
                f"DAG Level {level_idx + 1}/{len(execution_levels)}: {len(level)}个任务 — {level_tasks_info}")

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

            # 更新进度（只统计真正完成的任务，取消/失败不计入进度）
            total_tasks = len(pipeline.task_ids)
            done = len(completed_tasks)
            failed = len(failed_tasks)
            pipeline.progress = 0.4 + (0.4 * done / total_tasks) if total_tasks > 0 else 0.8
            pipeline.add_log("task_execution",
                f"进度: {pipeline.progress:.0%} — 完成:{done} 失败/取消:{failed} 剩余:{total_tasks - done - failed}",
                "debug")

        # 汇总
        total = len(pipeline.task_ids)
        done_count = len(completed_tasks)
        failed_count = len(failed_tasks)
        remaining = total - done_count - failed_count
        pipeline.add_log("task_execution",
            f"DAG执行结束 — 总计:{total} 完成:{done_count} 失败/取消:{failed_count} "
            f"未执行:{remaining}, 进度→0.8")

        pipeline.progress = 0.8

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
            dep_task = all_tasks.get(dep_id)
            dep_title = getattr(dep_task, 'title', dep_id) if dep_task else dep_id
            if dep_id in failed_tasks:
                pipeline.add_log("task_execution",
                    f"任务「{task.title}」依赖「{dep_title}」已失败 → 取消", "warning")
                await task_board.change_status(task_id, TaskStatus.CANCELLED, "pipeline")
                await task_board.add_comment(task_id, f"取消: 依赖任务 {dep_title} 失败", "pipeline")
                return False
            if dep_id not in completed_tasks:
                pipeline.add_log("task_execution",
                    f"任务「{task.title}」依赖「{dep_title}」未完成 → 阻塞", "debug")
                await task_board.change_status(task_id, TaskStatus.BLOCKED, "pipeline")
                await task_board.add_comment(task_id, f"阻塞: 等待依赖任务 {dep_title}", "pipeline")
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
            pipeline.add_log("task_execution",
                f"任务「{task.title}」风险级别 {risk_level.value} → 需人工审批，阻塞", "warning")
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
            pipeline.add_log("task_execution",
                f"任务「{task.title}」无法分配Agent — 无可用Agent", "error")
            await task_board.add_comment(task_id, "无可用Agent", "pipeline")
            return False

        # 持久化 assigned_agents (BUG #3 fix)
        await task_board.assign_agents(task_id, [agent_id])

        agent_info = agent_service.get_agent(agent_id)
        agent_name = agent_info.get("name", agent_id) if agent_info else agent_id
        pipeline.add_log("task_execution",
            f"任务「{task.title}」→ Agent [{agent_name}] 开始执行 (风险: {risk_level.value})")

        # 构建上游依赖任务清单，注入任务描述（BUG #2 fix: pull 模型）
        original_description = task.description or ""
        upstream_manifest = self._build_upstream_manifest(task, all_tasks, pipeline.project_id)
        if upstream_manifest:
            task.description = f"{original_description}\n\n{upstream_manifest}"

        # 通知
        msg = Message(
            sender_id="system",
            sender_name="Pipeline",
            channel=f"task:{task_id}",
            content=f"⚡ Agent {agent_id} 开始执行: {task.title} [风险: {risk_level.value}]",
            message_type=MessageType.SYSTEM
        )
        await message_bus.send_to_task(msg, task_id)

        # 执行（含超时重试）
        max_attempts = 2
        last_error = None
        for attempt in range(1, max_attempts + 1):
            if pipeline.stop_requested:
                break
            if attempt > 1:
                pipeline.add_log("task_execution",
                    f"重试任务「{task.title}」(第 {attempt} 次)...", "warning")
                await asyncio.sleep(2)

            try:
                result = await agent_executor.execute_task_with_agent(task_id, agent_id)
                # 恢复原始描述
                task.description = original_description
                success = result.get("success", False)
                waiting_for_user = result.get("waiting_for_user", False)

                if waiting_for_user:
                    # Agent 向用户提问，任务已由 agent_executor 设为 WAITING_FOR_USER
                    pipeline.add_log("task_execution",
                        f"⏸ 任务「{task.title}」→ WAITING_FOR_USER — Agent [{agent_name}] 需要用户澄清",
                        "warning")
                    self.transition(pipeline, PipelineStatus.PAUSED)
                    last_error = None
                    break  # 退出重试循环，等待用户答复

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
                    pipeline.add_log("task_execution",
                        f"✓ 任务「{task.title}」完成 → REVIEW (Agent: {agent_name})")
                else:
                    err_msg = result.get('error', 'Unknown')
                    await task_board.change_status(task_id, TaskStatus.CANCELLED, agent_id)
                    await task_board.add_comment(task_id,
                        f"执行失败: {err_msg}", "pipeline")
                    pipeline.add_log("task_execution",
                        f"✗ 任务「{task.title}」失败 → CANCELLED (Agent: {agent_name}, 原因: {err_msg[:200]})", "error")

                last_error = None
                break  # 成功或非超时失败，退出重试

            except asyncio.TimeoutError:
                last_error = f"LLM 调用超时 (attempt {attempt}/{max_attempts})"
                pipeline.add_log("task_execution",
                    f"任务「{task.title}」尝试 {attempt}/{max_attempts} 超时", "warning")
                continue
            except Exception as e:
                err_str = str(e)
                # 仅超时类异常触发重试
                if "timeout" in err_str.lower() or "timed out" in err_str.lower():
                    last_error = f"{err_str} (attempt {attempt}/{max_attempts})"
                    pipeline.add_log("task_execution",
                        f"任务「{task.title}」尝试 {attempt}/{max_attempts} 超时类异常", "warning")
                    continue
                last_error = err_str
                break  # 非超时异常，不重试

        if last_error:
            # 恢复原始描述
            task.description = original_description

            # 断路器记录
            await security_guard.record_operation_result(
                agent_id=agent_id,
                operation=OperationType.GENERATE_CODE,
                success=False
            )

            tb = traceback.format_exc()
            pipeline.add_log("task_execution",
                f"✗ 任务「{task.title}」执行失败 (重试{max_attempts-1}次后) — {last_error}\n{tb[-300:]}", "error")
            await task_board.add_comment(task_id,
                f"执行失败 (重试后): {last_error}", "pipeline")

            audit_logger.log(
                action=AuditAction.TASK_EXECUTED,
                actor=agent_id,
                agent_id=agent_id,
                target=task_id,
                outcome="error",
                detail=str(last_error),
            )

            return False

        return success  # result.get("success", False)

    def _build_upstream_manifest(
        self, task, all_tasks: Dict[str, Any], project_id: str
    ) -> str:
        """构建上游依赖任务产出物清单（pull 模型）。
        告知下游 agent 哪些前置任务已完成、产出物在哪，agent 用 list_files/read_file 按需拉取。
        """
        deps = getattr(task, 'dependencies', []) or []
        if not deps:
            return ""

        from app.services.project.workspace_manager import workspace_manager as _wm

        # 提前获取所有产出物文件列表（只调用一次）
        try:
            all_artifact_files = _wm.list_artifact_files(project_id)
        except Exception:
            all_artifact_files = []

        items = []
        for dep_id in deps:
            dep_task = all_tasks.get(dep_id)
            if not dep_task:
                continue
            dep_title = getattr(dep_task, 'title', dep_id)
            dep_phase = getattr(dep_task, 'phase', '')
            dep_desc = getattr(dep_task, 'description', '') or ''
            # 只取前 100 字符作为摘要
            dep_summary = dep_desc[:100] + "..." if len(dep_desc) > 100 else dep_desc
            line = f"- **{dep_title}** (阶段: {dep_phase or '无'})\n  摘要: {dep_summary}"

            # 匹配与上游任务相关的产出物文件
            safe_title = re.sub(r'[\s\\/:*?"<>|]+', '_', dep_title).strip('_')
            matched = [af["path"] for af in all_artifact_files if safe_title[:15] in af["name"]]
            if matched:
                line += f"\n  产出物文件: {', '.join(matched)}"

            items.append(line)

        if not items:
            return ""

        return registry.render("agent.executor.upstream_manifest", {
            "upstream_items": "\n\n".join(items),
        })

    async def _assign_task_to_agent(self, task, pipeline: Pipeline) -> Optional[str]:
        """策略感知的 Agent 分配。核心流程：trait 匹配优先 → 队列兜底。"""
        if not pipeline.agents:
            pipeline.add_log("task_execution",
                f"分配失败: 任务「{task.title}」— pipeline 无 Agent", "warning")
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
                    top3 = [(aid, f"{s:.2f}") for aid, s in matches[:3]]
                    pipeline.add_log("task_execution",
                        f"Trait匹配: 「{task.title}」技能={required_skills} → "
                        f"最佳={matches[0][0]}({matches[0][1]:.2f}), 候选: {top3}")
                    return matches[0][0]
            except Exception as e:
                pipeline.add_log("task_execution",
                    f"Trait匹配失败: {e}，回退到策略分配", "warning")

        # 策略感知分配
        selected: Optional[str] = None
        if strategy == "sequential":
            selected = self._assign_sequential(task_tags, pipeline)
        elif strategy == "hierarchical":
            selected = await self._assign_hierarchical(task_tags, pipeline)
        elif strategy == "discussion":
            selected = self._assign_discussion(task_tags, pipeline)
        else:  # "auto"
            selected = self._assign_best_match(task_tags, pipeline)

        if selected:
            agent_info = agent_service.get_agent(selected)
            agent_name = agent_info.get("name", selected) if agent_info else selected
            pipeline.add_log("task_execution",
                f"分配决策: 「{task.title}」→ [{agent_name}] (策略: {strategy}, "
                f"角色: {pipeline.agent_roles.get(selected, '未指定')})",
                "debug")

        return selected

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

    @staticmethod
    def _analyst_role_for_type(project_type: str) -> str:
        """根据项目类型返回需求分析的角色定位。"""
        roles = {
            "research": "资深研究分析师",
            "content": "资深内容策划",
            "analysis": "资深数据分析师",
            "design": "资深设计顾问",
            "development": "资深产品经理",
        }
        return roles.get(project_type, "资深产品经理")

    @staticmethod
    def _domain_to_project_type(domain: str) -> str:
        """将 TaskAnalyzer 的领域分类映射为项目类型。支持逗号分隔的多领域字符串。"""
        mapping = {
            "信息查询": "research",
            "分析研究": "research",
            "文案写作": "content",
            "软件开发": "development",
            "数据分析": "analysis",
            "设计创意": "design",
        }
        # 处理逗号分隔的多领域字符串，优先级: research > analysis > content > design > development
        domains = [d.strip() for d in domain.replace("，", ",").split(",")]
        priority = ["research", "analysis", "content", "design", "development"]
        found_types = set()
        for d in domains:
            if d in mapping:
                found_types.add(mapping[d])
        for pt in priority:
            if pt in found_types:
                return pt
        return "development"

    async def _rebuild_stages_from_tasks(self, pipeline: Pipeline) -> None:
        """从已保存的任务中重建 pipeline.stages（用于恢复场景）。"""
        phase_labels = {
            "analysis": "分析", "execution": "执行",
            "review": "审查", "testing": "测试", "delivery": "交付",
        }
        seen_keys = set()
        stages = [
            {"key": "requirement_analysis", "label": "需求分析", "status": "completed"},
            {"key": "task_breakdown", "label": "任务拆解", "status": "completed"},
        ]
        for task_id in pipeline.task_ids:
            task = task_board.get_task(task_id)
            if not task or not task.tags:
                continue
            for tag in task.tags:
                if tag in phase_labels and tag not in seen_keys:
                    seen_keys.add(tag)
                    stages.append({"key": tag, "label": phase_labels.get(tag, tag), "status": "pending"})
        stages.append({"key": "review", "label": "审查", "status": "pending"})
        pipeline.stages = stages
        pipeline.add_log("task_breakdown", f"从 {len(pipeline.task_ids)} 个任务重建阶段", "debug")

    @staticmethod
    def _extract_clarification_questions(discussion_result, final_analysis: str) -> list:
        """从讨论报告和记录中提取需要用户澄清的问题。"""
        import re
        questions = []

        # 1. 从合并报告中提取 "需要用户澄清" 章节
        clar_section = re.search(
            r'##\s*需要用户澄清\s*\n(.*?)(?=\n##|\Z)',
            final_analysis, re.DOTALL
        )
        if clar_section:
            for line in clar_section.group(1).strip().split('\n'):
                line = line.strip()
                # 匹配 "- xxx?" 或 "- **xxx?**"
                q_match = re.match(r'[-*]\s*(?:\*\*)?(.+?\?)(?:\*\*)?$', line)
                if q_match:
                    questions.append(q_match.group(1).strip())

        # 2. 从讨论记录中提取 [NEEDS_CLARIFICATION] 标记
        for msg in getattr(discussion_result, 'transcript', []) or []:
            content = getattr(msg, 'content', '') if hasattr(msg, 'content') else str(msg)
            if '[NEEDS_CLARIFICATION]' in content:
                # 提取标记后的所有问题行
                parts = content.split('[NEEDS_CLARIFICATION]', 1)
                if len(parts) > 1:
                    for line in parts[1].strip().split('\n'):
                        line = line.strip()
                        q_match = re.match(r'[-*]\s*(.+?\?)', line)
                        if q_match:
                            q = q_match.group(1).strip()
                            if q not in questions:
                                questions.append(q)

        return questions

    @staticmethod
    def _update_stage_status(pipeline, stage_key: str, status: str) -> None:
        """更新 pipeline.stages 中指定阶段的状态 (BUG #4 fix)。"""
        for stage in (pipeline.stages or []):
            if stage.get("key") == stage_key:
                stage["status"] = status
                return

    def _select_stage_participants(
        self,
        pipeline: Pipeline,
        preferred_roles: List[str] = None,
    ) -> List[str]:
        """所有 agent 参与所有阶段——配置阶段不预设角色分工。"""
        return list(pipeline.agents)

    async def _stage_review(self, pipeline: Pipeline) -> None:
        self._update_stage_status(pipeline, "review", "active")

        review_tasks = task_board.get_tasks_by_status(TaskStatus.REVIEW, project_id=pipeline.project_id)
        done_tasks = task_board.get_tasks_by_status(TaskStatus.DONE, project_id=pipeline.project_id)
        cancelled_tasks = task_board.get_tasks_by_status(TaskStatus.CANCELLED, project_id=pipeline.project_id)

        pipeline.add_log("review",
            f"审查阶段启动 — 待审核: {len(review_tasks)}, "
            f"已完成: {len(done_tasks)}, 已取消: {len(cancelled_tasks)}, "
            f"总任务: {len(pipeline.task_ids)}")

        msg = Message(
            sender_id="system",
            sender_name="Pipeline",
            channel=f"project:{pipeline.project_id}",
            content=f"🔍 开始审核阶段... (待审核: {len(review_tasks)}, 已取消: {len(cancelled_tasks)})",
            message_type=MessageType.SYSTEM
        )
        await message_bus.broadcast(msg)

        if not review_tasks:
            if done_tasks:
                # 有已完成的任务（跳过审核直接完成），项目正常结束
                pipeline.add_log("review", f"无待审核任务，{len(done_tasks)} 个任务已完成", "info")
                pipeline.progress = 1.0
            elif not pipeline.task_ids:
                # 无任务创建（空项目），正常结束
                pipeline.add_log("review", "无任务，项目完成", "info")
                pipeline.progress = 1.0
            else:
                # 有任务但全部取消/失败/未执行 — 项目失败
                cancelled = task_board.get_tasks_by_status(TaskStatus.CANCELLED, project_id=pipeline.project_id)
                pipeline.add_log("review",
                    f"无已完成任务（{len(cancelled)} 个已取消），项目标记为失败", "error")
                msg = Message(
                    sender_id="system",
                    sender_name="Pipeline",
                    channel=f"project:{pipeline.project_id}",
                    content=f"⚠️ 项目失败：所有 {len(pipeline.task_ids)} 个任务均未完成",
                    message_type=MessageType.SYSTEM
                )
                await message_bus.broadcast(msg)
                self.transition(pipeline, PipelineStatus.FAILED)
            return

        # 选择参与者（测试 + 架构师优先，确保多视角审查）
        participants = self._select_stage_participants(pipeline, ["测试工程师", "架构师"])

        if len(participants) < 2:
            # 单人审查 — 直接用 LLM
            review_result = await self._single_llm_review(pipeline, review_tasks)
        else:
            # 多 Agent 审查讨论
            tasks_summary = self._build_tasks_summary_for_discussion(review_tasks)
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
                review_result = await self._merge_discussion_into_review(result, review_tasks)
                pipeline.context["review_discussion"] = {
                    "transcript": [m.model_dump(mode='json') for m in result.transcript],
                    "consensus": result.consensus_reached,
                    "participants": participants,
                }
            except Exception as e:
                pipeline.add_log("review", f"Agent 讨论失败: {e}，回退到单 LLM", "warning")
                review_result = await self._single_llm_review(pipeline, review_tasks)

        pipeline.context["review"] = review_result

        # 保存审查报告到 workspace
        from app.services.project.workspace_manager import workspace_manager
        try:
            workspace_manager.add_artifact(
                pipeline.project_id, "review",
                "review_report.md", review_result,
            )
        except Exception:
            logger.warning("保存审查报告到工作区失败", exc_info=True)

        msg = Message(
            sender_id="system",
            sender_name="Pipeline",
            channel=f"project:{pipeline.project_id}",
            content=f"✅ 审核完成",
            message_type=MessageType.SYSTEM
        )
        await message_bus.broadcast(msg)

        # 基于风险等级自动审批任务（使用枚举直接比较，避免字符串转换歧义）
        auto_approved = 0
        pending_approval = 0
        for task in review_tasks:
            risk = getattr(task, 'risk_level', None)
            task_id_val = getattr(task, 'id', str(task))
            # 默认低风险自动通过，空值兜底也自动通过
            is_auto = risk is None or risk in (RiskLevel.LOW, RiskLevel.MEDIUM)
            is_high = risk == RiskLevel.HIGH
            if is_auto:
                await task_board.change_status(task_id_val, TaskStatus.DONE, "system")
                auto_approved += 1
            elif is_high:
                pending_approval += 1
            else:
                # CRITICAL 或其他未知级别 — 保守起见保持 REVIEW
                pending_approval += 1

        pipeline.add_log("review",
            f"审查完成: {len(participants)} 位 Agent 参与, "
            f"自动通过: {auto_approved}, 待人工审批: {pending_approval}")

        if pending_approval > 0:
            msg = Message(
                sender_id="system",
                sender_name="Pipeline",
                channel=f"project:{pipeline.project_id}",
                content=f"⏳ {pending_approval} 个高风险任务需要人工审批。其他阶段已完成。",
                message_type=MessageType.SYSTEM
            )
            await message_bus.broadcast(msg)
        else:
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

    async def _trigger_learning_cycle(self, pipeline: Pipeline) -> None:
        """Step 10: 从 pipeline 执行中提取经验，写入技能库和 growth.json"""
        from app.services.agent.agent_service import agent_service

        try:
            from app.services.learning.intelligent_learning import get_learning_service
            learning = await get_learning_service()
        except Exception:
            pipeline.add_log("learning", "学习服务不可用，跳过", "info")
            return

        for agent_id in pipeline.agents:
            agent = agent_service.get_agent(agent_id)
            if not agent:
                continue

            decisions = self._extract_decisions_for_agent(pipeline, agent_id)
            if not decisions:
                continue

            project = project_service.get_project(pipeline.project_id)
            try:
                skill = await learning.learn_from_task(
                    agent_id=agent_id,
                    task_description=project.name if project else pipeline.name,
                    decisions=decisions,
                    outcomes={
                        "project_id": pipeline.project_id,
                        "status": pipeline.status.value,
                        "tasks_completed": len(pipeline.task_ids),
                    },
                    success="success",
                )
                if skill:
                    pipeline.add_log("learning", f"Agent {agent_id} 习得技能: {skill.name}")

                    # Update growth.json
                    try:
                        self._update_growth_file(agent, skill, pipeline)
                    except Exception as e:
                        pipeline.add_log("learning", f"growth.json 更新失败: {e}", "warning")
            except Exception as e:
                pipeline.add_log("learning", f"Agent {agent_id} 学习失败: {e}", "warning")

        # 手动晋升：将本次任务中高频使用的记忆晋升到更高层级
        await self._promote_key_memories(pipeline)

    async def _promote_key_memories(self, pipeline: Pipeline) -> None:
        """复盘后手动晋升关键记忆（双轨晋升的手动轨）"""
        try:
            from app.services.memory.persistent_memory_manager import PersistentMemoryManager
            from app.services.memory.memory_promotion import promotion_service

            manager = PersistentMemoryManager()
            promoted_count = 0

            for agent_id in pipeline.agents:
                memories = await manager.get_agent_memories(agent_id)
                if not memories:
                    continue

                memory_dicts = []
                for m in memories:
                    memory_dicts.append({
                        "id": m.id,
                        "level": m.level,
                        "usage_count": m.usage_count,
                        "relevance_score": m.relevance_score,
                        "created_at": m.created_at,
                    })

                # 晋升使用次数 ≥ 3 的 L1 记忆到 L2
                candidates = promotion_service.manual_promote(
                    memory_dicts,
                    [m["id"] for m in memory_dicts if m["usage_count"] >= 3 and m["level"] == "working"],
                    "short_term",
                )

                for memory_data, target_level in candidates:
                    success = await manager.promote_memory(memory_data["id"], target_level)
                    if success:
                        promoted_count += 1

            if promoted_count > 0:
                pipeline.add_log("learning", f"手动晋升 {promoted_count} 条关键记忆")
        except Exception as e:
            pipeline.add_log("learning", f"手动晋升记忆失败: {e}", "warning")

    def _extract_decisions_for_agent(self, pipeline: Pipeline, agent_id: str) -> list:
        """从 pipeline 日志中提取某 agent 的决策记录"""
        decisions = []
        for entry in pipeline.logs:
            if hasattr(entry, 'agent_id') and entry.agent_id == agent_id:
                decisions.append({
                    "step": len(decisions) + 1,
                    "action": getattr(entry, 'message', '')[:200],
                    "reasoning": "",
                })
        if not decisions:
            # 兜底：用 pipeline 阶段日志
            for i, entry in enumerate(pipeline.logs[-10:]):
                decisions.append({
                    "step": i + 1,
                    "action": getattr(entry, 'message', str(entry))[:200],
                    "reasoning": "",
                })
        return decisions

    def _update_growth_file(self, agent: dict, skill, pipeline: Pipeline) -> None:
        """更新 agent 的 growth.json 文件"""
        from pathlib import Path

        soul_data = agent.get("soul_data", {})
        soul_name = soul_data.get("name", agent.get("name", ""))
        if not soul_name:
            return

        growth_path = Path(f"agents/agent_{soul_name}/growth.json")
        growth_path.parent.mkdir(parents=True, exist_ok=True)

        import json
        growth = {}
        if growth_path.exists():
            try:
                with open(growth_path, "r", encoding="utf-8") as f:
                    growth = json.load(f)
            except Exception:
                growth = {}

        if not growth:
            growth = {
                "soul_name": soul_name,
                "version": 1,
                "updated_at": "",
                "stats": {"total_projects": 0, "successful_projects": 0, "success_rate": 0.0, "total_tasks": 0, "skills_count": 0},
                "skills": [],
                "recent_trajectories": [],
            }

        # Update skills
        skills = growth.get("skills", [])
        skill_entry = {
            "id": getattr(skill, 'id', ''),
            "name": getattr(skill, 'name', ''),
            "category": getattr(skill, 'category', ''),
            "success_rate": getattr(skill, 'success_rate', 0.0),
            "usage_count": getattr(skill, 'usage_count', 1),
            "trigger_keywords": getattr(skill, 'trigger_keywords', []),
            "description": getattr(skill, 'description', ''),
        }
        if not any(s.get("id") == skill_entry["id"] for s in skills):
            skills.append(skill_entry)
        growth["skills"] = skills

        # Add trajectory
        project = project_service.get_project(pipeline.project_id)
        trajectory = {
            "project": project.name if project else pipeline.name,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "success": True,
        }
        trajectories = growth.get("recent_trajectories", [])
        trajectories.insert(0, trajectory)
        growth["recent_trajectories"] = trajectories[:10]

        # Update stats
        total_projects = len(trajectories)
        successful = sum(1 for t in trajectories if t.get("success"))
        growth["stats"] = {
            "total_projects": total_projects,
            "successful_projects": successful,
            "success_rate": round(successful / total_projects, 2) if total_projects else 0.0,
            "total_tasks": sum(s.get("usage_count", 0) for s in growth.get("skills", [])),
            "skills_count": len(growth.get("skills", [])),
        }
        growth["updated_at"] = datetime.now().isoformat()
        growth["version"] = growth.get("version", 1) + 0.1

        with open(growth_path, "w", encoding="utf-8") as f:
            json.dump(growth, f, ensure_ascii=False, indent=2, default=str)

    async def confirm_stages(
        self, pipeline_id: str, stages: List[Dict[str, Any]]
    ) -> bool:
        """确认阶段配置。必须在 start_pipeline 之前调用。"""
        async with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if not pipeline:
                return False

            if pipeline.status == PipelineStatus.RUNNING:
                return False  # already running, can't reconfigure

            pipeline.stages = stages
            pipeline.current_stage = stages[0].get("key", "") if stages else ""
            pipeline.context["stages_confirmed"] = True
            pipeline.add_log("init",
                f"阶段已确认: {[s.get('label', s.get('key', '')) for s in stages]}")

            # Persist to workspace project.json
            try:
                from app.services.project.workspace_manager import workspace_manager
                workspace_manager.update_stages(pipeline.project_id, stages)
            except Exception:
                logger.warning("更新工作区阶段状态失败", exc_info=True)

            if self._db:
                await self._db.save(pipeline)
            return True

    async def respond_to_agent(
        self, pipeline_id: str, answer: str, task_id: str = None
    ) -> bool:
        """用户答复 Agent 的提问，恢复任务执行。"""
        async with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if not pipeline:
                return False

            # 1. 找到等待中的任务并注入用户答复
            if task_id:
                task = task_board.get_task(task_id)
                if task and task.status == TaskStatus.WAITING_FOR_USER:
                    # 将用户答复写入任务评论
                    await task_board.add_comment(
                        task_id,
                        f"👤 **用户答复:** {answer}",
                        "human",
                    )
                    # 将答复注入任务描述，Agent 恢复执行时能看到
                    original_desc = task.description or ""
                    task.description = (
                        f"{original_desc}\n\n## 用户答复\n{answer}"
                    )
                    task.updated_at = datetime.now()
                    # 恢复任务
                    await task_board.change_status(task_id, TaskStatus.IN_PROGRESS, "human")
                    pipeline.add_log("intervention",
                        f"用户答复任务「{task.title}」: {answer[:100]}")

            # 2. 清理干预队列中的相关条目
            pipeline._human_intervention_queue = [
                item for item in pipeline._human_intervention_queue
                if not (
                    item.get("type") == "question_for_user"
                    and (task_id is None or item.get("task_id") == task_id)
                )
            ]

            # 3. 将答复写入 pipeline 上下文，供后续阶段使用
            if "user_responses" not in pipeline.context:
                pipeline.context["user_responses"] = []
            pipeline.context["user_responses"].append({
                "task_id": task_id,
                "answer": answer,
                "timestamp": datetime.now().isoformat(),
            })

            # 4. 恢复 pipeline
            self.transition(pipeline, PipelineStatus.RUNNING)
            self._active_pipelines[pipeline.project_id] = pipeline_id

            # 5. 启动新的执行任务继续处理
            if pipeline_id in self._execution_tasks:
                old_task = self._execution_tasks.pop(pipeline_id, None)
                if old_task and not old_task.done():
                    old_task.cancel()
            new_task = asyncio.create_task(self._run_pipeline(pipeline_id))
            self._execution_tasks[pipeline_id] = new_task

            pipeline.add_log("intervention",
                f"用户答复已注入，流水线恢复执行 — task: {task_id or 'all'}")
            if self._db:
                await self._db.save(pipeline)
            return True

    async def approve_task(self, pipeline_id: str, task_id: str) -> bool:
        """人工审批通过 REVIEW 状态的任务，转为 DONE。"""
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return False
        task = task_board.get_task(task_id)
        if not task:
            return False
        if task.status != TaskStatus.REVIEW:
            return False
        await task_board.change_status(task_id, TaskStatus.DONE, "human_approver")
        await task_board.add_comment(task_id, "人工审批通过", "human_approver")
        pipeline.add_log("review", f"任务「{task.title}」已人工审批通过")
        # 如果有待审批任务全部通过，解除暂停
        remaining = task_board.get_tasks_by_status(TaskStatus.REVIEW, project_id=pipeline.project_id)
        if not remaining:
            self.transition(pipeline, PipelineStatus.RUNNING)
            pipeline.add_log("review", "所有任务审批完成，流水线可继续")
        return True

    async def pause_pipeline(self, pipeline_id: str) -> bool:
        async with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if not pipeline or pipeline.status != PipelineStatus.RUNNING:
                return False

            self.transition(pipeline, PipelineStatus.PAUSED)
            await agent_executor.pause_project(pipeline.project_id)
            speaking_controller.set_mode(pipeline_id, SpeakingMode.FREE_STYLE)

            pipeline.add_log("control",
                f"流水线已暂停 — 阶段: {pipeline.current_stage}, "
                f"进度: {pipeline.progress:.0%}, 任务: {len(pipeline.task_ids)}个")
            if self._db:
                await self._db.save(pipeline)
            return True

    async def resume_pipeline(self, pipeline_id: str) -> bool:
        async with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if not pipeline or pipeline.status != PipelineStatus.PAUSED:
                return False

            self.transition(pipeline, PipelineStatus.RUNNING)
            await agent_executor.resume_project(pipeline.project_id)
            speaking_controller.set_mode(pipeline_id, SpeakingMode.PRIORITY_BASED)

            pipeline.add_log("control",
                f"流水线已恢复 — 从阶段: {pipeline.current_stage} 继续, "
                f"进度: {pipeline.progress:.0%}")
            if self._db:
                await self._db.save(pipeline)
            return True

    async def stop_pipeline(self, pipeline_id: str) -> bool:
        async with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if not pipeline:
                return False

            task_count = len(pipeline.task_ids)
            progress = pipeline.progress
            pipeline.stop_requested = True
            self.transition(pipeline, PipelineStatus.FAILED)
            self._cleanup_pipeline_agents(pipeline)
            self._active_pipelines.pop(pipeline.project_id, None)

            # 取消 _run_pipeline asyncio 任务
            task = self._execution_tasks.pop(pipeline_id, None)
            if task and not task.done():
                task.cancel()

            pipeline.add_log("control",
                f"流水线已停止 — 阶段: {pipeline.current_stage}, "
                f"进度曾为: {progress:.0%}, 任务: {task_count}个")
            if self._db:
                await self._db.save(pipeline)
            return True

    async def close_pipeline(self, pipeline_id: str) -> bool:
        """关闭流水线：取消执行、保存状态为 PAUSED（可恢复），释放 agent。"""
        async with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if not pipeline:
                return False

            # 1. 通过 agent_executor 暂停所有运行中的任务
            try:
                await agent_executor.pause_project(pipeline.project_id)
            except Exception as e:
                pipeline.add_log("control", f"暂停任务执行失败: {e}", "warning")

            # 2. 取消 _run_pipeline asyncio 任务
            task = self._execution_tasks.pop(pipeline_id, None)
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass  # 取消操作的预期异常
                except Exception:
                    logger.warning("取消 pipeline 任务时出错", exc_info=True)

            # 3. 保存完整状态
            pipeline.stop_requested = False
            if pipeline.status != PipelineStatus.PAUSED:
                self.transition(pipeline, PipelineStatus.PAUSED)
            self._active_pipelines.pop(pipeline.project_id, None)

            # 4. 释放 agent
            self._cleanup_pipeline_agents(pipeline)

            pipeline.add_log("control",
                f"流水线已关闭保存 — 阶段: {pipeline.current_stage}, "
                f"进度: {pipeline.progress:.0%}, 任务: {len(pipeline.task_ids)}个, 可恢复")

            # 5. 同步更新 workspace project.json
            try:
                from app.services.project.workspace_manager import workspace_manager
                workspace_manager.update_status(pipeline.project_id, "paused")
            except Exception:
                logger.warning("同步工作区暂停状态失败", exc_info=True)

            if self._db:
                await self._db.save(pipeline)
            return True

    async def resume_from_close(self, pipeline_id: str) -> bool:
        """从关闭状态恢复流水线：重新指派 agent，启动新的 _run_pipeline 任务。"""
        async with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if not pipeline or pipeline.status != PipelineStatus.PAUSED:
                return False

            # 1. 重新指派 agent
            for agent_id in pipeline.agents:
                agent = agent_service.get_agent(agent_id)
                if agent:
                    current_project = agent_service.get_agent_project(agent_id)
                    if current_project and current_project != pipeline.project_id:
                        pipeline.add_log("control", f"Agent {agent_id} 已在项目 {current_project} 中，跳过指派", "warning")
                        continue
                    agent_service.assign_agent_to_project(agent_id, pipeline.project_id)

            # 2. 重置标志
            pipeline.stop_requested = False
            self.transition(pipeline, PipelineStatus.RUNNING)
            self._active_pipelines[pipeline.project_id] = pipeline_id

            pipeline.add_log("control", "流水线已从保存状态恢复")

            # 3. 同步更新 workspace project.json
            try:
                from app.services.project.workspace_manager import workspace_manager
                workspace_manager.update_status(pipeline.project_id, "running")
            except Exception:
                logger.warning("同步工作区运行状态失败", exc_info=True)

            if self._db:
                await self._db.save(pipeline)

            # 4. 启动新的 _run_pipeline（上下文注入跳过已完成阶段）
            task = asyncio.create_task(self._run_pipeline(pipeline_id))
            self._execution_tasks[pipeline_id] = task
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
            "current_stage": pipeline.current_stage,
            "progress": pipeline.progress,
            "agents": pipeline.agents,
            "task_count": len(pipeline.task_ids),
            "created_at": pipeline.created_at.isoformat(),
            "started_at": pipeline.started_at.isoformat() if pipeline.started_at else None,
            "completed_at": pipeline.completed_at.isoformat() if pipeline.completed_at else None,
            "logs": pipeline.logs[-50:],
            "context": pipeline.context,
            "team_config": getattr(pipeline, 'team_config', {}),
            "agent_roles": getattr(pipeline, 'agent_roles', {}),
            "stages": getattr(pipeline, 'stages', []),
            "can_resume": pipeline.status in (PipelineStatus.PAUSED, PipelineStatus.COMPLETED, PipelineStatus.FAILED),
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
