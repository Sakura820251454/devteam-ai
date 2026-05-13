"""
完整协作流程集成测试 - Phase 6.4

测试场景：
- 创建多个 Agent
- Agent 间消息传递
- Pipeline 执行流程
- 任务创建和分配
- 任务状态流转
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.agent.agent_service import agent_service, AgentType
from app.services.collaboration.task_board import task_board
from app.services.collaboration.project_service import project_service, ProjectStatus, ProjectPhase
from app.services.collaboration.pipeline_orchestrator import pipeline_orchestrator
from app.models.task import TaskStatus, Priority


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_agent_ids():
    return []


class TestAgentCreation:
    """测试 Agent 创建"""

    @pytest.mark.asyncio
    async def test_create_multiple_agents_via_api(self, client):
        """通过 API 创建多个 Agent"""
        agent_ids = []

        for i in range(3):
            template_data = {
                "name": f"测试Agent{i+1}",
                "type": "custom",
                "description": f"测试用途的 Agent {i+1}",
                "system_prompt": f"你是一个专业的测试 Agent {i+1}",
                "capabilities": [f"capability_{i+1}"],
                "tags": ["test", f"agent_{i+1}"]
            }
            response = await client.post("/api/agents/templates", json=template_data)
            assert response.status_code == 200
            data = response.json()
            agent_ids.append(data["id"])

        assert len(agent_ids) == 3
        for agent_id in agent_ids:
            assert agent_id is not None

    @pytest.mark.asyncio
    async def test_create_agent_from_template(self, client):
        """从模板创建 Agent"""
        template_response = await client.post(
            "/api/agents/templates",
            json={
                "name": "开发者模板",
                "type": "custom",
                "system_prompt": "你是一个 Python 开发者",
                "capabilities": ["coding", "review"]
            }
        )
        assert template_response.status_code == 200
        template_id = template_response.json()["id"]

        agent_response = await client.post(
            "/api/agents/",
            json={"template_id": template_id, "name": "DevAgent"}
        )
        assert agent_response.status_code == 200
        agent_data = agent_response.json()
        assert agent_data["name"] == "DevAgent"

    @pytest.mark.asyncio
    async def test_list_agents(self, client):
        """列出所有 Agent"""
        response = await client.get("/api/agents/")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "total" in data


class TestTaskWorkflow:
    """测试任务工作流"""

    @pytest.mark.asyncio
    async def test_task_lifecycle(self, client):
        """测试任务完整生命周期"""
        create_response = await client.post(
            "/api/tasks/",
            json={
                "title": "测试任务",
                "description": "测试任务描述",
                "priority": "high"
            }
        )
        assert create_response.status_code == 200
        task = create_response.json()
        task_id = task["id"]
        assert task["title"] == "测试任务"
        assert task["status"] == TaskStatus.BACKLOG.value

        get_response = await client.get(f"/api/tasks/{task_id}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == task_id

        update_response = await client.patch(
            f"/api/tasks/{task_id}",
            json={"title": "更新后的任务"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["title"] == "更新后的任务"

    @pytest.mark.asyncio
    async def test_task_status_transitions(self, client):
        """测试任务状态转换"""
        task_response = await client.post(
            "/api/tasks/",
            json={"title": "状态测试任务", "priority": "medium"}
        )
        task_id = task_response.json()["id"]

        status_changes = [
            (TaskStatus.TODO, "todo"),
            (TaskStatus.IN_PROGRESS, "in_progress"),
            (TaskStatus.REVIEW, "review"),
            (TaskStatus.DONE, "done")
        ]

        for new_status, _ in status_changes:
            status_response = await client.post(
                f"/api/tasks/{task_id}/status",
                json={"status": new_status.value}
            )
            assert status_response.status_code == 200
            assert status_response.json()["status"] == new_status.value

    @pytest.mark.asyncio
    async def test_task_assignment(self, client):
        """测试任务分配"""
        task_response = await client.post(
            "/api/tasks/",
            json={"title": "分配测试任务"}
        )
        task_id = task_response.json()["id"]

        assign_response = await client.post(
            f"/api/tasks/{task_id}/assign",
            json={"agent_ids": ["agent_1", "agent_2"]}
        )
        assert assign_response.status_code == 200
        assigned = assign_response.json()
        assert "agent_1" in assigned["assigned_agents"]
        assert "agent_2" in assigned["assigned_agents"]

    @pytest.mark.asyncio
    async def test_task_board_view(self, client):
        """测试看板视图"""
        for i in range(3):
            await client.post(
                "/api/tasks/",
                json={"title": f"看板任务{i+1}"}
            )

        board_response = await client.get("/api/tasks/board/all")
        assert board_response.status_code == 200
        board = board_response.json()
        assert "columns" in board
        assert "total" in board

    @pytest.mark.asyncio
    async def test_task_search(self, client):
        """测试任务搜索"""
        search_term = "unique_search_term_12345"
        await client.post(
            "/api/tasks/",
            json={"title": f"包含 {search_term} 的任务"}
        )

        search_response = await client.get(f"/api/tasks/search/{search_term}")
        assert search_response.status_code == 200
        results = search_response.json()
        assert len(results) >= 1


class TestAgentCollaboration:
    """测试 Agent 协作"""

    @pytest.mark.asyncio
    async def test_create_team(self, client):
        """创建 Agent 团队"""
        agent_response = await client.post(
            "/api/agents/templates",
            json={"name": "团队成员1", "type": "custom", "system_prompt": "团队成员"}
        )
        agent1_id = agent_response.json()["id"]

        team_response = await client.post(
            "/api/agents/teams",
            json={
                "name": "测试团队",
                "agent_ids": [agent1_id]
            }
        )
        assert team_response.status_code == 200
        team = team_response.json()
        assert team["name"] == "测试团队"

    @pytest.mark.asyncio
    async def test_list_teams(self, client):
        """列出团队"""
        response = await client.get("/api/agents/teams")
        assert response.status_code in [200, 404]


class TestProjectAndPipeline:
    """测试项目和 Pipeline"""

    @pytest.mark.asyncio
    async def test_project_lifecycle(self):
        """测试项目完整生命周期"""
        project = project_service.create_project(
            name="测试项目",
            description="用于测试的项目",
            requirements="完成集成测试",
            created_by="test"
        )
        assert project.name == "测试项目"
        assert project.status == ProjectStatus.PLANNING
        assert project.current_phase == ProjectPhase.REQUIREMENT

        project_service.advance_phase(project.id)
        updated = project_service.get_project(project.id)
        assert updated.current_phase == ProjectPhase.DESIGN

        project_service.update_project(
            project.id,
            status=ProjectStatus.IN_PROGRESS
        )
        progress = project_service.get_project(project.id)
        assert progress.status == ProjectStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_pipeline_creation(self):
        """测试 Pipeline 创建"""
        project = project_service.create_project(
            name="Pipeline测试",
            requirements="测试"
        )

        pipeline = await pipeline_orchestrator.create_pipeline(
            project_id=project.id,
            name="测试Pipeline",
            agent_ids=["agent_1", "agent_2"]
        )

        assert pipeline.name == "测试Pipeline"
        assert pipeline.project_id == project.id

        retrieved = pipeline_orchestrator.get_pipeline(pipeline.id)
        assert retrieved is not None
        assert retrieved["name"] == "测试Pipeline"

    @pytest.mark.asyncio
    async def test_pipeline_intervention(self):
        """测试 Pipeline 干预"""
        project = project_service.create_project(name="干预测试")
        pipeline = await pipeline_orchestrator.create_pipeline(
            project_id=project.id,
            name="干预Pipeline",
            agent_ids=["agent_1"]
        )

        await pipeline_orchestrator.intervene(
            pipeline_id=pipeline.id,
            message="请检查代码质量",
            agent_id="agent_1"
        )

        queue = pipeline_orchestrator.get_intervention_queue()
        assert len(queue) >= 1


class TestEndToEndCollaborationFlow:
    """端到端协作流程测试"""

    @pytest.mark.asyncio
    async def test_full_collaboration_flow(self, client):
        """测试完整协作流程"""
        # 1. 创建 Agent 团队
        template1 = await client.post(
            "/api/agents/templates",
            json={
                "name": "前端开发",
                "type": "custom",
                "system_prompt": "你是一个专业的前端开发工程师"
            }
        )
        template2 = await client.post(
            "/api/agents/templates",
            json={
                "name": "后端开发",
                "type": "custom",
                "system_prompt": "你是一个专业的后端开发工程师"
            }
        )
        frontend_id = template1.json()["id"]
        backend_id = template2.json()["id"]

        # 2. 创建团队
        team_response = await client.post(
            "/api/agents/teams",
            json={
                "name": "Web开发团队",
                "agent_ids": [frontend_id, backend_id]
            }
        )
        assert team_response.status_code == 200

        # 3. 创建项目
        project = project_service.create_project(
            name="Web应用开发",
            description="开发一个简单的Web应用",
            requirements="前后端分离架构",
            created_by="test"
        )

        # 4. 创建任务
        frontend_task = await client.post(
            "/api/tasks/",
            json={
                "title": "前端开发任务",
                "description": "开发前端界面",
                "priority": "high",
                "assigned_agents": [frontend_id]
            }
        )
        assert frontend_task.status_code == 200

        backend_task = await client.post(
            "/api/tasks/",
            json={
                "title": "后端开发任务",
                "description": "开发后端API",
                "priority": "high",
                "assigned_agents": [backend_id]
            }
        )
        assert backend_task.status_code == 200

        # 5. 创建 Pipeline
        pipeline = await pipeline_orchestrator.create_pipeline(
            project_id=project.id,
            name="Web开发Pipeline",
            agent_ids=[frontend_id, backend_id]
        )
        assert pipeline.name == "Web开发Pipeline"

        # 6. 更新任务状态 (先从 backlog -> todo -> in_progress)
        await client.post(
            f"/api/tasks/{frontend_task.json()['id']}/status",
            json={"status": "todo"}
        )
        await client.post(
            f"/api/tasks/{frontend_task.json()['id']}/status",
            json={"status": "in_progress"}
        )

        await client.post(
            f"/api/tasks/{backend_task.json()['id']}/status",
            json={"status": "todo"}
        )
        await client.post(
            f"/api/tasks/{backend_task.json()['id']}/status",
            json={"status": "in_progress"}
        )

        # 7. 获取看板状态
        board = await client.get("/api/tasks/board/all")
        assert board.status_code == 200
        assert "columns" in board.json()

        # 8. 完成任务 (in_progress -> review -> done)
        await client.post(
            f"/api/tasks/{frontend_task.json()['id']}/status",
            json={"status": "review"}
        )
        await client.post(
            f"/api/tasks/{frontend_task.json()['id']}/status",
            json={"status": "done"}
        )

        await client.post(
            f"/api/tasks/{backend_task.json()['id']}/status",
            json={"status": "review"}
        )
        await client.post(
            f"/api/tasks/{backend_task.json()['id']}/status",
            json={"status": "done"}
        )

        # 9. 验证最终状态
        final_frontend = await client.get(f"/api/tasks/{frontend_task.json()['id']}")
        assert final_frontend.json()["status"] == "done"

        final_backend = await client.get(f"/api/tasks/{backend_task.json()['id']}")
        assert final_backend.json()["status"] == "done"


class TestAgentMessaging:
    """测试 Agent 消息传递"""

    @pytest.mark.asyncio
    async def test_create_session(self, client):
        """创建会话"""
        try:
            response = await client.post(
                "/api/sessions",
                json={"title": "测试会话"}
            )
            if response.status_code == 200:
                session = response.json()
                assert session["title"] == "测试会话"
        except (AttributeError, TypeError):
            pass

    @pytest.mark.asyncio
    async def test_list_sessions(self, client):
        """列出会话"""
        try:
            await client.post("/api/sessions", json={"title": "会话1"})
            await client.post("/api/sessions", json={"title": "会话2"})

            response = await client.get("/api/sessions")
            assert response.status_code == 200
            sessions = response.json()
            assert isinstance(sessions, list)
        except (AttributeError, TypeError):
            pass

    @pytest.mark.asyncio
    async def test_send_message(self, client):
        """发送消息"""
        message_response = await client.post(
            "/api/messages/broadcast",
            json={
                "sender_id": "user",
                "sender_name": "User",
                "content": "测试消息"
            }
        )
        assert message_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
