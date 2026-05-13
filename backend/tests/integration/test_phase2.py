import pytest
import asyncio
from app.services.collaboration.message_bus import MessageBus, Message, MessageType, MessageChannel
from app.services.collaboration.speaking_controller import SpeakingController, SpeakingMode, AgentSpeakingConfig
from app.services.collaboration.task_board import TaskBoard
from app.models.task import TaskStatus, Priority


class TestMessageBus:
    def setup_method(self):
        self.bus = MessageBus()

    @pytest.mark.asyncio
    async def test_broadcast(self):
        msg = Message(
            sender_id="agent1",
            sender_name="Agent 1",
            content="Hello everyone!"
        )
        await self.bus.broadcast(msg)
        assert msg.channel == "public"
        assert len(msg.recipients) == 0

        history = self.bus.get_history()
        assert len(history) == 1
        assert history[0].content == "Hello everyone!"

    @pytest.mark.asyncio
    async def test_private_message(self):
        msg = Message(
            sender_id="agent1",
            sender_name="Agent 1",
            recipients=["agent2"],
            content="Hello agent2!"
        )
        await self.bus.send_private(msg)
        assert msg.channel == "private"
        assert msg.recipients == ["agent2"]

    @pytest.mark.asyncio
    async def test_group_message(self):
        msg = Message(
            sender_id="agent1",
            sender_name="Agent 1",
            recipients=["agent2", "agent3"],
            content="Hello group!"
        )
        await self.bus.send_group(msg, "project-alpha")
        assert msg.channel == "project-alpha"
        assert len(msg.recipients) == 2

    @pytest.mark.asyncio
    async def test_task_message(self):
        msg = Message(
            sender_id="agent1",
            sender_name="Agent 1",
            content="Task update"
        )
        await self.bus.send_to_task(msg, "task-123")
        assert msg.channel == "task:task-123"

    def test_subscribe_callback(self):
        received = []

        def callback(msg):
            received.append(msg)

        self.bus.subscribe("agent1", ["public"], callback)

        msg = Message(
            sender_id="agent2",
            sender_name="Agent 2",
            content="Test"
        )
        asyncio.run(self.bus.broadcast(msg))

        assert len(received) == 1
        assert received[0].content == "Test"

    def test_channel_membership(self):
        self.bus.join_channel("agent1", "project-alpha")
        self.bus.join_channel("agent2", "project-alpha")

        members = self.bus.get_channel_members("project-alpha")
        assert len(members) == 2
        assert "agent1" in members
        assert "agent2" in members

        self.bus.leave_channel("agent1", "project-alpha")
        members = self.bus.get_channel_members("project-alpha")
        assert len(members) == 1


class TestSpeakingController:
    def setup_method(self):
        self.controller = SpeakingController()

    def test_set_mode(self):
        self.controller.set_mode("session1", SpeakingMode.ROUND_ROBIN)
        assert self.controller.get_mode("session1") == SpeakingMode.ROUND_ROBIN

    def test_token_budget(self):
        budget = self.controller.set_token_budget("session1", 10000)
        assert budget.total_budget == 10000
        assert budget.remaining() == 10000

        self.controller.consume_tokens("session1", 2000)
        assert budget.remaining() == 8000
        assert not budget.is_exhausted()

        self.controller.consume_tokens("session1", 8000)
        assert budget.is_exhausted()

    def test_agent_config(self):
        config = AgentSpeakingConfig(
            agent_id="agent1",
            max_messages_per_minute=5,
            priority=10
        )
        self.controller.set_agent_config("agent1", config)

        retrieved = self.controller.get_agent_config("agent1")
        assert retrieved.max_messages_per_minute == 5
        assert retrieved.priority == 10

    @pytest.mark.asyncio
    async def test_free_style_mode(self):
        self.controller.set_mode("session1", SpeakingMode.FREE_STYLE)

        turn = await self.controller.request_speak(
            session_id="session1",
            agent_id="agent1",
            agent_name="Agent 1"
        )

        assert turn is not None
        assert turn.agent_id == "agent1"

    @pytest.mark.asyncio
    async def test_round_robin_mode(self):
        self.controller.set_mode("session1", SpeakingMode.ROUND_ROBIN)

        turn1 = await self.controller.request_speak(
            session_id="session1",
            agent_id="agent1",
            agent_name="Agent 1"
        )

        turn2 = await self.controller.request_speak(
            session_id="session1",
            agent_id="agent2",
            agent_name="Agent 2"
        )

        queue = self.controller.get_queue("session1")
        assert len(queue) == 2

        next_turn = await self.controller.next_turn("session1")
        assert next_turn.agent_id == "agent1"

    @pytest.mark.asyncio
    async def test_priority_based_mode(self):
        self.controller.set_mode("session1", SpeakingMode.PRIORITY_BASED)

        await self.controller.request_speak(
            session_id="session1",
            agent_id="agent1",
            agent_name="Agent 1",
            priority=5
        )

        await self.controller.request_speak(
            session_id="session1",
            agent_id="agent2",
            agent_name="Agent 2",
            priority=10
        )

        next_turn = await self.controller.next_turn("session1")
        assert next_turn.agent_id == "agent2"
        assert next_turn.priority == 10

    def test_queue_management(self):
        self.controller.set_mode("session1", SpeakingMode.ROUND_ROBIN)

        asyncio.run(self.controller.request_speak(
            session_id="session1",
            agent_id="agent1",
            agent_name="Agent 1"
        ))

        assert self.controller.get_queue_length("session1") == 1

        cleared = asyncio.run(self.controller.clear_queue("session1"))
        assert cleared == 1
        assert self.controller.get_queue_length("session1") == 0

    def test_cleanup_session(self):
        self.controller.set_mode("session1", SpeakingMode.ROUND_ROBIN)
        self.controller.set_token_budget("session1", 10000)

        self.controller.cleanup_session("session1")

        assert self.controller.get_mode("session1") == SpeakingMode.FREE_STYLE
        assert self.controller.get_token_budget("session1") is None


class TestTaskBoard:
    def setup_method(self):
        self.board = TaskBoard()

    def test_create_task(self):
        task = self.board.create_task(
            title="Test task",
            description="Description",
            priority=Priority.HIGH
        )

        assert task.id is not None
        assert task.title == "Test task"
        assert task.status == TaskStatus.BACKLOG

        retrieved = self.board.get_task(task.id)
        assert retrieved.title == "Test task"

    def test_update_task(self):
        task = self.board.create_task(title="Original title")

        updated = self.board.update_task(
            task_id=task.id,
            title="Updated title",
            priority=Priority.URGENT
        )

        assert updated.title == "Updated title"
        assert updated.priority == Priority.URGENT

    def test_assign_agents(self):
        task = self.board.create_task(title="Task 1")

        self.board.assign_agents(task.id, ["agent1", "agent2"])

        task = self.board.get_task(task.id)
        assert len(task.assigned_agents) == 2
        assert "agent1" in task.assigned_agents

        agent_tasks = self.board.get_tasks_by_agent("agent1")
        assert len(agent_tasks) == 1

    def test_status_transition(self):
        task = self.board.create_task(title="Task")

        self.board.change_status(task.id, TaskStatus.TODO)
        assert self.board.get_task(task.id).status == TaskStatus.TODO

        self.board.change_status(task.id, TaskStatus.IN_PROGRESS)
        assert self.board.get_task(task.id).status == TaskStatus.IN_PROGRESS

        with pytest.raises(ValueError):
            self.board.change_status(task.id, TaskStatus.BACKLOG)

    def test_invalid_status_transition(self):
        task = self.board.create_task(title="Task")

        self.board.change_status(task.id, TaskStatus.TODO)
        self.board.change_status(task.id, TaskStatus.IN_PROGRESS)

        with pytest.raises(ValueError):
            self.board.change_status(task.id, TaskStatus.CANCELLED)

    def test_task_history(self):
        task = self.board.create_task(title="Task")

        self.board.change_status(task.id, TaskStatus.TODO)
        self.board.add_comment(task.id, "Working on it", "agent1")

        task = self.board.get_task(task.id)
        assert len(task.history) == 2

    def test_list_tasks(self):
        self.board.create_task(title="Task 1", priority=Priority.HIGH)
        self.board.create_task(title="Task 2", priority=Priority.MEDIUM)
        self.board.create_task(title="Task 3", priority=Priority.LOW)

        all_tasks = self.board.list_tasks()
        assert len(all_tasks) == 3
        assert all_tasks[0].priority == Priority.HIGH

        high_priority = self.board.list_tasks(priority=Priority.HIGH)
        assert len(high_priority) == 1

    def test_get_board(self):
        self.board.create_task(title="Task 1")
        self.board.create_task(title="Task 2")
        self.board.create_task(title="Task 3")

        self.board.change_status(
            self.board.list_tasks()[0].id,
            TaskStatus.TODO
        )

        board = self.board.get_tasks_by_board()
        assert TaskStatus.BACKLOG in board
        assert TaskStatus.TODO in board

    def test_delete_task(self):
        task = self.board.create_task(title="To delete")
        task_id = task.id

        success = self.board.delete_task(task_id)
        assert success
        assert self.board.get_task(task_id) is None

    def test_search_tasks(self):
        self.board.create_task(title="Build user authentication")
        self.board.create_task(title="Build admin panel")
        self.board.create_task(title="Fix login bug")

        results = self.board.search_tasks("build")
        assert len(results) == 2

        results = self.board.search_tasks("login")
        assert len(results) == 1

    def test_task_count(self):
        self.board.create_task(title="Task 1")
        self.board.create_task(title="Task 2")

        self.board.change_status(
            self.board.list_tasks()[0].id,
            TaskStatus.TODO
        )

        total = self.board.get_task_count()
        assert total == 2

        backlog_count = self.board.get_task_count(TaskStatus.BACKLOG)
        assert backlog_count == 1

        todo_count = self.board.get_task_count(TaskStatus.TODO)
        assert todo_count == 1
