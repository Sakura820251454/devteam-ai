import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


def _get_workspace_root() -> Path:
    from app.api.settings import get_workspace_root as get_persisted_root
    root = Path(get_persisted_root())
    if not root.is_absolute():
        root = Path(__file__).parent.parent.parent.parent / root
    return root.resolve()


class WorkspaceManager:
    """Manages project workspace directories on disk."""

    STAGE_KEYS = [
        "requirement_analysis",
        "task_breakdown",
        "coding",
        "review",
        "testing",
        "delivery",
    ]

    def _workspace_dir(self, project_id: str) -> Path:
        return _get_workspace_root() / project_id

    def create_workspace(
        self,
        project_id: str,
        name: str,
        description: str = "",
        agents: Optional[List[Dict[str, Any]]] = None,
        stages: Optional[List[Dict[str, Any]]] = None,
        team_config: Optional[Dict[str, Any]] = None,
        template: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ws_dir = self._workspace_dir(project_id)
        ws_dir.mkdir(parents=True, exist_ok=True)

        for subdir in ["docs", "src", "logs"]:
            (ws_dir / subdir).mkdir(exist_ok=True)

        # Use template stage keys for artifact directories, or fallback to default
        stage_keys = [s["key"] for s in (stages or [])] if stages else self.STAGE_KEYS

        artifacts_dir = ws_dir / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)
        for stage_key in stage_keys:
            (artifacts_dir / stage_key).mkdir(exist_ok=True)

        project_data = {
            "id": project_id,
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "running",
            "agents": agents or [],
            "stages": stages or [],
            "team_config": team_config,
            "template": template,
        }

        with open(ws_dir / "project.json", "w", encoding="utf-8") as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)

        with open(ws_dir / "logs" / "project.log", "w", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] Project created: {name}\n")

        return project_data

    def get_workspace(self, project_id: str) -> Optional[Dict[str, Any]]:
        ws_dir = self._workspace_dir(project_id)
        project_file = ws_dir / "project.json"
        if not project_file.exists():
            return None

        with open(project_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["files"] = self._build_file_tree(ws_dir)
        data["workspace_path"] = str(ws_dir)
        return data

    def list_workspaces(self) -> List[Dict[str, Any]]:
        root = _get_workspace_root()
        if not root.exists():
            return []

        workspaces = []
        for ws_dir in sorted(root.iterdir(), reverse=True):
            if not ws_dir.is_dir():
                continue
            project_file = ws_dir / "project.json"
            if project_file.exists():
                with open(project_file, "r", encoding="utf-8") as f:
                    workspaces.append(json.load(f))
        return workspaces

    def add_artifact(
        self, project_id: str, stage_key: str, name: str, content: str
    ) -> Optional[str]:
        ws_dir = self._workspace_dir(project_id)
        if not ws_dir.exists():
            return None

        artifact_dir = ws_dir / "artifacts" / stage_key
        artifact_dir.mkdir(parents=True, exist_ok=True)

        safe_name = name.replace("/", "_").replace("\\", "_")
        file_path = artifact_dir / safe_name

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)

    def list_files(self, project_id: str, subdir: str = "") -> List[Dict[str, Any]]:
        ws_dir = self._workspace_dir(project_id)
        if not ws_dir.exists():
            return []

        target = ws_dir / subdir if subdir else ws_dir
        if not target.exists():
            return []

        files = []
        for entry in sorted(target.iterdir()):
            if entry.name == "project.json" and not subdir:
                continue
            files.append({
                "name": entry.name,
                "path": str(entry.relative_to(ws_dir)),
                "type": "directory" if entry.is_dir() else "file",
                "size": entry.stat().st_size if entry.is_file() else 0,
                "modified_at": datetime.fromtimestamp(entry.stat().st_mtime).isoformat(),
            })
        return files

    def read_file(self, project_id: str, file_path: str) -> Optional[str]:
        ws_dir = self._workspace_dir(project_id)
        target = ws_dir / file_path
        if not target.exists() or not target.is_file():
            return None
        with open(target, "r", encoding="utf-8") as f:
            return f.read()

    def add_log(self, project_id: str, level: str, source: str, message: str) -> None:
        ws_dir = self._workspace_dir(project_id)
        if not ws_dir.exists():
            return

        log_dir = ws_dir / "logs"
        log_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().isoformat()
        with open(log_dir / "project.log", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{level.upper()}] [{source}] {message}\n")

    def update_status(self, project_id: str, status: str, current_stage: str = "") -> bool:
        ws_dir = self._workspace_dir(project_id)
        project_file = ws_dir / "project.json"
        if not project_file.exists():
            return False

        with open(project_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["status"] = status
        data["updated_at"] = datetime.now().isoformat()
        if current_stage:
            data["current_stage"] = current_stage

        with open(project_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True

    def update_stages(self, project_id: str, stages: List[Dict[str, Any]]) -> bool:
        """Update stages in project.json. Returns True on success."""
        ws_dir = self._workspace_dir(project_id)
        project_file = ws_dir / "project.json"
        if not project_file.exists():
            return False

        with open(project_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["stages"] = stages
        data["updated_at"] = datetime.now().isoformat()

        with open(project_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True

    def delete_workspace(self, project_id: str) -> bool:
        ws_dir = self._workspace_dir(project_id)
        if not ws_dir.exists():
            return False
        shutil.rmtree(ws_dir)
        return True

    # ========== Artifact 管理 ==========

    def get_artifact_status(self, project_id: str, stages: List[dict]) -> Dict[str, Any]:
        """获取各阶段的产出物状态"""
        ws_dir = self._workspace_dir(project_id)
        artifact_dir = ws_dir / "artifacts"

        stage_status = {}
        for stage in stages:
            stage_key = stage.get("key", stage.get("label", ""))
            expected = stage.get("expected_artifact", "")
            stage_dir = artifact_dir / stage_key

            files = []
            if stage_dir.exists():
                for f in sorted(stage_dir.iterdir()):
                    files.append({
                        "name": f.name,
                        "size": f.stat().st_size if f.is_file() else 0,
                        "modified_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    })

            stage_status[stage_key] = {
                "label": stage.get("label", stage_key),
                "expected_artifact": expected,
                "has_artifacts": len(files) > 0,
                "files": files,
            }

        return {
            "project_id": project_id,
            "stages": stage_status,
        }

    def get_prerequisite_artifacts(
        self, project_id: str, current_stage_key: str, stage_order: List[str],
    ) -> Dict[str, Any]:
        """获取前置阶段的产出物内容（用于可执行反馈）"""
        ws_dir = self._workspace_dir(project_id)
        artifact_dir = ws_dir / "artifacts"

        try:
            current_idx = stage_order.index(current_stage_key)
            prerequisite_keys = stage_order[:current_idx]
        except ValueError:
            prerequisite_keys = stage_order

        artifacts = {}
        for stage_key in prerequisite_keys:
            stage_dir = artifact_dir / stage_key
            if stage_dir.exists():
                files = {}
                for f in sorted(stage_dir.iterdir()):
                    if f.is_file():
                        try:
                            with open(f, "r", encoding="utf-8") as fh:
                                files[f.name] = fh.read()[:5000]  # 截断到5000字符
                        except Exception:
                            files[f.name] = "[binary or unreadable]"
                if files:
                    artifacts[stage_key] = files

        return artifacts

    def assemble_artifacts_to_src(self, project_id: str) -> List[str]:
        """将所有 artifacts 目录中的文件复制到 src/ 目录。
        返回相对于 workspace 根目录的已组装文件路径列表。"""
        ws_dir = self._workspace_dir(project_id)
        artifact_dir = ws_dir / "artifacts"
        src_dir = ws_dir / "src"
        if not artifact_dir.exists():
            return []
        src_dir.mkdir(parents=True, exist_ok=True)

        assembled = []
        for stage_dir in sorted(artifact_dir.iterdir()):
            if not stage_dir.is_dir():
                continue
            for f in stage_dir.iterdir():
                if not f.is_file():
                    continue
                # 用阶段名做前缀避免文件名冲突
                dest_name = f"{stage_dir.name}_{f.name}"
                dest_path = src_dir / dest_name
                try:
                    shutil.copy2(f, dest_path)
                    assembled.append(str(dest_path.relative_to(ws_dir)))
                except Exception as e:
                    logger.warning(f"Failed to copy {f} to src/: {e}")

        return assembled

    def list_artifact_files(self, project_id: str) -> List[Dict[str, str]]:
        """递归列出 artifacts 目录下所有文件。
        返回 [{"name": 文件名, "path": 相对路径, "stage": 阶段名}, ...]"""
        ws_dir = self._workspace_dir(project_id)
        artifact_dir = ws_dir / "artifacts"
        if not artifact_dir.exists():
            return []

        files = []
        for stage_dir in sorted(artifact_dir.iterdir()):
            if not stage_dir.is_dir():
                continue
            for f in sorted(stage_dir.iterdir()):
                if not f.is_file():
                    continue
                files.append({
                    "name": f.name,
                    "path": str(f.relative_to(ws_dir)),
                    "stage": stage_dir.name,
                })
        return files

    def _build_file_tree(self, ws_dir: Path) -> List[Dict[str, Any]]:
        files = []
        for entry in sorted(ws_dir.iterdir()):
            if entry.name == "project.json":
                continue
            if entry.is_dir():
                children = []
                for child in sorted(entry.iterdir()):
                    children.append({
                        "name": child.name,
                        "path": str(child.relative_to(ws_dir)),
                        "type": "directory" if child.is_dir() else "file",
                        "size": child.stat().st_size if child.is_file() else 0,
                    })
                files.append({
                    "name": entry.name,
                    "path": str(entry.relative_to(ws_dir)),
                    "type": "directory",
                    "children": children,
                })
        return files


workspace_manager = WorkspaceManager()
