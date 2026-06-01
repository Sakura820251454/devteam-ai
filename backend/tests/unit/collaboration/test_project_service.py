"""ProjectService 单元测试 — 项目生命周期管理。

覆盖 create / get / update / list / delete / summary / advance_phase。
"""
import pytest
from app.services.collaboration.project_service import (
    ProjectService, ProjectStatus, ProjectPhase,
)


class TestCreateProject:
    """创建项目。"""

    @pytest.mark.asyncio
    async def test_create_basic(self):
        svc = ProjectService()
        proj = await svc.create_project("测试项目", "项目描述")
        assert proj.name == "测试项目"
        assert proj.description == "项目描述"
        assert proj.status == ProjectStatus.PLANNING
        assert proj.current_phase == ProjectPhase.REQUIREMENT
        assert proj.created_by == "user"

    @pytest.mark.asyncio
    async def test_create_with_full_fields(self):
        svc = ProjectService()
        proj = await svc.create_project(
            "完整项目", "详细描述",
            requirements="需要支持多语言",
            created_by="admin",
            team_config={"agents": 3},
        )
        assert proj.requirements == "需要支持多语言"
        assert proj.created_by == "admin"
        assert proj.team_config == {"agents": 3}

    @pytest.mark.asyncio
    async def test_create_returns_unique_ids(self):
        svc = ProjectService()
        p1 = await svc.create_project("项目1")
        p2 = await svc.create_project("项目2")
        assert p1.id != p2.id


class TestGetProject:
    """获取项目。"""

    @pytest.mark.asyncio
    async def test_get_existing(self):
        svc = ProjectService()
        proj = await svc.create_project("项目A")
        found = svc.get_project(proj.id)
        assert found is not None
        assert found.name == "项目A"

    def test_get_nonexistent(self):
        svc = ProjectService()
        assert svc.get_project("no-such-id") is None


class TestUpdateProject:
    """更新项目。"""

    @pytest.mark.asyncio
    async def test_update_name(self):
        svc = ProjectService()
        proj = await svc.create_project("旧名称")
        updated = await svc.update_project(proj.id, name="新名称")
        assert updated is not None
        assert updated.name == "新名称"

    @pytest.mark.asyncio
    async def test_update_status(self):
        svc = ProjectService()
        proj = await svc.create_project("项目")
        updated = await svc.update_project(proj.id, status="in_progress")
        assert updated.status == ProjectStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_update_phase(self):
        svc = ProjectService()
        proj = await svc.create_project("项目")
        updated = await svc.update_project(proj.id, current_phase="development")
        assert updated.current_phase == ProjectPhase.DEVELOPMENT

    @pytest.mark.asyncio
    async def test_update_requirements(self):
        svc = ProjectService()
        proj = await svc.create_project("项目")
        updated = await svc.update_project(proj.id, requirements="新需求")
        assert updated.requirements == "新需求"

    @pytest.mark.asyncio
    async def test_update_partial(self):
        """只更新部分字段，其他字段保持不变。"""
        svc = ProjectService()
        proj = await svc.create_project("项目", description="原始描述")
        updated = await svc.update_project(proj.id, name="新名称")
        assert updated.name == "新名称"
        assert updated.description == "原始描述"  # 未变

    @pytest.mark.asyncio
    async def test_update_nonexistent(self):
        svc = ProjectService()
        result = await svc.update_project("ghost", name="x")
        assert result is None


class TestListProjects:
    """列表查询。"""

    @pytest.mark.asyncio
    async def test_list_all(self):
        svc = ProjectService()
        await svc.create_project("项目1")
        await svc.create_project("项目2")
        projects = svc.list_projects()
        assert len(projects) == 2

    @pytest.mark.asyncio
    async def test_filter_by_status(self):
        svc = ProjectService()
        p1 = await svc.create_project("活跃项目")
        p2 = await svc.create_project("已完成项目")
        await svc.update_project(p2.id, status="completed")

        active = svc.list_projects(status=ProjectStatus.PLANNING)
        completed = svc.list_projects(status=ProjectStatus.COMPLETED)
        assert len(active) == 1
        assert len(completed) == 1

    @pytest.mark.asyncio
    async def test_sorted_by_updated_at(self):
        """应按更新时间倒序排列。"""
        svc = ProjectService()
        p1 = await svc.create_project("旧项目")
        p2 = await svc.create_project("新项目")
        await svc.update_project(p1.id, name="旧项目-已更新")
        projects = svc.list_projects()
        assert projects[0].name == "旧项目-已更新"  # 刚更新的排前面


class TestDeleteProject:
    """删除项目。"""

    @pytest.mark.asyncio
    async def test_delete_existing(self):
        svc = ProjectService()
        proj = await svc.create_project("要删除的项目")
        assert svc.get_project(proj.id) is not None
        result = await svc.delete_project(proj.id, cascade=False)
        assert result is True
        assert svc.get_project(proj.id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self):
        svc = ProjectService()
        result = await svc.delete_project("ghost")
        assert result is False


class TestAdvancePhase:
    """阶段推进。"""

    @pytest.mark.asyncio
    async def test_advance_requirement_to_design(self):
        svc = ProjectService()
        proj = await svc.create_project("项目")
        assert proj.current_phase == ProjectPhase.REQUIREMENT

        await svc.advance_phase(proj.id)
        proj = svc.get_project(proj.id)
        assert proj.current_phase == ProjectPhase.DESIGN

    @pytest.mark.asyncio
    async def test_advance_to_last_phase(self):
        """推进到 DEPLOYMENT 后不应再推进。"""
        svc = ProjectService()
        proj = await svc.create_project("项目")
        for _ in range(4):  # REQUIREMENT → DESIGN → DEVELOPMENT → TESTING → DEPLOYMENT
            await svc.advance_phase(proj.id)
        proj = svc.get_project(proj.id)
        assert proj.current_phase == ProjectPhase.DEPLOYMENT

        # 再推进应保持在 DEPLOYMENT
        await svc.advance_phase(proj.id)
        proj = svc.get_project(proj.id)
        assert proj.current_phase == ProjectPhase.DEPLOYMENT

    @pytest.mark.asyncio
    async def test_advance_nonexistent(self):
        svc = ProjectService()
        result = await svc.advance_phase("ghost")
        assert result is None


class TestTaskBreakdownPrompt:
    """任务拆解 Prompt 存取。"""

    def test_set_and_get(self):
        svc = ProjectService()
        svc.set_task_breakdown_prompt("proj-1", "自定义 prompt 内容")
        assert svc.get_task_breakdown_prompt("proj-1") == "自定义 prompt 内容"

    def test_get_not_set(self):
        svc = ProjectService()
        assert svc.get_task_breakdown_prompt("no-project") is None
