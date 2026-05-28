"""工作区管理器单元测试。

测试项目工作区的创建、文件管理、artifact 操作。
使用临时文件系统，不依赖真实项目数据。
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.project.workspace_manager import WorkspaceManager


@pytest.fixture
def temp_root():
    """临时工作区根目录。"""
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture
def ws_manager(temp_root):
    """创建指向临时目录的 WorkspaceManager。"""
    with patch(
        "app.services.project.workspace_manager._get_workspace_root",
        return_value=Path(temp_root),
    ):
        yield WorkspaceManager()


# ========== 工作区创建 ==========


class TestCreateWorkspace:
    """create_workspace 测试。"""

    def test_create_basic_workspace(self, ws_manager):
        data = ws_manager.create_workspace(
            project_id="proj-001",
            name="测试项目",
            description="一个测试项目",
        )
        assert data["id"] == "proj-001"
        assert data["name"] == "测试项目"
        assert data["status"] == "running"
        assert "created_at" in data

    def test_create_workspace_creates_directories(self, ws_manager, temp_root):
        ws_manager.create_workspace(project_id="proj-002", name="项目2")
        ws_dir = Path(temp_root) / "proj-002"
        assert ws_dir.exists()
        assert (ws_dir / "docs").exists()
        assert (ws_dir / "src").exists()
        assert (ws_dir / "logs").exists()
        assert (ws_dir / "artifacts").exists()

    def test_create_workspace_with_custom_stages(self, ws_manager, temp_root):
        ws_manager.create_workspace(
            project_id="proj-003",
            name="项目3",
            stages=[
                {"key": "collect", "label": "收集"},
                {"key": "analyze", "label": "分析"},
            ],
        )
        assert (Path(temp_root) / "proj-003" / "artifacts" / "collect").exists()
        assert (Path(temp_root) / "proj-003" / "artifacts" / "analyze").exists()

    def test_create_workspace_writes_project_json(self, ws_manager, temp_root):
        ws_manager.create_workspace(project_id="proj-004", name="项目4", agents=[
            {"id": "agent-1", "name": "小王"}
        ])
        project_file = Path(temp_root) / "proj-004" / "project.json"
        assert project_file.exists()
        with open(project_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["name"] == "项目4"
        assert data["agents"][0]["name"] == "小王"

    def test_create_workspace_writes_initial_log(self, ws_manager, temp_root):
        ws_manager.create_workspace(project_id="proj-005", name="项目5")
        log_file = Path(temp_root) / "proj-005" / "logs" / "project.log"
        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "Project created: 项目5" in content

    def test_create_workspace_idempotent(self, ws_manager):
        """重复创建同一项目不应报错。"""
        ws_manager.create_workspace(project_id="proj-dup", name="首次")
        # 第二次调用不抛出异常
        data = ws_manager.create_workspace(project_id="proj-dup", name="覆盖")
        assert data["name"] == "覆盖"


# ========== 工作区查询 ==========


class TestGetWorkspace:
    """get_workspace / list_workspaces 测试。"""

    def test_get_existing_workspace(self, ws_manager):
        ws_manager.create_workspace(project_id="proj-g1", name="项目G1")
        ws = ws_manager.get_workspace("proj-g1")
        assert ws is not None
        assert ws["name"] == "项目G1"
        assert "workspace_path" in ws
        assert "files" in ws

    def test_get_nonexistent_workspace(self, ws_manager):
        assert ws_manager.get_workspace("no-such-project") is None

    def test_list_workspaces(self, ws_manager):
        ws_manager.create_workspace(project_id="proj-l1", name="项目L1")
        ws_manager.create_workspace(project_id="proj-l2", name="项目L2")
        workspaces = ws_manager.list_workspaces()
        assert len(workspaces) == 2
        names = {w["name"] for w in workspaces}
        assert "项目L1" in names
        assert "项目L2" in names

    def test_list_workspaces_empty(self, ws_manager):
        workspaces = ws_manager.list_workspaces()
        assert workspaces == []


# ========== Artifact 管理 ==========


class TestArtifact:
    """add_artifact / list_files / read_file 测试。"""

    def test_add_artifact(self, ws_manager, temp_root):
        ws_manager.create_workspace(project_id="proj-a1", name="A1", stages=[
            {"key": "coding", "label": "开发"}
        ])
        path = ws_manager.add_artifact("proj-a1", "coding", "main.py", "print('hello')")
        assert path is not None
        assert "main.py" in path

        # 验证文件内容
        actual = (Path(temp_root) / "proj-a1" / "artifacts" / "coding" / "main.py").read_text()
        assert actual == "print('hello')"

    def test_add_artifact_nonexistent_project(self, ws_manager):
        result = ws_manager.add_artifact("no-proj", "stage", "file.txt", "content")
        assert result is None

    def test_add_artifact_sanitizes_filename(self, ws_manager):
        ws_manager.create_workspace(project_id="proj-a2", name="A2")
        path = ws_manager.add_artifact("proj-a2", "coding", "path/to/malicious.py", "safe")
        # "/" 和 "\\" 应被替换
        filename = Path(path).name
        assert "/" not in filename
        assert "\\" not in filename

    def test_list_files(self, ws_manager):
        ws_manager.create_workspace(project_id="proj-f1", name="F1")
        ws_manager.add_artifact("proj-f1", "coding", "a.py", "a")
        ws_manager.add_artifact("proj-f1", "coding", "b.py", "b")

        files = ws_manager.list_files("proj-f1")
        file_names = {f["name"] for f in files}
        assert "artifacts" in file_names  # artifacts 目录
        assert "docs" in file_names
        assert "src" in file_names

    def test_list_files_subdir(self, ws_manager):
        ws_manager.create_workspace(project_id="proj-f2", name="F2")
        ws_manager.add_artifact("proj-f2", "coding", "main.py", "code")

        files = ws_manager.list_files("proj-f2", subdir="artifacts/coding")
        assert len(files) == 1
        assert files[0]["name"] == "main.py"
        assert files[0]["type"] == "file"

    def test_read_file(self, ws_manager):
        ws_manager.create_workspace(project_id="proj-r1", name="R1")
        ws_manager.add_artifact("proj-r1", "docs", "readme.md", "# 项目说明")

        content = ws_manager.read_file("proj-r1", "artifacts/docs/readme.md")
        assert content == "# 项目说明"

    def test_read_file_not_found(self, ws_manager):
        ws_manager.create_workspace(project_id="proj-r2", name="R2")
        assert ws_manager.read_file("proj-r2", "no/such/file.txt") is None

    def test_list_files_nonexistent_project(self, ws_manager):
        assert ws_manager.list_files("no-proj") == []


# ========== 日志 ==========


class TestLogging:
    """add_log / update_status 测试。"""

    def test_add_log(self, ws_manager, temp_root):
        ws_manager.create_workspace(project_id="proj-log1", name="Log1")
        ws_manager.add_log("proj-log1", "info", "pipeline", "任务开始执行")

        log_file = Path(temp_root) / "proj-log1" / "logs" / "project.log"
        content = log_file.read_text(encoding="utf-8")
        assert "[INFO]" in content
        assert "[pipeline]" in content
        assert "任务开始执行" in content

    def test_add_log_nonexistent_project(self, ws_manager):
        """不存在的项目写入日志不应报错。"""
        ws_manager.add_log("no-proj", "error", "test", "msg")

    def test_update_status(self, ws_manager, temp_root):
        ws_manager.create_workspace(project_id="proj-st1", name="Status1")
        result = ws_manager.update_status("proj-st1", "completed", current_stage="review")
        assert result is True

        # 验证 project.json 已更新
        with open(Path(temp_root) / "proj-st1" / "project.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["status"] == "completed"
        assert data["current_stage"] == "review"

    def test_update_status_nonexistent_project(self, ws_manager):
        assert ws_manager.update_status("no-proj", "running") is False

    def test_update_stages(self, ws_manager, temp_root):
        ws_manager.create_workspace(project_id="proj-st2", name="Stages1")
        new_stages = [{"key": "s1", "label": "阶段一"}]
        result = ws_manager.update_stages("proj-st2", new_stages)
        assert result is True

        with open(Path(temp_root) / "proj-st2" / "project.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["stages"] == new_stages

    def test_update_stages_nonexistent_project(self, ws_manager):
        assert ws_manager.update_stages("no-proj", []) is False


# ========== STAGE_KEYS ==========


class TestStageKeys:
    """内置阶段 key 列表。"""

    def test_stage_keys_not_empty(self):
        assert len(WorkspaceManager.STAGE_KEYS) >= 4

    def test_stage_keys_all_strings(self):
        for key in WorkspaceManager.STAGE_KEYS:
            assert isinstance(key, str)
            assert len(key) > 0
