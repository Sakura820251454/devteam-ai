import asyncio
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Callable, Any
from enum import Enum

from app.models.agent import Agent
from app.models.task import TaskStatus, Priority
from app.services.collaboration.project_service import project_service, ProjectPhase
from app.services.collaboration.task_board import task_board
from app.services.agent.agent_service import agent_service
from app.services.collaboration.message_bus import message_bus, Message, MessageType
from app.services.collaboration.speaking_controller import speaking_controller, SpeakingMode
from app.services.agent.agent_executor import agent_executor, ExecutionStatus


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
        self._active_pipeline: Optional[str] = None
        self._execution_tasks: Dict[str, asyncio.Task] = {}
        self._human_intervention_queue: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._human_paused: bool = False
        self._stop_requested: bool = False

    async def create_pipeline(
        self,
        project_id: str,
        name: str,
        agent_ids: List[str]
    ) -> Pipeline:
        async with self._lock:
            pipeline = Pipeline()
            pipeline.project_id = project_id
            pipeline.name = name
            pipeline.agents = agent_ids

            self._pipelines[pipeline.id] = pipeline
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
            self._active_pipeline = pipeline_id

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

            if self._stop_requested:
                pipeline.status = PipelineStatus.FAILED
                return

            await self._stage_task_breakdown(pipeline, project)

            if self._stop_requested:
                pipeline.status = PipelineStatus.FAILED
                return

            await self._stage_task_execution(pipeline)

            if self._stop_requested:
                pipeline.status = PipelineStatus.FAILED
                return

            await self._stage_review(pipeline)

            pipeline.status = PipelineStatus.COMPLETED
            pipeline.completed_at = datetime.now()
            pipeline.current_stage = PipelineStage.COMPLETED

            project_service.update_project(pipeline.project_id, status="completed")

        except Exception as e:
            pipeline.status = PipelineStatus.FAILED
            pipeline.add_log("error", f"Pipeline failed: {str(e)}", "error")

    async def _stage_requirement_analysis(self, pipeline: Pipeline) -> None:
        pipeline.current_stage = PipelineStage.REQUIREMENT_ANALYSIS
        pipeline.add_log("requirement_analysis", "Starting requirement analysis...")

        project = project_service.get_project(pipeline.project_id)
        if not project:
            return

        msg = Message(
            sender_id="system",
            sender_name="Pipeline",
            channel=f"project:{pipeline.project_id}",
            content=f"开始分析需求: {project.requirements[:100]}...",
            message_type=MessageType.SYSTEM
        )
        await message_bus.broadcast(msg)

        speaking_controller.set_mode(pipeline.id, SpeakingMode.PRIORITY_BASED)
        speaking_controller.set_token_budget(pipeline.id, 100000)

        pipeline.add_log("requirement_analysis", "Requirement analysis completed")
        pipeline.progress = 0.2

    async def _stage_task_breakdown(self, pipeline: Pipeline, project) -> None:
        pipeline.current_stage = PipelineStage.TASK_BREAKDOWN
        pipeline.add_log("task_breakdown", "Starting task breakdown...")

        prompt = project_service.get_task_breakdown_prompt(pipeline.project_id)
        if not prompt:
            prompt = f"根据以下需求拆解任务：\n{project.requirements}"

        pipeline.add_log("task_breakdown", f"Task breakdown prompt prepared")

        msg = Message(
            sender_id="system",
            sender_name="Pipeline",
            channel=f"project:{pipeline.project_id}",
            content="任务拆解完成，已生成开发任务列表",
            message_type=MessageType.SYSTEM
        )
        await message_bus.broadcast(msg)

        pipeline.progress = 0.4

    async def _stage_task_execution(self, pipeline: Pipeline) -> None:
        pipeline.current_stage = PipelineStage.TASK_EXECUTION
        pipeline.add_log("task_execution", "Starting task execution...")

        tasks = task_board.list_tasks()
        pipeline.task_ids = [t.id for t in tasks]

        for task_id in pipeline.task_ids:
            if self._human_paused or self._stop_requested:
                break

            await agent_executor.start_execution(task_id)
            pipeline.add_log("task_execution", f"Started task: {task_id}")

        while True:
            if self._human_paused or self._stop_requested:
                break

            running = agent_executor.get_running_tasks()
            if not running:
                break

            await asyncio.sleep(1)

        pipeline.progress = 0.8
        pipeline.add_log("task_execution", "Task execution completed")

    async def _stage_review(self, pipeline: Pipeline) -> None:
        pipeline.current_stage = PipelineStage.REVIEW
        pipeline.add_log("review", "Starting review stage...")

        msg = Message(
            sender_id="system",
            sender_name="Pipeline",
            channel=f"project:{pipeline.project_id}",
            content="所有任务执行完成，进入审核阶段",
            message_type=MessageType.SYSTEM
        )
        await message_bus.broadcast(msg)

        pipeline.progress = 1.0
        pipeline.add_log("review", "Review completed")

    async def pause_pipeline(self, pipeline_id: str) -> bool:
        async with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if not pipeline or pipeline.status != PipelineStatus.RUNNING:
                return False

            pipeline.status = PipelineStatus.PAUSED
            self._human_paused = True
            await agent_executor.pause_all()
            speaking_controller.set_mode(pipeline_id, SpeakingMode.FREE_STYLE)

            pipeline.add_log("control", "Pipeline paused by human intervention")
            return True

    async def resume_pipeline(self, pipeline_id: str) -> bool:
        async with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if not pipeline or pipeline.status != PipelineStatus.PAUSED:
                return False

            pipeline.status = PipelineStatus.RUNNING
            self._human_paused = False
            await agent_executor.resume_all()
            speaking_controller.set_mode(pipeline_id, SpeakingMode.PRIORITY_BASED)

            pipeline.add_log("control", "Pipeline resumed")
            return True

    async def stop_pipeline(self, pipeline_id: str) -> bool:
        async with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if not pipeline:
                return False

            self._stop_requested = True
            pipeline.status = PipelineStatus.FAILED
            self._active_pipeline = None

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
            "logs": pipeline.logs[-20:]
        }

    def list_pipelines(self) -> List[Dict[str, Any]]:
        return [self.get_pipeline(pid) for pid in self._pipelines.keys()]

    def get_active_pipeline(self) -> Optional[Dict[str, Any]]:
        if self._active_pipeline:
            return self.get_pipeline(self._active_pipeline)
        return None

    def get_intervention_queue(self) -> List[Dict[str, Any]]:
        return self._human_intervention_queue.copy()


pipeline_orchestrator = PipelineOrchestrator()
