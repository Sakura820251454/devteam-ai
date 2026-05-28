"""Pipeline 持久化层集成测试。

使用 SQLite 内存数据库测试 save / load / delete CRUD，
以及服务重启后 RUNNING→FAILED 自动修复和 paused 列兼容。
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base
from app.services.collaboration.pipeline_orchestrator import PipelineStatus
from app.services.persistence.pipeline_persistence import (
    PipelinePersistenceService,
    _model_from_pipeline,
)
from tests.factories import PipelineFactory


class TestPipelinePersistence:
    """Pipeline 持久化 CRUD。"""

    @pytest_asyncio.fixture
    async def persistence(self):
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        svc = PipelinePersistenceService()
        svc.initialize(session_factory)
        yield svc
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_save_new_pipeline(self, persistence):
        """新建 pipeline 应能保存并加载。"""
        p = PipelineFactory.idle(id="p-save-001", project_id="proj-001", name="测试保存")
        await persistence.save(p)

        all_pipelines = await persistence.load_all()
        assert "p-save-001" in all_pipelines
        loaded = all_pipelines["p-save-001"]
        assert loaded.name == "测试保存"
        assert loaded.status == PipelineStatus.IDLE

    @pytest.mark.asyncio
    async def test_save_update_existing_pipeline(self, persistence):
        """更新已存在的 pipeline。"""
        p = PipelineFactory.running(id="p-update-001", project_id="proj-001", name="原始名称")
        await persistence.save(p)

        p.name = "更新后名称"
        p.status = PipelineStatus.PAUSED
        await persistence.save(p)

        all_pipelines = await persistence.load_all()
        loaded = all_pipelines["p-update-001"]
        assert loaded.name == "更新后名称"
        assert loaded.status == PipelineStatus.PAUSED

    @pytest.mark.asyncio
    async def test_save_preserves_agents(self, persistence):
        """Agent 列表应完整保留。"""
        p = PipelineFactory.create(
            id="p-agents-001",
            project_id="proj-001",
            name="Agent测试",
            agents=["agent-1", "agent-2", "agent-3"],
        )
        await persistence.save(p)

        all_pipelines = await persistence.load_all()
        loaded = all_pipelines["p-agents-001"]
        assert loaded.agents == ["agent-1", "agent-2", "agent-3"]

    @pytest.mark.asyncio
    async def test_save_preserves_stages(self, persistence):
        """阶段列表应完整保留。"""
        stages = [
            {"key": "collect", "label": "收集"},
            {"key": "analyze", "label": "分析"},
        ]
        p = PipelineFactory.create(id="p-stages-001", project_id="proj-001", name="阶段测试", stages=stages)
        await persistence.save(p)

        all_pipelines = await persistence.load_all()
        loaded = all_pipelines["p-stages-001"]
        assert loaded.stages == stages

    @pytest.mark.asyncio
    async def test_delete_pipeline(self, persistence):
        """删除 pipeline 后不应能加载。"""
        p = PipelineFactory.idle(id="p-del-001", project_id="proj-001")
        await persistence.save(p)
        assert "p-del-001" in await persistence.load_all()

        await persistence.delete("p-del-001")
        assert "p-del-001" not in await persistence.load_all()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_does_not_error(self, persistence):
        """删除不存在的 pipeline 不应报错。"""
        await persistence.delete("no-such-pipeline")

    @pytest.mark.asyncio
    async def test_delete_by_project(self, persistence):
        """按 project_id 批量删除。"""
        p1 = PipelineFactory.idle(id="p-batch-001", project_id="proj-batch")
        p2 = PipelineFactory.idle(id="p-batch-002", project_id="proj-batch")
        p3 = PipelineFactory.idle(id="p-batch-003", project_id="proj-other")
        for p in [p1, p2, p3]:
            await persistence.save(p)

        await persistence.delete_by_project("proj-batch")

        remaining = await persistence.load_all()
        assert "p-batch-001" not in remaining
        assert "p-batch-002" not in remaining
        assert "p-batch-003" in remaining  # 不同项目不受影响


class TestRestartRecovery:
    """服务重启后的数据修复。"""

    @pytest_asyncio.fixture
    async def persistence(self):
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        svc = PipelinePersistenceService()
        svc.initialize(session_factory)
        yield svc
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_running_pipeline_marked_failed_on_load(self, persistence):
        """服务重启时 RUNNING 状态的 pipeline 自动标记为 FAILED。"""
        p = PipelineFactory.running(id="p-running-001", project_id="proj-001", name="运行中")
        await persistence.save(p)

        # load_all 应自动将 RUNNING 转为 FAILED（asyncio task 已丢失）
        all_pipelines = await persistence.load_all()
        loaded = all_pipelines["p-running-001"]
        assert loaded.status == PipelineStatus.FAILED

    @pytest.mark.asyncio
    async def test_paused_pipeline_preserved_on_load(self, persistence):
        """PAUSED 状态的 pipeline 重启后保持 PAUSED。"""
        p = PipelineFactory.paused(id="p-paused-001", project_id="proj-001", name="已暂停")
        await persistence.save(p)

        all_pipelines = await persistence.load_all()
        loaded = all_pipelines["p-paused-001"]
        assert loaded.status == PipelineStatus.PAUSED

    @pytest.mark.asyncio
    async def test_paused_flag_consistent_with_status(self, persistence):
        """保存 PAUSED pipeline 后，DB 中 paused 列应为 True。"""
        p = PipelineFactory.paused(id="p-flag-001", project_id="proj-001", name="暂停标检")
        await persistence.save(p)

        # 直接查 DB 模型
        from app.models.core_db import PipelineModel
        async with await persistence._get_session() as db:
            model = await db.get(PipelineModel, "p-flag-001")
            assert model is not None
            assert model.paused is True
            assert model.status == "paused"

    @pytest.mark.asyncio
    async def test_running_pipeline_paused_flag_false(self, persistence):
        """保存 RUNNING pipeline 后，DB 中 paused 列应为 False。"""
        p = PipelineFactory.running(id="p-flag-002", project_id="proj-001", name="运行标检")
        await persistence.save(p)

        from app.models.core_db import PipelineModel
        async with await persistence._get_session() as db:
            model = await db.get(PipelineModel, "p-flag-002")
            assert model is not None
            assert model.paused is False
            assert model.status == "running"


class TestLogTruncation:
    """日志截断测试。"""

    @pytest_asyncio.fixture
    async def persistence(self):
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        svc = PipelinePersistenceService()
        svc.initialize(session_factory)
        yield svc
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_logs_truncated_at_1000(self, persistence):
        """超过 1000 条日志时自动截断。"""
        p = PipelineFactory.idle(id="p-log-001", project_id="proj-001", name="日志测试")
        for i in range(1500):
            p.add_log("test", f"日志 {i}")

        await persistence.save(p)

        all_pipelines = await persistence.load_all()
        loaded = all_pipelines["p-log-001"]
        assert len(loaded.logs) == 1000
        # 应保留最新的 1000 条
        assert loaded.logs[0]["message"] == "日志 500"
        assert loaded.logs[-1]["message"] == "日志 1499"

    @pytest.mark.asyncio
    async def test_logs_under_1000_kept_intact(self, persistence):
        """少于 1000 条日志时完整保留。"""
        p = PipelineFactory.idle(id="p-log-002", project_id="proj-001", name="少量日志")
        p.add_log("test", "只有一条")

        await persistence.save(p)

        all_pipelines = await persistence.load_all()
        loaded = all_pipelines["p-log-002"]
        assert len(loaded.logs) == 1
