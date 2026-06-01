"""TaskBoard 单元测试 — 任务生命周期管理。

覆盖 create / update / assign / change_status / delete / list / search / handler。
"""
import pytest
from app.models.task import Task, TaskStatus, Priority, RiskLevel
from app.services.collaboration.task_board import TaskBoard


class TestCreateTask:
    """创建任务。"""

    @pytest.mark.asyncio
    async def test_create_basic(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "测试任务", "描述")
        assert task.title == "测试任务"
        assert task.description == "描述"
        assert task.project_id == "proj-1"
        assert task.status == TaskStatus.BACKLOG
        assert task.priority == Priority.MEDIUM

    @pytest.mark.asyncio
    async def test_create_with_full_fields(self):
        board = TaskBoard()
        task = await board.create_task(
            "proj-1", "紧急修复", "修bug",
            priority=Priority.URGENT,
            assigned_agents=["agent-a", "agent-b"],
            created_by="user-1",
            tags=["bug", "p0"],
            dependencies=["task-1"],
            risk_level=RiskLevel.HIGH,
        )
        assert task.priority == Priority.URGENT
        assert task.risk_level == RiskLevel.HIGH
        assert task.assigned_agents == ["agent-a", "agent-b"]
        assert task.created_by == "user-1"
        assert task.tags == ["bug", "p0"]
        assert task.dependencies == ["task-1"]

    @pytest.mark.asyncio
    async def test_create_returns_unique_ids(self):
        board = TaskBoard()
        t1 = await board.create_task("proj-1", "任务1")
        t2 = await board.create_task("proj-1", "任务2")
        assert t1.id != t2.id

    @pytest.mark.asyncio
    async def test_create_adds_to_status_index(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "测试")
        backlog = board.get_tasks_by_status(TaskStatus.BACKLOG, "proj-1")
        assert any(t.id == task.id for t in backlog)

    @pytest.mark.asyncio
    async def test_create_adds_to_agent_index(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "测试", assigned_agents=["agent-x"])
        agent_tasks = board.get_tasks_by_agent("agent-x", "proj-1")
        assert any(t.id == task.id for t in agent_tasks)


class TestGetTask:
    """获取任务。"""

    @pytest.mark.asyncio
    async def test_get_by_project_id(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "任务A")
        found = board.get_task(task.id, "proj-1")
        assert found is not None
        assert found.title == "任务A"

    @pytest.mark.asyncio
    async def test_get_without_project_id(self):
        board = TaskBoard()
        task = await board.create_task("proj-2", "任务B")
        found = board.get_task(task.id)
        assert found is not None
        assert found.title == "任务B"

    def test_get_nonexistent(self):
        board = TaskBoard()
        assert board.get_task("no-such-id") is None

    @pytest.mark.asyncio
    async def test_get_wrong_project(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "任务")
        assert board.get_task(task.id, "proj-2") is None


class TestUpdateTask:
    """更新任务字段。"""

    @pytest.mark.asyncio
    async def test_update_title(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "旧标题")
        await board.update_task(task.id, "proj-1", title="新标题")
        assert board.get_task(task.id).title == "新标题"

    @pytest.mark.asyncio
    async def test_update_priority(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "任务", priority=Priority.LOW)
        await board.update_task(task.id, "proj-1", priority=Priority.URGENT)
        assert board.get_task(task.id).priority == Priority.URGENT

    @pytest.mark.asyncio
    async def test_update_tags(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "任务")
        await board.update_task(task.id, "proj-1", tags=["a", "b"])
        assert board.get_task(task.id).tags == ["a", "b"]

    @pytest.mark.asyncio
    async def test_update_dependencies(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "任务")
        await board.update_task(task.id, "proj-1", dependencies=["dep-1"])
        assert board.get_task(task.id).dependencies == ["dep-1"]

    @pytest.mark.asyncio
    async def test_update_metadata(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "任务")
        await board.update_task(task.id, "proj-1", metadata={"key": "val"})
        assert board.get_task(task.id).metadata == {"key": "val"}

    @pytest.mark.asyncio
    async def test_update_nonexistent(self):
        board = TaskBoard()
        result = await board.update_task("ghost", title="x")
        assert result is None


class TestAssignAgents:
    """分配 Agent。"""

    @pytest.mark.asyncio
    async def test_assign_new_agents(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "任务")
        await board.assign_agents(task.id, ["agent-1", "agent-2"], "proj-1")
        assert board.get_task(task.id).assigned_agents == ["agent-1", "agent-2"]

    @pytest.mark.asyncio
    async def test_reassign_removes_old_from_index(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "任务", assigned_agents=["old-agent"])
        await board.assign_agents(task.id, ["new-agent"], "proj-1")
        old_tasks = board.get_tasks_by_agent("old-agent", "proj-1")
        new_tasks = board.get_tasks_by_agent("new-agent", "proj-1")
        assert len(old_tasks) == 0
        assert len(new_tasks) == 1

    @pytest.mark.asyncio
    async def test_assign_nonexistent_task(self):
        board = TaskBoard()
        result = await board.assign_agents("ghost", ["agent-1"])
        assert result is None


class TestChangeStatus:
    """状态变更。"""

    @pytest.mark.asyncio
    async def test_valid_transition_backlog_to_todo(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "任务")
        await board.change_status(task.id, TaskStatus.TODO, "user-1", "proj-1")
        assert board.get_task(task.id).status == TaskStatus.TODO

    @pytest.mark.asyncio
    async def test_valid_transition_todo_to_in_progress(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "任务")
        await board.change_status(task.id, TaskStatus.TODO)
        await board.change_status(task.id, TaskStatus.IN_PROGRESS)
        assert board.get_task(task.id).status == TaskStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_invalid_transition_raises(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "任务")
        with pytest.raises(ValueError, match="Invalid status transition"):
            await board.change_status(task.id, TaskStatus.DONE)  # BACKLOG → DONE 非法

    @pytest.mark.asyncio
    async def test_same_status_noop(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "任务")
        result = await board.change_status(task.id, TaskStatus.BACKLOG)
        assert result is not None
        assert result.status == TaskStatus.BACKLOG

    @pytest.mark.asyncio
    async def test_status_index_updated(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "任务")
        assert board.get_task_count(TaskStatus.BACKLOG, "proj-1") == 1
        await board.change_status(task.id, TaskStatus.TODO)
        assert board.get_task_count(TaskStatus.BACKLOG, "proj-1") == 0
        assert board.get_task_count(TaskStatus.TODO, "proj-1") == 1

    @pytest.mark.asyncio
    async def test_status_change_adds_history(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "任务")
        await board.change_status(task.id, TaskStatus.TODO, "tester")
        history_count = len(board.get_task(task.id).history)
        assert history_count >= 1

    @pytest.mark.asyncio
    async def test_change_nonexistent_task(self):
        board = TaskBoard()
        result = await board.change_status("ghost", TaskStatus.TODO)
        assert result is None


class TestAddComment:
    """添加评论。"""

    @pytest.mark.asyncio
    async def test_add_comment(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "任务")
        result = await board.add_comment(task.id, "这是一条评论", "reviewer", "proj-1")
        assert result is not None
        histories = board.get_task(task.id).history
        assert any("这是一条评论" in h.action for h in histories)

    @pytest.mark.asyncio
    async def test_add_comment_nonexistent(self):
        board = TaskBoard()
        result = await board.add_comment("ghost", "评论")
        assert result is None


class TestDeleteTask:
    """删除任务。"""

    @pytest.mark.asyncio
    async def test_delete_existing(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "任务")
        assert await board.delete_task(task.id, "proj-1") is True
        assert board.get_task(task.id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self):
        board = TaskBoard()
        assert await board.delete_task("ghost") is False

    @pytest.mark.asyncio
    async def test_delete_removes_from_status_index(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "任务")
        await board.delete_task(task.id, "proj-1")
        assert board.get_task_count(TaskStatus.BACKLOG, "proj-1") == 0

    @pytest.mark.asyncio
    async def test_delete_removes_from_agent_index(self):
        board = TaskBoard()
        task = await board.create_task("proj-1", "任务", assigned_agents=["agent-x"])
        await board.delete_task(task.id, "proj-1")
        assert len(board.get_tasks_by_agent("agent-x", "proj-1")) == 0


class TestListTasks:
    """任务列表（过滤、排序、分页）。"""

    async def _setup(self):
        board = TaskBoard()
        t1 = await board.create_task("proj-1", "高优Bug", priority=Priority.HIGH, tags=["bug"])
        t2 = await board.create_task("proj-1", "低优文档", priority=Priority.LOW, tags=["doc"])
        t3 = await board.create_task("proj-2", "另一个任务", priority=Priority.MEDIUM)
        return board, t1, t2, t3

    @pytest.mark.asyncio
    async def test_list_all_in_project(self):
        board, t1, t2, t3 = await self._setup()
        tasks = board.list_tasks(project_id="proj-1")
        assert len(tasks) == 2

    @pytest.mark.asyncio
    async def test_list_all_projects(self):
        board, t1, t2, t3 = await self._setup()
        tasks = board.list_tasks()
        assert len(tasks) == 3

    @pytest.mark.asyncio
    async def test_filter_by_status(self):
        board, t1, t2, t3 = await self._setup()
        await board.change_status(t1.id, TaskStatus.TODO)
        tasks = board.list_tasks(status=TaskStatus.TODO)
        assert len(tasks) == 1
        assert tasks[0].id == t1.id

    @pytest.mark.asyncio
    async def test_filter_by_priority(self):
        board, t1, t2, t3 = await self._setup()
        tasks = board.list_tasks(priority=Priority.HIGH)
        assert len(tasks) == 1
        assert tasks[0].title == "高优Bug"

    @pytest.mark.asyncio
    async def test_filter_by_agent(self):
        board = TaskBoard()
        await board.create_task("proj-1", "任务A", assigned_agents=["agent-1"])
        await board.create_task("proj-1", "任务B", assigned_agents=["agent-2"])
        tasks = board.list_tasks(assigned_agent="agent-1")
        assert len(tasks) == 1
        assert tasks[0].title == "任务A"

    @pytest.mark.asyncio
    async def test_filter_by_tags(self):
        board, t1, t2, t3 = await self._setup()
        tasks = board.list_tasks(tags=["bug"])
        assert len(tasks) == 1
        assert tasks[0].title == "高优Bug"

    @pytest.mark.asyncio
    async def test_filter_by_created_by(self):
        board = TaskBoard()
        await board.create_task("proj-1", "系统任务", created_by="system")
        await board.create_task("proj-1", "用户任务", created_by="user-a")
        tasks = board.list_tasks(created_by="user-a")
        assert len(tasks) == 1
        assert tasks[0].title == "用户任务"

    @pytest.mark.asyncio
    async def test_sort_by_priority_then_created(self):
        board = TaskBoard()
        await board.create_task("proj-1", "低", priority=Priority.LOW)
        await board.create_task("proj-1", "高", priority=Priority.HIGH)
        tasks = board.list_tasks()
        assert tasks[0].title == "高"
        assert tasks[1].title == "低"

    @pytest.mark.asyncio
    async def test_limit_and_offset(self):
        board = TaskBoard()
        for i in range(5):
            await board.create_task("proj-1", f"任务{i}")
        tasks = board.list_tasks(limit=2, offset=1)
        assert len(tasks) == 2


class TestGetTasksByStatus:
    """按状态查询。"""

    @pytest.mark.asyncio
    async def test_by_status_in_project(self):
        board = TaskBoard()
        t = await board.create_task("proj-1", "任务")
        await board.change_status(t.id, TaskStatus.TODO)
        results = board.get_tasks_by_status(TaskStatus.TODO, "proj-1")
        assert len(results) == 1
        assert results[0].id == t.id

    @pytest.mark.asyncio
    async def test_by_status_all_projects(self):
        board = TaskBoard()
        await board.create_task("proj-1", "任务1")
        await board.create_task("proj-2", "任务2")
        assert len(board.get_tasks_by_status(TaskStatus.BACKLOG)) == 2


class TestGetTasksByAgent:
    """按 Agent 查询。"""

    @pytest.mark.asyncio
    async def test_by_agent_in_project(self):
        board = TaskBoard()
        await board.create_task("proj-1", "任务", assigned_agents=["agent-x"])
        results = board.get_tasks_by_agent("agent-x", "proj-1")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_by_agent_all_projects(self):
        board = TaskBoard()
        await board.create_task("proj-1", "任务1", assigned_agents=["agent-x"])
        await board.create_task("proj-2", "任务2", assigned_agents=["agent-x"])
        assert len(board.get_tasks_by_agent("agent-x")) == 2

    def test_agent_with_no_tasks(self):
        board = TaskBoard()
        assert board.get_tasks_by_agent("no-such-agent") == []


class TestGetTasksByBoard:
    """看板视图。"""

    @pytest.mark.asyncio
    async def test_board_view(self):
        board = TaskBoard()
        await board.create_task("proj-1", "任务1")
        await board.create_task("proj-1", "任务2")
        kanban = board.get_tasks_by_board("proj-1")
        assert isinstance(kanban, dict)
        assert len(kanban[TaskStatus.BACKLOG]) == 2
        assert len(kanban[TaskStatus.DONE]) == 0


class TestGetTaskCount:
    """任务计数。"""

    @pytest.mark.asyncio
    async def test_count_all_in_project(self):
        board = TaskBoard()
        for i in range(3):
            await board.create_task("proj-1", f"任务{i}")
        assert board.get_task_count(project_id="proj-1") == 3

    @pytest.mark.asyncio
    async def test_count_by_status(self):
        board = TaskBoard()
        await board.create_task("proj-1", "任务")
        assert board.get_task_count(TaskStatus.BACKLOG, "proj-1") == 1
        assert board.get_task_count(TaskStatus.DONE, "proj-1") == 0

    @pytest.mark.asyncio
    async def test_count_all_projects(self):
        board = TaskBoard()
        await board.create_task("proj-1", "任务1")
        await board.create_task("proj-2", "任务2")
        assert board.get_task_count() == 2


class TestSearchTasks:
    """搜索任务。"""

    @pytest.mark.asyncio
    async def test_search_by_title(self):
        board = TaskBoard()
        await board.create_task("proj-1", "修复登录Bug")
        await board.create_task("proj-1", "添加注册功能")
        results = board.search_tasks("登录", "proj-1")
        assert len(results) == 1
        assert "登录" in results[0].title

    @pytest.mark.asyncio
    async def test_search_by_description(self):
        board = TaskBoard()
        await board.create_task("proj-1", "任务A", description="需要修改数据库schema")
        results = board.search_tasks("数据库", "proj-1")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self):
        board = TaskBoard()
        await board.create_task("proj-1", "LOGIN BUG")
        results = board.search_tasks("login", "proj-1")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_no_match(self):
        board = TaskBoard()
        await board.create_task("proj-1", "任务")
        assert board.search_tasks("不存在的关键词", "proj-1") == []

    @pytest.mark.asyncio
    async def test_search_all_projects(self):
        board = TaskBoard()
        await board.create_task("proj-1", "登录Bug")
        await board.create_task("proj-2", "登录优化")
        assert len(board.search_tasks("登录")) == 2


class TestHandlers:
    """事件处理器注册和通知。"""

    @pytest.mark.asyncio
    async def test_register_and_notify(self):
        board = TaskBoard()
        events = []

        def handler(task_id, event, task):
            events.append((event, task.title))

        board.register_handler("created", handler)
        await board.create_task("proj-1", "测试任务")
        assert ("created", "测试任务") in events

    @pytest.mark.asyncio
    async def test_unregister_handler(self):
        board = TaskBoard()
        events = []

        def handler(task_id, event, task):
            events.append(event)

        board.register_handler("status_changed", handler)
        board.unregister_handler("status_changed", handler)
        task = await board.create_task("proj-1", "任务")
        await board.change_status(task.id, TaskStatus.TODO)
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_handler_exception_swallowed(self):
        board = TaskBoard()
        good_called = []

        def bad_handler(task_id, event, task):
            raise RuntimeError("boom")

        def good_handler(task_id, event, task):
            good_called.append(True)

        board.register_handler("created", bad_handler)
        board.register_handler("created", good_handler)
        await board.create_task("proj-1", "任务")
        assert len(good_called) == 1

    @pytest.mark.asyncio
    async def test_multiple_events(self):
        board = TaskBoard()
        created_events = []
        updated_events = []

        board.register_handler("created", lambda tid, ev, t: created_events.append(ev))
        board.register_handler("updated", lambda tid, ev, t: updated_events.append(ev))

        task = await board.create_task("proj-1", "任务")
        await board.update_task(task.id, "proj-1", title="更新")

        assert len(created_events) == 1
        assert "updated" in updated_events


class TestClearAll:
    """清空。"""

    @pytest.mark.asyncio
    async def test_clear_all(self):
        board = TaskBoard()
        for i in range(3):
            await board.create_task("proj-1", f"任务{i}")
        board.clear_all()
        assert board.get_task_count() == 0

    @pytest.mark.asyncio
    async def test_clear_project_tasks(self):
        board = TaskBoard()
        await board.create_task("proj-1", "任务1")
        await board.create_task("proj-2", "任务2")
        await board.clear_project_tasks("proj-1")
        assert board.get_task_count(project_id="proj-1") == 0
        assert board.get_task_count(project_id="proj-2") == 1
