"""
Phase 2 集成测试 - 协作引擎
使用 Mock LLM 数据测试消息总线、发言控制器和任务看板

运行方式：
    pytest tests/test_phase2_integration.py -v
    pytest tests/test_phase2_integration.py::TestMessageBus -v
    pytest tests/test_phase2_integration.py::TestSpeakingController -v
    pytest tests/test_phase2_integration.py::TestTaskBoard -v
"""

import pytest
import asyncio
from datetime import datetime
from typing import List

import sys
sys.path.insert(0, 'd:/AIproject/devteam-ai/backend')

from app.services.collaboration.message_bus import message_bus, Message, MessageType, MessageChannel
from app.services.collaboration.speaking_controller import speaking_controller, SpeakingMode, SpeakingTurn
from app.services.collaboration.task_board import task_board, TaskStatus, Priority
from app.models.task import Task

from tests.mock.mock_llm_data import MockLLMData, get_mock_response, SCENARIOS


class TestMessageBus:
    """消息总线测试"""

    def setup_method(self):
        """每个测试前清空消息总线"""
        message_bus.clear_history()

    def test_broadcast_message(self):
        """测试广播消息"""
        received = []

        def callback(msg):
            received.append(msg)

        # 订阅公共频道
        sub_id = message_bus.subscribe("agent_1", ["public"], callback)

        # 发送广播
        msg = Message(
            sender_id="pm",
            sender_name="产品经理",
            content="大家好，开始讨论项目",
            message_type=MessageType.TEXT
        )
        asyncio.run(message_bus.broadcast(msg))

        # 验证收到消息
        assert len(received) == 1
        assert received[0].content == "大家好，开始讨论项目"
        assert received[0].sender_id == "pm"

    def test_private_message(self):
        """测试私信"""
        received = []

        def callback(msg):
            received.append(msg)

        # 订阅
        sub_id = message_bus.subscribe("backend", ["private"], callback)

        # 发送私信
        msg = Message(
            sender_id="pm",
            sender_name="产品经理",
            recipients=["backend"],
            content="这个任务交给你负责",
            message_type=MessageType.ACTION
        )
        asyncio.run(message_bus.send_private(msg))

        # 验证收到消息
        assert len(received) == 1
        assert received[0].content == "这个任务交给你负责"
        assert received[0].is_private()

    def test_multi_agent_discussion(self):
        """测试多 Agent 讨论场景"""
        received_by_agent = {"pm": [], "backend": [], "frontend": []}

        def create_callback(agent_id):
            def callback(msg):
                received_by_agent[agent_id].append(msg)
            return callback

        # 多个 Agent 订阅
        message_bus.subscribe("pm", ["public"], create_callback("pm"))
        message_bus.subscribe("backend", ["public"], create_callback("backend"))
        message_bus.subscribe("frontend", ["public"], create_callback("frontend"))

        # 模拟讨论
        messages = [
            ("pm", "产品经理", "大家好，今天讨论用户管理系统"),
            ("architect", "架构师", "我建议采用前后端分离架构"),
            ("backend", "后端开发", "后端用 FastAPI，我来负责"),
            ("frontend", "前端开发", "前端用 React，UI我来设计"),
        ]

        for sender_id, sender_name, content in messages:
            msg = Message(
                sender_id=sender_id,
                sender_name=sender_name,
                content=content,
                message_type=MessageType.TEXT
            )
            asyncio.run(message_bus.broadcast(msg))

        # 验证所有 Agent 都收到所有消息
        assert len(received_by_agent["pm"]) == 4
        assert len(received_by_agent["backend"]) == 4
        assert len(received_by_agent["frontend"]) == 4

    def test_message_history(self):
        """测试消息历史"""
        # 发送几条消息
        for i in range(5):
            msg = Message(
                sender_id="pm",
                sender_name="产品经理",
                content=f"消息 {i+1}",
                message_type=MessageType.TEXT
            )
            asyncio.run(message_bus.broadcast(msg))

        # 获取历史
        history = message_bus.get_history("public", limit=10)

        assert len(history) == 5
        assert history[0].content == "消息 1"
        assert history[-1].content == "消息 5"


class TestSpeakingController:
    """发言控制器测试"""

    def setup_method(self):
        """每个测试前重置"""
        speaking_controller.cleanup_session("test_session")
        speaking_controller.set_mode("test_session", SpeakingMode.FREE_STYLE)

    def test_free_style_mode(self):
        """测试自由发言模式"""
        speaking_controller.set_mode("test_session", SpeakingMode.FREE_STYLE)

        # 多个 Agent 请求发言
        turns = []
        for agent_id in ["pm", "architect", "backend"]:
            turn = asyncio.run(speaking_controller.request_speak(
                "test_session", agent_id, f"Agent_{agent_id}"
            ))
            turns.append(turn)

        # 自由模式下立即返回
        assert all(t is not None for t in turns)

    def test_round_robin_mode(self):
        """测试轮询发言模式"""
        speaking_controller.set_mode("test_session", SpeakingMode.ROUND_ROBIN)

        # Agent 请求发言
        turn1 = asyncio.run(speaking_controller.request_speak(
            "test_session", "pm", "产品经理"
        ))
        assert turn1 is not None

        # 获取下一轮
        next_turn = asyncio.run(speaking_controller.next_turn("test_session"))

        # 队列应该为空（新发言者直接发言）
        assert speaking_controller.get_queue_length("test_session") == 0

    def test_priority_mode(self):
        """测试优先级模式"""
        speaking_controller.set_mode("test_session", SpeakingMode.PRIORITY_BASED)

        # 用户发言（高优先级）
        user_turn = asyncio.run(speaking_controller.request_speak(
            "test_session", "human", "用户", priority=100, is_user=True
        ))

        # 普通 Agent 发言
        agent_turn = asyncio.run(speaking_controller.request_speak(
            "test_session", "pm", "产品经理", priority=10
        ))

        assert user_turn is not None
        assert agent_turn is not None
        assert user_turn.priority > agent_turn.priority

    def test_token_budget(self):
        """测试 Token 预算控制"""
        budget = speaking_controller.set_token_budget("test_session", total_budget=1000)

        assert budget.total_budget == 1000
        assert budget.remaining() == 1000

        # 消费 Token
        speaking_controller.consume_tokens("test_session", 300)
        assert budget.remaining() == 700

        # 消费到耗尽
        speaking_controller.consume_tokens("test_session", 700)
        assert budget.remaining() == 0
        assert budget.is_exhausted()

    def test_rate_limit(self):
        """测试频率限制"""
        speaking_controller.set_mode("test_session", SpeakingMode.SEQUENTIAL)

        for _ in range(2):
            result = asyncio.run(speaking_controller.request_speak(
                "test_session", "test_agent", "TestAgent"
            ))
            assert result is not None

    def test_queue_management(self):
        """测试队列管理"""
        speaking_controller.set_mode("test_session", SpeakingMode.SEQUENTIAL)

        # 添加多个发言
        for agent_id in ["pm", "backend", "frontend"]:
            asyncio.run(speaking_controller.request_speak(
                "test_session", agent_id, f"Agent_{agent_id}"
            ))

        assert speaking_controller.get_queue_length("test_session") == 3

        # 获取下一个
        turn = asyncio.run(speaking_controller.next_turn("test_session"))
        assert turn.agent_id == "pm"
        assert speaking_controller.get_queue_length("test_session") == 2

        # 清空队列
        count = asyncio.run(speaking_controller.clear_queue("test_session"))
        assert count == 2
        assert speaking_controller.get_queue_length("test_session") == 0


class TestTaskBoard:
    """任务看板测试"""

    def setup_method(self):
        """每个测试前清空"""
        task_board.clear_all()

    def test_create_task(self):
        """测试创建任务"""
        task = asyncio.run(task_board.create_task(
            project_id="test-project",
            title="设计数据库架构",
            description="设计用户管理模块的数据库表结构",
            priority=Priority.HIGH,
            created_by="pm"
        ))

        assert task is not None
        assert task.title == "设计数据库架构"
        assert task.status == TaskStatus.BACKLOG
        assert task.priority == Priority.HIGH

    def test_task_status_transition(self):
        """测试任务状态流转"""
        # 创建任务
        task = asyncio.run(task_board.create_task(
            project_id="test-project",
            title="测试任务",
            created_by="pm"
        ))
        task_id = task.id

        # 流转: BACKLOG -> TODO -> IN_PROGRESS -> REVIEW -> DONE
        asyncio.run(task_board.change_status(task_id, TaskStatus.TODO, "pm"))

        assert task_board.get_task(task_id).status == TaskStatus.TODO

        asyncio.run(task_board.change_status(task_id, TaskStatus.IN_PROGRESS, "backend"))

        assert task_board.get_task(task_id).status == TaskStatus.IN_PROGRESS

        asyncio.run(task_board.change_status(task_id, TaskStatus.REVIEW, "backend"))

        assert task_board.get_task(task_id).status == TaskStatus.REVIEW

        asyncio.run(task_board.change_status(task_id, TaskStatus.DONE, "tester"))

        assert task_board.get_task(task_id).status == TaskStatus.DONE

    def test_invalid_status_transition(self):
        """测试无效状态流转"""
        task = asyncio.run(task_board.create_task(project_id="test-project", title="测试任务", created_by="pm"))


        # BACKLOG 不能直接到 DONE
        with pytest.raises(ValueError):
            asyncio.run(task_board.change_status(task.id, TaskStatus.DONE, "pm"))


    def test_task_assignment(self):
        """测试任务分配"""
        task = asyncio.run(task_board.create_task(
            project_id="test-project",
            title="后端开发",
            assigned_agents=["backend"],
            created_by="pm"
        ))

        # 按负责人查询
        tasks = task_board.get_tasks_by_agent("backend")
        assert len(tasks) == 1
        assert tasks[0].title == "后端开发"

    def test_task_priority(self):
        """测试任务优先级排序"""
        # 创建不同优先级的任务
        asyncio.run(task_board.create_task(project_id="test-project", title="低优先级", priority=Priority.LOW, created_by="pm"))

        asyncio.run(task_board.create_task(project_id="test-project", title="紧急任务", priority=Priority.URGENT, created_by="pm"))

        asyncio.run(task_board.create_task(project_id="test-project", title="中优先级", priority=Priority.MEDIUM, created_by="pm"))

        asyncio.run(task_board.create_task(project_id="test-project", title="高优先级", priority=Priority.HIGH, created_by="pm"))


        # 按优先级排序查询
        tasks = task_board.list_tasks()

        # 验证排序顺序
        priorities = [t.priority.sort_value for t in tasks]
        assert priorities == sorted(priorities, reverse=True)

    def test_task_board_view(self):
        """测试看板视图"""
        task_board.clear_all()
        task1 = asyncio.run(task_board.create_task(project_id="test-project", title="任务1", created_by="pm"))

        task2 = asyncio.run(task_board.create_task(project_id="test-project", title="任务2", created_by="pm"))

        task3 = asyncio.run(task_board.create_task(project_id="test-project", title="任务3", created_by="pm"))

        task4 = asyncio.run(task_board.create_task(project_id="test-project", title="任务4", created_by="pm"))


        asyncio.run(task_board.change_status(task1.id, TaskStatus.TODO, "pm"))

        asyncio.run(task_board.change_status(task2.id, TaskStatus.TODO, "pm"))

        asyncio.run(task_board.change_status(task3.id, TaskStatus.TODO, "pm"))

        asyncio.run(task_board.change_status(task3.id, TaskStatus.IN_PROGRESS, "pm"))

        asyncio.run(task_board.change_status(task4.id, TaskStatus.TODO, "pm"))

        asyncio.run(task_board.change_status(task4.id, TaskStatus.IN_PROGRESS, "pm"))

        asyncio.run(task_board.change_status(task4.id, TaskStatus.REVIEW, "pm"))

        asyncio.run(task_board.change_status(task4.id, TaskStatus.DONE, "pm"))


        # 获取看板视图
        board = task_board.get_tasks_by_board()

        assert len(board[TaskStatus.BACKLOG]) == 0
        assert len(board[TaskStatus.TODO]) == 2
        assert len(board[TaskStatus.IN_PROGRESS]) == 1
        assert len(board[TaskStatus.DONE]) == 1

    def test_task_filter(self):
        """测试任务过滤"""
        asyncio.run(task_board.create_task(project_id="test-project", title="前端1", priority=Priority.HIGH, created_by="pm"))

        asyncio.run(task_board.create_task(project_id="test-project", title="前端2", priority=Priority.MEDIUM, created_by="pm"))

        asyncio.run(task_board.create_task(project_id="test-project", title="后端1", priority=Priority.HIGH, created_by="pm"))


        # 筛选高优先级
        high_priority = task_board.list_tasks(priority=Priority.HIGH)
        assert len(high_priority) == 2


class TestPhase2MockScenario:
    """Phase 2 Mock 场景测试"""

    def setup_method(self):
        task_board.clear_all()
        message_bus.clear_history()
        speaking_controller.cleanup_session("demo_session")

    def test_user_management_project_discussion(self):
        """用户管理系统项目讨论场景"""
        scenario = SCENARIOS["user_management"]

        # 1. 初始化讨论
        speaking_controller.set_mode("demo_session", SpeakingMode.PRIORITY_BASED)
        speaking_controller.set_token_budget("demo_session", 10000)

        # 2. 模拟讨论消息
        messages = MockLLMData.get_discussion_flow("requirement")

        received_messages = []
        def on_message(msg):
            received_messages.append(msg)

        message_bus.subscribe("pm", ["public"], on_message)
        message_bus.subscribe("architect", ["public"], on_message)

        # 3. 模拟讨论
        for msg_data in messages:
            mock_response = get_mock_response(
                prompt=msg_data["content"],
                agent=msg_data["agent"],
                response_type="discussion"
            )

            msg = Message(
                sender_id=msg_data["agent"],
                sender_name=MockLLMData.AGENT_PROFILES[msg_data["agent"]]["name"],
                content=mock_response.content,
                message_type=MessageType.TEXT
            )
            asyncio.run(message_bus.broadcast(msg))

        # 4. 验证
        assert len(set(m.id for m in received_messages)) == len(messages)
        print(f"✅ 讨论场景测试通过：收到 {len(set(m.id for m in received_messages))} 条消息")

    def test_task_creation_from_discussion(self):
        """从讨论生成任务"""
        breakdown_data = MockLLMData.TASK_BREAKDOWN

        created_tasks = []
        for phase in breakdown_data["phases"]:
            for task_data in phase["tasks"]:
                task = asyncio.run(task_board.create_task(
                    project_id="test-project",
                    title=task_data["title"],
                    description=task_data["description"],
                    priority=Priority(task_data["priority"]),
                    created_by="pm"
                ))
                created_tasks.append(task)

        assert len(created_tasks) > 0
        total_expected = sum(len(p["tasks"]) for p in breakdown_data["phases"])
        assert len(created_tasks) == total_expected

        urgent_tasks = task_board.list_tasks(priority=Priority.URGENT)
        high_tasks = task_board.list_tasks(priority=Priority.HIGH)
        print(f"✅ 任务创建测试通过：创建了 {len(created_tasks)} 个任务")

    def test_collaboration_workflow(self):
        """协作工作流测试"""
        task = asyncio.run(task_board.create_task(
            project_id="test-project",
            title="实现用户注册API",
            description="POST /api/users/register",
            priority=Priority.HIGH,
            created_by="pm"
        ))

        # 2. 发送任务通知
        msg = Message(
            sender_id="pm",
            sender_name="产品经理",
            content=f"任务分配：{task.title}",
            message_type=MessageType.ACTION
        )
        asyncio.run(message_bus.send_to_task(msg, task.id))

        asyncio.run(task_board.change_status(task.id, TaskStatus.TODO, "pm"))

        asyncio.run(task_board.change_status(task.id, TaskStatus.IN_PROGRESS, "pm"))


        # 3. Backend 完成任务
        mock_response = get_mock_response(
            prompt="实现用户注册API",
            agent="backend",
            response_type="code"
        )

        # 发送完成通知
        msg = Message(
            sender_id="backend",
            sender_name="后端开发",
            content=f"任务完成：{task.title}\n\n代码：\n{mock_response.content}",
            message_type=MessageType.ACTION
        )
        asyncio.run(message_bus.send_to_task(msg, task.id))

        asyncio.run(task_board.change_status(task.id, TaskStatus.REVIEW, "pm"))


        # 5. 验证
        assert task_board.get_task(task.id).status == TaskStatus.REVIEW
        print(f"✅ 协作工作流测试通过：任务 {task.title} 进入审核状态")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
