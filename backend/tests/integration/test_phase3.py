import pytest
import asyncio
from app.services.collaboration.project_service import project_service, ProjectPhase, ProjectStatus
from app.services.agent.agent_executor import agent_executor, ExecutionStatus
from app.services.collaboration.pipeline_orchestrator import pipeline_orchestrator, PipelineStage
from app.models.task import TaskStatus


class TestProjectService:
    def test_create_project(self):
        project = project_service.create_project(
            name="Test Project",
            description="A test project",
            requirements="Build a web app",
            created_by="user"
        )

        assert project.name == "Test Project"
        assert project.status == ProjectStatus.PLANNING
        assert project.current_phase == ProjectPhase.REQUIREMENT

    def test_get_project(self):
        project = project_service.create_project(name="Test")
        retrieved = project_service.get_project(project.id)
        assert retrieved is not None
        assert retrieved.id == project.id

    def test_update_project(self):
        project = project_service.create_project(name="Original")
        updated = project_service.update_project(
            project_id=project.id,
            name="Updated",
            status=ProjectStatus.IN_PROGRESS
        )
        assert updated.name == "Updated"
        assert updated.status == ProjectStatus.IN_PROGRESS

    def test_advance_phase(self):
        project = project_service.create_project(name="Test")
        assert project.current_phase == ProjectPhase.REQUIREMENT

        project_service.advance_phase(project.id)
        updated = project_service.get_project(project.id)
        assert updated.current_phase == ProjectPhase.DESIGN

    def test_list_projects(self):
        project_service.create_project(name="Project 1")
        project_service.create_project(name="Project 2")

        projects = project_service.list_projects()
        assert len(projects) >= 2

    def test_delete_project(self):
        project = project_service.create_project(name="To Delete")
        success = project_service.delete_project(project.id)
        assert success
        assert project_service.get_project(project.id) is None


class TestAgentExecutor:
    def setup_method(self):
        from app.services.collaboration.task_board import task_board
        from app.models.task import Priority

        self.task_board = task_board
        self.task = task_board.create_task(
            title="Test Task",
            priority=Priority.MEDIUM
        )

    @pytest.mark.asyncio
    async def test_assign_task(self):
        async def mock_execute(task):
            return {"success": True, "summary": "Done"}

        success = await agent_executor.assign_task(
            task_id=self.task.id,
            agent_id="test-agent",
            agent_execute_fn=mock_execute
        )
        assert success

        current = agent_executor.get_agent_current_task("test-agent")
        assert current == self.task.id

    @pytest.mark.asyncio
    async def test_start_execution(self):
        async def mock_execute(task):
            return {"success": True}

        await agent_executor.assign_task(
            task_id=self.task.id,
            agent_id="test-agent",
            agent_execute_fn=mock_execute
        )

        success = await agent_executor.start_execution(self.task.id)
        assert success

        status = agent_executor.get_execution_status(self.task.id)
        assert status["status"] in ["running", "completed"]

    @pytest.mark.asyncio
    async def test_pause_and_resume(self):
        async def mock_execute(task):
            return {"success": True}

        await agent_executor.assign_task(
            task_id=self.task.id,
            agent_id="test-agent",
            agent_execute_fn=mock_execute
        )

        self.task_board.change_status(self.task.id, TaskStatus.TODO)
        self.task_board.change_status(self.task.id, TaskStatus.IN_PROGRESS)

        execution = agent_executor._running_tasks.get(self.task.id)
        if execution:
            execution["status"] = "running"

        await agent_executor.pause_execution(self.task.id)
        status = agent_executor.get_execution_status(self.task.id)
        assert status["status"] == ExecutionStatus.PAUSED.value

    @pytest.mark.asyncio
    async def test_cancel_execution(self):
        async def mock_execute(task):
            return {"success": True}

        await agent_executor.assign_task(
            task_id=self.task.id,
            agent_id="test-agent",
            agent_execute_fn=mock_execute
        )

        success = await agent_executor.cancel_execution(self.task.id)
        assert success

        current = agent_executor.get_agent_current_task("test-agent")
        assert current is None


class TestPipelineOrchestrator:
    @pytest.mark.asyncio
    async def test_create_pipeline(self):
        project = project_service.create_project(
            name="Pipeline Test",
            requirements="Test"
        )

        pipeline = await pipeline_orchestrator.create_pipeline(
            project_id=project.id,
            name="Test Pipeline",
            agent_ids=["agent1", "agent2"]
        )

        assert pipeline.name == "Test Pipeline"
        assert pipeline.project_id == project.id

    @pytest.mark.asyncio
    async def test_get_pipeline(self):
        project = project_service.create_project(name="Test")
        pipeline = await pipeline_orchestrator.create_pipeline(
            project_id=project.id,
            name="Test",
            agent_ids=[]
        )

        retrieved = pipeline_orchestrator.get_pipeline(pipeline.id)
        assert retrieved is not None
        assert retrieved["name"] == "Test"

    @pytest.mark.asyncio
    async def test_list_pipelines(self):
        project = project_service.create_project(name="Test List")
        await pipeline_orchestrator.create_pipeline(
            project_id=project.id,
            name="Pipeline 1",
            agent_ids=[]
        )

        pipelines = pipeline_orchestrator.list_pipelines()
        assert len(pipelines) >= 1

    @pytest.mark.asyncio
    async def test_intervention(self):
        project = project_service.create_project(name="Test")
        pipeline = await pipeline_orchestrator.create_pipeline(
            project_id=project.id,
            name="Test",
            agent_ids=[]
        )

        await pipeline_orchestrator.intervene(
            pipeline_id=pipeline.id,
            message="Please review the code",
            agent_id="agent1"
        )

        queue = pipeline_orchestrator.get_intervention_queue()
        assert len(queue) >= 1
        assert "review" in queue[-1]["message"].lower()

    def test_get_active_pipeline_none(self):
        active = pipeline_orchestrator.get_active_pipeline()
        assert active is None or active.get("status") != "running"
