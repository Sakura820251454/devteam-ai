"""
Phase 3 集成测试 - 干预系统
使用 Mock LLM 数据测试 Pipeline 编排、项目管理和 Agent 执行

运行方式：
    pytest tests/test_phase3_integration.py -v
    pytest tests/test_phase3_integration.py::TestPipelineOrchestrator -v
    pytest tests/test_phase3_integration.py::TestProjectService -v
    pytest tests/test_phase3_integration.py::TestHumanIntervention -v
"""

import pytest
import asyncio
from datetime import datetime
from typing import List

import sys
sys.path.insert(0, 'd:/AIproject/devteam-ai/backend')

from app.services.collaboration.message_bus import message_bus, Message, MessageType
from app.services.collaboration.speaking_controller import speaking_controller, SpeakingMode
from app.services.collaboration.task_board import task_board, TaskStatus, Priority
from app.services.collaboration.project_service import project_service, ProjectStatus, ProjectPhase
from app.services.collaboration.pipeline_orchestrator import pipeline_orchestrator, PipelineStatus, PipelineStage
from app.services.agent.agent_executor import agent_executor, ExecutionStatus

from tests.mock.mock_llm_data import MockLLMData, get_mock_response, SCENARIOS


class TestProjectService:
    """项目服务测试"""

    def setup_method(self):
        """每个测试前清空"""
        project_service._projects.clear()
        task_board.clear_all()

    def test_create_project(self):
        """测试创建项目"""
        project = project_service.create_project(
            name="用户管理系统",
            description="企业内部用户权限管理系统",
            requirements="1. 用户注册登录\n2. 角色权限管理\n3. 审计日志",
            created_by="user",
            team_config={"pm": "pm_agent", "backend": "backend_agent"}
        )

        assert project is not None
        assert project.name == "用户管理系统"
        assert project.status == ProjectStatus.PLANNING
        assert project.current_phase == ProjectPhase.REQUIREMENT
        assert "pm" in project.team_config

    def test_update_project_status(self):
        """测试更新项目状态"""
        project = project_service.create_project(name="测试项目")

        # 更新状态
        updated = project_service.update_project(
            project.id,
            status=ProjectStatus.IN_PROGRESS
        )

        assert updated.status == ProjectStatus.IN_PROGRESS

    def test_advance_phase(self):
        """测试推进项目阶段"""
        project = project_service.create_project(name="测试项目")

        # 初始阶段
        assert project.current_phase == ProjectPhase.REQUIREMENT

        # 推进到设计阶段
        project_service.advance_phase(project.id)
        assert project.current_phase == ProjectPhase.DESIGN

        # 推进到开发阶段
        project_service.advance_phase(project.id)
        assert project.current_phase == ProjectPhase.DEVELOPMENT

    def test_list_projects(self):
        """测试项目列表"""
        project_service.create_project(name="项目1")
        project_service.create_project(name="项目2")
        project_service.create_project(name="项目3")

        all_projects = project_service.list_projects()
        assert len(all_projects) >= 3


class TestPipelineOrchestrator:
    """Pipeline 编排器测试"""

    def setup_method(self):
        """每个测试前清空"""
        pipeline_orchestrator._pipelines.clear()
        pipeline_orchestrator._active_pipeline = None
        pipeline_orchestrator._human_intervention_queue.clear()
        task_board.clear_all()

    @pytest.mark.asyncio
    async def test_create_pipeline(self):
        """测试创建 Pipeline"""
        # 创建项目
        project = project_service.create_project(name="测试项目")

        # 创建 Pipeline
        pipeline = await pipeline_orchestrator.create_pipeline(
            project_id=project.id,
            name="用户管理系统开发流程",
            agent_ids=["pm_agent", "backend_agent", "frontend_agent"]
        )

        assert pipeline is not None
        assert pipeline.project_id == project.id
        assert pipeline.status == PipelineStatus.IDLE
        assert len(pipeline.agents) == 3

    @pytest.mark.asyncio
    async def test_pipeline_lifecycle(self):
        """测试 Pipeline 生命周期"""
        project = project_service.create_project(name="测试项目")

        # 创建并启动
        pipeline = await pipeline_orchestrator.create_pipeline(
            project_id=project.id,
            name="开发流程",
            agent_ids=["backend_agent"]
        )

        result = await pipeline_orchestrator.start_pipeline(pipeline.id)
        assert result is True

        pipeline_info = pipeline_orchestrator.get_pipeline(pipeline.id)
        assert pipeline_info["status"] == PipelineStatus.RUNNING.value

    @pytest.mark.asyncio
    async def test_pipeline_pause_resume(self):
        """测试 Pipeline 暂停和恢复"""
        project = project_service.create_project(name="测试项目")

        pipeline = await pipeline_orchestrator.create_pipeline(
            project_id=project.id,
            name="开发流程",
            agent_ids=["backend_agent"]
        )

        await pipeline_orchestrator.start_pipeline(pipeline.id)

        # 暂停
        result = await pipeline_orchestrator.pause_pipeline(pipeline.id)
        assert result is True

        pipeline_info = pipeline_orchestrator.get_pipeline(pipeline.id)
        assert pipeline_info["status"] == PipelineStatus.PAUSED.value

        # 恢复
        result = await pipeline_orchestrator.resume_pipeline(pipeline.id)
        assert result is True

        pipeline_info = pipeline_orchestrator.get_pipeline(pipeline.id)
        assert pipeline_info["status"] == PipelineStatus.RUNNING.value

    @pytest.mark.asyncio
    async def test_pipeline_stop(self):
        """测试停止 Pipeline"""
        project = project_service.create_project(name="测试项目")

        pipeline = await pipeline_orchestrator.create_pipeline(
            project_id=project.id,
            name="开发流程",
            agent_ids=["backend_agent"]
        )

        await pipeline_orchestrator.start_pipeline(pipeline.id)

        # 停止
        result = await pipeline_orchestrator.stop_pipeline(pipeline.id)
        assert result is True

        pipeline_info = pipeline_orchestrator.get_pipeline(pipeline.id)
        assert pipeline_info["status"] == PipelineStatus.FAILED.value


class TestAgentExecutor:
    """Agent 执行器测试"""

    def setup_method(self):
        """每个测试前清空"""
        agent_executor._running_tasks.clear()
        agent_executor._agent_tasks.clear()
        task_board.clear_all()

    @pytest.mark.asyncio
    async def test_assign_task(self):
        """测试任务分配"""
        # 创建任务
        task = task_board.create_task(
            title="实现用户API",
            assigned_agents=["backend"],
            created_by="pm"
        )

        # 定义执行函数
        async def mock_execute(t):
            await asyncio.sleep(0.1)
            return {"success": True, "summary": "完成"}

        # 分配任务
        result = await agent_executor.assign_task(
            task_id=task.id,
            agent_id="backend",
            agent_execute_fn=mock_execute
        )

        assert result is True

        # 验证
        current_task = agent_executor.get_agent_current_task("backend")
        assert current_task == task.id

    @pytest.mark.asyncio
    async def test_task_execution(self):
        """测试任务执行"""
        task = task_board.create_task(
            title="实现登录API",
            created_by="pm"
        )

        async def mock_execute(t):
            return {"success": True, "summary": "登录API实现完成"}

        result = await agent_executor.assign_task(
            task_id=task.id,
            agent_id="backend",
            agent_execute_fn=mock_execute
        )
        assert result is True

        result = await agent_executor.start_execution(task.id)
        assert result is True

        await asyncio.sleep(0.2)

        status = agent_executor.get_execution_status(task.id)
        assert status is not None

    @pytest.mark.asyncio
    async def test_pause_resume_execution(self):
        """测试暂停和恢复执行"""
        task = task_board.create_task(title="测试任务", created_by="pm")

        async def mock_execute(t):
            return {"success": True}

        result = await agent_executor.assign_task(
            task_id=task.id,
            agent_id="test_executor",
            agent_execute_fn=mock_execute
        )
        assert result is True

        status = agent_executor.get_execution_status(task.id)
        assert status is not None


class TestHumanIntervention:
    """人类干预测试"""

    def setup_method(self):
        """每个测试前清空"""
        pipeline_orchestrator._pipelines.clear()
        pipeline_orchestrator._human_intervention_queue.clear()
        message_bus.clear_history()

    @pytest.mark.asyncio
    async def test_human_broadcast(self):
        """测试人类广播消息"""
        project = project_service.create_project(name="测试项目")

        pipeline = await pipeline_orchestrator.create_pipeline(
            project_id=project.id,
            name="开发流程",
            agent_ids=["backend_agent"]
        )

        # 人类干预 - 广播
        await pipeline_orchestrator.intervene(
            pipeline_id=pipeline.id,
            message="请优先处理登录模块",
            agent_id=None  # 广播
        )

        # 验证干预队列
        queue = pipeline_orchestrator.get_intervention_queue()
        assert len(queue) == 1
        assert queue[0]["message"] == "请优先处理登录模块"

    @pytest.mark.asyncio
    async def test_human_private_message(self):
        """测试人类私信"""
        project = project_service.create_project(name="测试项目")

        pipeline = await pipeline_orchestrator.create_pipeline(
            project_id=project.id,
            name="开发流程",
            agent_ids=["backend_agent"]
        )

        received = []
        def on_message(msg):
            received.append(msg)

        message_bus.subscribe("backend_agent", ["private"], on_message)

        # 人类私信
        await pipeline_orchestrator.intervene(
            pipeline_id=pipeline.id,
            message="这个模块需要特别关注",
            agent_id="backend_agent"
        )

        # 等待消息传递
        await asyncio.sleep(0.1)

        assert len(received) == 1
        assert "特别关注" in received[0].content

    @pytest.mark.asyncio
    async def test_pipeline_pause_intervention(self):
        """测试暂停干预"""
        project = project_service.create_project(name="测试项目")

        pipeline = await pipeline_orchestrator.create_pipeline(
            project_id=project.id,
            name="开发流程",
            agent_ids=["backend_agent"]
        )

        await pipeline_orchestrator.start_pipeline(pipeline.id)

        # 暂停
        await pipeline_orchestrator.pause_pipeline(pipeline.id)

        # 验证状态
        pipeline_info = pipeline_orchestrator.get_pipeline(pipeline.id)
        assert pipeline_info["status"] == PipelineStatus.PAUSED.value


class TestPhase3MockScenario:
    """Phase 3 Mock 场景测试"""

    def setup_method(self):
        """每个测试前清空"""
        task_board.clear_all()
        message_bus.clear_history()
        project_service._projects.clear()
        pipeline_orchestrator._pipelines.clear()
        pipeline_orchestrator._human_intervention_queue.clear()

    @pytest.mark.asyncio
    async def test_end_to_end_project_flow(self):
        """端到端项目流程测试"""
        print("\n=== 端到端项目流程测试 ===")

        # 阶段 1: 创建项目和团队
        print("\n📋 阶段1: 创建项目")
        project = project_service.create_project(
            name="用户管理系统",
            description="企业内部用户权限管理系统",
            requirements="""
1. 用户注册和登录
2. 角色权限管理
3. 用户信息CRUD
4. 操作审计日志
            """,
            created_by="user",
            team_config={
                "pm": "pm_agent",
                "architect": "architect_agent",
                "backend": "backend_agent",
                "frontend": "frontend_agent",
                "tester": "tester_agent"
            }
        )
        print(f"✅ 项目创建: {project.name}")
        print(f"   团队成员: {len(project.team_config)} 人")

        # 阶段 2: 从讨论生成任务
        print("\n📋 阶段2: 任务拆解")
        breakdown_data = MockLLMData.TASK_BREAKDOWN
        task_count = 0
        for phase in breakdown_data["phases"]:
            for task_data in phase["tasks"]:
                task = task_board.create_task(
                    title=task_data["title"],
                    description=task_data["description"],
                    priority=Priority(task_data["priority"]),
                    created_by="pm_agent"
                )
                task_count += 1
        print(f"✅ 任务创建: {task_count} 个任务")

        # 阶段 3: 创建 Pipeline
        print("\n📋 阶段3: 启动 Pipeline")
        pipeline = await pipeline_orchestrator.create_pipeline(
            project_id=project.id,
            name="用户管理系统开发",
            agent_ids=list(project.team_config.values())
        )

        result = await pipeline_orchestrator.start_pipeline(pipeline.id)
        print(f"✅ Pipeline 启动: {'成功' if result else '失败'}")

        # 阶段 4: 模拟人类干预
        print("\n📋 阶段4: 人类干预")

        # 广播消息
        await pipeline_orchestrator.intervene(
            pipeline_id=pipeline.id,
            message="请优先处理用户注册和登录功能",
            agent_id=None
        )
        print("✅ 广播消息已发送")

        # 私信
        await pipeline_orchestrator.intervene(
            pipeline_id=pipeline.id,
            message="注意数据库索引优化",
            agent_id="backend_agent"
        )
        print("✅ 私信已发送")

        # 暂停
        await pipeline_orchestrator.pause_pipeline(pipeline.id)
        print("✅ Pipeline 已暂停")

        # 恢复
        await pipeline_orchestrator.resume_pipeline(pipeline.id)
        print("✅ Pipeline 已恢复")

        # 阶段 5: 执行任务
        print("\n📋 阶段5: 任务执行")

        async def mock_execute(task):
            await asyncio.sleep(0.1)
            return {"success": True, "summary": f"完成: {task.title}"}

        tasks = task_board.list_tasks(limit=3)
        for task in tasks:
            await agent_executor.assign_task(
                task_id=task.id,
                agent_id="backend_agent",
                agent_execute_fn=mock_execute
            )
            await agent_executor.start_execution(task.id)

        print(f"✅ 启动执行: {len(tasks)} 个任务")

        # 等待执行
        await asyncio.sleep(0.3)

        # 阶段 6: 验证结果
        print("\n📋 阶段6: 验证结果")

        # 验证任务状态
        completed_tasks = task_board.list_tasks(status=TaskStatus.REVIEW)
        print(f"✅ 进入审核任务: {len(completed_tasks)} 个")

        # 验证干预记录
        interventions = pipeline_orchestrator.get_intervention_queue()
        print(f"✅ 干预记录: {len(interventions)} 条")

        # 验证 Pipeline 状态
        pipeline_info = pipeline_orchestrator.get_pipeline(pipeline.id)
        print(f"✅ Pipeline 状态: {pipeline_info['status']}")

        print("\n" + "="*50)
        print("🎉 端到端流程测试完成!")
        print("="*50)

    @pytest.mark.asyncio
    async def test_mock_llm_discussion_flow(self):
        """Mock LLM 讨论流程测试"""
        print("\n=== Mock LLM 讨论流程测试 ===")

        # 模拟多轮讨论
        scenario = SCENARIOS["user_management"]

        # 设置发言控制
        speaking_controller.set_mode("demo_session", SpeakingMode.PRIORITY_BASED)
        speaking_controller.set_token_budget("demo_session", 5000)

        # 收集消息
        discussion_log = []

        def on_message(msg):
            discussion_log.append({
                "sender": msg.sender_name,
                "content": msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
            })

        # 订阅消息
        message_bus.subscribe("demo_session", ["public"], on_message)

        # 模拟讨论流程
        flow = MockLLMData.get_discussion_flow("requirement")
        for step in flow:
            # 获取 Mock 响应
            mock_response = get_mock_response(
                prompt=step["content"],
                agent=step["agent"],
                response_type="discussion"
            )

            # 发送消息
            msg = Message(
                sender_id=step["agent"],
                sender_name=MockLLMData.AGENT_PROFILES[step["agent"]]["name"],
                content=mock_response.content,
                message_type=MessageType.TEXT
            )
            await message_bus.broadcast(msg)

            print(f"[{msg.sender_name}] {msg.content[:40]}...")

        # 验证讨论
        assert len(discussion_log) == len(flow)
        print(f"\n✅ 讨论完成: {len(discussion_log)} 条消息")

        # 生成摘要
        summary = MockLLMData.SUMMARY_TEMPLATE.format(
            topic="用户管理系统需求讨论",
            participants=", ".join(set(d["sender"] for d in discussion_log)),
            content="\n".join(f"- {d['content']}" for d in discussion_log[:3]),
            decisions="- 采用前后端分离架构\n- 使用 FastAPI + React",
            open_issues="- 缓存策略待定\n- 部署方案待定",
            next_steps="- 完成数据库设计\n- 开始 API 开发",
            meeting_time=datetime.now().strftime("%Y-%m-%d %H:%M")
        )

        print("\n📋 讨论摘要预览:")
        print(summary[:200] + "...")


class TestMockLLMResponses:
    """Mock LLM 响应测试"""

    def test_get_agent_response(self):
        """测试 Agent 响应生成"""
        for agent in ["pm", "architect", "backend", "frontend", "tester"]:
            response = get_mock_response(
                prompt="测试问题",
                agent=agent,
                response_type="discussion"
            )
            assert response.agent == agent
            assert response.tokens_used > 0
            print(f"[{agent}] {response.content[:40]}...")

    def test_analysis_response(self):
        """测试分析响应"""
        response = get_mock_response(
            prompt="性能优化建议",
            agent="architect",
            response_type="analysis"
        )
        assert "分析报告" in response.content or "分析" in response.content

    def test_code_response(self):
        """测试代码响应"""
        response = get_mock_response(
            prompt="user register",
            agent="backend",
            response_type="code"
        )
        assert response.response_type == "code"

    def test_scenarios(self):
        """测试预定义场景"""
        for key, scenario in SCENARIOS.items():
            assert "name" in scenario
            assert "requirements" in scenario
            print(f"✅ 场景 '{key}': {scenario['name']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
