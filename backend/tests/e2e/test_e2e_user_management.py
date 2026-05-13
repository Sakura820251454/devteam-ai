"""
端到端集成测试 - 用户管理系统完整流程
使用 Mock LLM 数据测试从需求讨论到代码生成的完整流程

运行方式：
    pytest tests/test_e2e_user_management.py -v -s
"""

import pytest
import asyncio
from datetime import datetime

import sys
sys.path.insert(0, 'd:/AIproject/devteam-ai/backend')

from app.services.collaboration.message_bus import message_bus, Message, MessageType
from app.services.collaboration.speaking_controller import speaking_controller, SpeakingMode
from app.services.collaboration.task_board import task_board, TaskStatus, Priority
from app.services.collaboration.project_service import project_service, ProjectStatus, ProjectPhase
from app.services.collaboration.pipeline_orchestrator import pipeline_orchestrator, PipelineStatus, PipelineStage
from app.services.agent.agent_executor import agent_executor, ExecutionStatus

from tests.mock.mock_llm_data import MockLLMData, get_mock_response


class TestUserManagementE2E:
    """用户管理系统端到端测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前清空所有状态"""
        task_board.clear_all()
        message_bus.clear_history()
        project_service._projects.clear()
        pipeline_orchestrator._pipelines.clear()
        pipeline_orchestrator._human_intervention_queue.clear()
        agent_executor._running_tasks.clear()
        agent_executor._agent_tasks.clear()
        speaking_controller.cleanup_session("e2e_session")
        yield

    @pytest.mark.asyncio
    async def test_complete_project_lifecycle(self):
        """完整项目生命周期测试"""
        print("\n" + "="*60)
        print("🚀 用户管理系统 - 完整生命周期测试")
        print("="*60)

        # ========== 阶段 1: 需求讨论 ==========
        print("\n📌 阶段 1: 需求讨论")
        print("-"*40)

        speaking_controller.set_mode("e2e_session", SpeakingMode.PRIORITY_BASED)
        speaking_controller.set_token_budget("e2e_session", 20000)

        discussion_log = []
        def on_message(msg):
            discussion_log.append({
                "sender": msg.sender_name,
                "content": msg.content
            })

        message_bus.subscribe("e2e_session", ["public"], on_message)

        # PM 发起讨论
        pm_intro = Message(
            sender_id="pm",
            sender_name="产品经理小李",
            content="大家好，我们今天来讨论一个新项目：开发一个用户管理系统。",
            message_type=MessageType.TEXT
        )
        await message_bus.broadcast(pm_intro)
        print(f"  [{pm_intro.sender_name}] {pm_intro.content[:50]}...")

        # 架构师询问规模
        arch_question = Message(
            sender_id="architect",
            sender_name="架构师老王",
            content="请先介绍一下预期用户规模和核心功能需求？",
            message_type=MessageType.TEXT
        )
        await message_bus.broadcast(arch_question)

        # PM 回答
        pm_answer = Message(
            sender_id="pm",
            sender_name="产品经理小李",
            content="预计初期1000并发用户，主要功能：用户注册登录、角色权限管理、个人信息管理。",
            message_type=MessageType.TEXT
        )
        await message_bus.broadcast(pm_answer)

        # Backend 发言
        backend_speech = Message(
            sender_id="backend",
            sender_name="后端开发小张",
            content="我建议使用 FastAPI + PostgreSQL，成熟稳定，扩展性好。",
            message_type=MessageType.TEXT
        )
        await message_bus.broadcast(backend_speech)

        print(f"  ✅ 讨论完成，共 {len(discussion_log)} 条消息")

        # ========== 阶段 2: 任务拆解 ==========
        print("\n📌 阶段 2: 任务拆解")
        print("-"*40)

        breakdown_data = MockLLMData.TASK_BREAKDOWN
        created_tasks = {}

        for phase in breakdown_data["phases"]:
            print(f"\n  📂 {phase['phase']}:")
            for task_data in phase["tasks"]:
                task = task_board.create_task(
                    title=task_data["title"],
                    description=task_data["description"],
                    priority=Priority(task_data["priority"]),
                    created_by="pm"
                )
                created_tasks[task.id] = task
                priority_emoji = {"urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
                emoji = priority_emoji.get(task_data["priority"], "⚪")
                print(f"    {emoji} {task.title}")

        print(f"\n  ✅ 共创建 {len(created_tasks)} 个任务")

        # ========== 阶段 3: 创建项目 ==========
        print("\n📌 阶段 3: 创建项目")
        print("-"*40)

        project = project_service.create_project(
            name="用户管理系统",
            description="企业内部用户权限管理系统",
            requirements="1. 用户注册登录\n2. 角色权限管理\n3. 个人信息管理",
            created_by="user",
            team_config={
                "pm": "pm_agent",
                "architect": "architect_agent",
                "backend": "backend_agent",
                "frontend": "frontend_agent"
            }
        )
        print(f"  ✅ 项目: {project.name}")
        print(f"  ✅ 项目ID: {project.id}")
        print(f"  ✅ 团队: {len(project.team_config)} 人")

        # ========== 阶段 4: 启动 Pipeline ==========
        print("\n📌 阶段 4: 启动 Pipeline")
        print("-"*40)

        pipeline = await pipeline_orchestrator.create_pipeline(
            project_id=project.id,
            name="用户管理系统开发流程",
            agent_ids=list(project.team_config.values())
        )
        print(f"  ✅ Pipeline 创建: {pipeline.id}")

        result = await pipeline_orchestrator.start_pipeline(pipeline.id)
        print(f"  ✅ Pipeline 启动: {'成功' if result else '失败'}")

        # ========== 阶段 5: 人类干预 ==========
        print("\n📌 阶段 5: 人类干预")
        print("-"*40)

        # 干预1: 全局广播
        await pipeline_orchestrator.intervene(
            pipeline_id=pipeline.id,
            message="请优先处理用户注册和登录功能，这是核心功能。",
            agent_id=None
        )
        print("  📢 广播: 请优先处理用户注册和登录功能")

        # 干预2: 私信后端
        await pipeline_orchestrator.intervene(
            pipeline_id=pipeline.id,
            message="数据库设计时注意添加索引，提高查询性能。",
            agent_id="backend_agent"
        )
        print("  📩 私信后端: 数据库索引建议")

        # 干预3: 暂停
        await pipeline_orchestrator.pause_pipeline(pipeline.id)
        print("  ⏸️ Pipeline 已暂停")

        # 干预4: 恢复
        await pipeline_orchestrator.resume_pipeline(pipeline.id)
        print("  ▶️ Pipeline 已恢复")

        # ========== 阶段 6: 任务执行 ==========
        print("\n📌 阶段 6: 任务执行")
        print("-"*40)

        # 分配并执行部分任务
        backend_tasks = [t for t in created_tasks.values()
                        if "API" in t.title or "表" in t.title][:3]

        async def mock_execute(task):
            print(f"    🔄 执行中: {task.title}")
            await asyncio.sleep(0.1)
            return {"success": True, "summary": f"完成: {task.title}"}

        for task in backend_tasks:
            await agent_executor.assign_task(
                task_id=task.id,
                agent_id="backend_agent",
                agent_execute_fn=mock_execute
            )
            await agent_executor.start_execution(task.id)

        # 等待执行完成
        await asyncio.sleep(0.5)

        print(f"  ✅ 任务执行: {len(backend_tasks)} 个任务已启动")

        # ========== 阶段 7: 代码审查 ==========
        print("\n📌 阶段 7: 代码审查")
        print("-"*40)

        reviews = MockLLMData.CODE_REVIEWS

        for issue_key, review in reviews.items():
            print(f"  🔍 [{review['severity'].upper()}] {issue_key}")
            print(f"     问题: {review['message']}")
            print(f"     建议: {review['suggestion']}")

        # ========== 阶段 8: 结果验证 ==========
        print("\n📌 阶段 8: 结果验证")
        print("-"*40)

        # 验证任务
        all_tasks = task_board.list_tasks()
        print(f"  📋 总任务数: {len(all_tasks)}")

        backlog = task_board.list_tasks(status=TaskStatus.BACKLOG)
        in_progress = task_board.list_tasks(status=TaskStatus.IN_PROGRESS)
        review = task_board.list_tasks(status=TaskStatus.REVIEW)
        done = task_board.list_tasks(status=TaskStatus.DONE)

        print(f"     待办: {len(backlog)}")
        print(f"     进行中: {len(in_progress)}")
        print(f"     审核中: {len(review)}")
        print(f"     已完成: {len(done)}")

        # 验证 Pipeline
        pipeline_info = pipeline_orchestrator.get_pipeline(pipeline.id)
        print(f"\n  🔧 Pipeline 状态: {pipeline_info['status']}")
        print(f"     当前阶段: {pipeline_info['current_stage']}")
        print(f"     进度: {pipeline_info['progress']*100:.0f}%")

        # 验证干预
        interventions = pipeline_orchestrator.get_intervention_queue()
        print(f"\n  👤 干预次数: {len(interventions)}")

        # ========== 完成 ==========
        print("\n" + "="*60)
        print("🎉 端到端测试完成!")
        print("="*60)

        # 断言验证
        assert len(all_tasks) == 12, "应该有12个任务"
        assert pipeline_info["status"] in ["running", "paused", "completed"]
        assert len(interventions) >= 3, "至少有3次干预"

    @pytest.mark.asyncio
    async def test_task_status_workflow(self):
        """任务状态完整工作流测试"""
        print("\n" + "="*60)
        print("🔄 任务状态完整工作流测试")
        print("="*60)

        # 创建任务
        task = task_board.create_task(
            title="实现用户注册API",
            description="POST /api/users/register",
            priority=Priority.HIGH,
            created_by="pm"
        )
        print(f"\n✅ 创建任务: {task.title} (状态: {task.status})")

        # 分配
        task_board.assign_agents(task.id, ["backend"])
        print(f"✅ 分配给: backend")

        # 状态流转
        transitions = [
            (TaskStatus.TODO, "pm"),
            (TaskStatus.IN_PROGRESS, "backend"),
            (TaskStatus.REVIEW, "backend"),
            (TaskStatus.DONE, "tester")
        ]

        for new_status, changed_by in transitions:
            task_board.change_status(task.id, new_status, changed_by)
            current = task_board.get_task(task.id)
            print(f"✅ 状态变更: {current.status} (by {changed_by})")

        # 验证
        final_task = task_board.get_task(task.id)
        assert final_task.status == TaskStatus.DONE
        print(f"\n🎉 任务 '{final_task.title}' 已完成!")

    @pytest.mark.asyncio
    async def test_multi_agent_collaboration(self):
        """多 Agent 协作测试"""
        print("\n" + "="*60)
        print("👥 多 Agent 协作测试")
        print("="*60)

        # 设置发言模式
        speaking_controller.set_mode("collab_session", SpeakingMode.ROUND_ROBIN)
        speaking_controller.set_token_budget("collab_session", 10000)

        # Agent 接收消息
        received = {agent_id: [] for agent_id in ["pm", "backend", "frontend"]}

        def create_callback(agent_id):
            def callback(msg):
                received[agent_id].append(msg)
            return callback

        for agent_id in received.keys():
            message_bus.subscribe(agent_id, ["public"], create_callback(agent_id))

        # 模拟多轮讨论
        agents = ["pm", "architect", "backend", "frontend", "tester"]
        for i, agent_id in enumerate(agents):
            msg = Message(
                sender_id=agent_id,
                sender_name=MockLLMData.AGENT_PROFILES[agent_id]["name"],
                content=f"这是第 {i+1} 轮讨论内容: 关于项目进展的讨论。",
                message_type=MessageType.TEXT
            )
            await message_bus.broadcast(msg)
            print(f"  📢 [{msg.sender_name}]: {msg.content[:30]}...")

        # 验证所有 Agent 都收到消息
        print(f"\n📊 消息统计:")
        for agent_id, messages in received.items():
            print(f"  - {agent_id}: 收到 {len(messages)} 条消息")

        assert all(len(msgs) == len(agents) for msgs in received.values())
        print("\n✅ 所有 Agent 都收到了完整的讨论内容")


class TestMockLLMDataQuality:
    """Mock LLM 数据质量测试"""

    def test_discussion_flow_completeness(self):
        """测试讨论流程完整性"""
        for topic in ["requirement", "task_breakdown"]:
            flow = MockLLMData.get_discussion_flow(topic)
            assert len(flow) > 0, f"{topic} 流程不应为空"

            agents_in_flow = set(step["agent"] for step in flow)
            print(f"\n✅ {topic}: {len(flow)} 步, {len(agents_in_flow)} 个 Agent")

    def test_task_breakdown_structure(self):
        """测试任务拆解结构"""
        breakdown = MockLLMData.TASK_BREAKDOWN

        assert "phases" in breakdown
        assert len(breakdown["phases"]) > 0

        total_tasks = sum(len(phase["tasks"]) for phase in breakdown["phases"])
        print(f"\n✅ 任务拆解: {len(breakdown['phases'])} 个阶段, {total_tasks} 个任务")

        for phase in breakdown["phases"]:
            assert "phase" in phase
            assert "tasks" in phase
            for task in phase["tasks"]:
                assert "title" in task
                assert "description" in task
                assert "priority" in task

    def test_agent_profiles(self):
        """测试 Agent 配置"""
        profiles = MockLLMData.AGENT_PROFILES

        required_agents = ["pm", "architect", "backend", "frontend", "tester"]
        for agent in required_agents:
            assert agent in profiles
            profile = profiles[agent]
            assert "name" in profile
            assert "role" in profile
            assert "expertise" in profile
            print(f"\n✅ {agent}: {profile['name']} ({profile['role']})")

    def test_code_templates(self):
        """测试代码模板"""
        templates = MockLLMData.CODE_TEMPLATES

        assert "user_model" in templates
        assert "register_endpoint" in templates
        assert "login_endpoint" in templates

        for key, template in templates.items():
            assert len(template) > 50, f"{key} 模板太短"
            print(f"\n✅ {key}: {len(template)} 字符")

    def test_response_generation(self):
        """测试响应生成"""
        agents = ["pm", "architect", "backend"]
        response_types = ["discussion", "analysis", "code", "review"]

        for agent in agents:
            for resp_type in response_types:
                response = get_mock_response(
                    prompt="测试提示词",
                    agent=agent,
                    response_type=resp_type
                )

                assert response.agent == agent
                assert response.response_type == resp_type
                assert response.tokens_used > 0
                assert len(response.content) > 0

        print(f"\n✅ 响应生成: {len(agents)} agents × {len(response_types)} types = {len(agents)*len(response_types)} combinations")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
