import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


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
    ) -> Dict[str, Any]:
        ws_dir = self._workspace_dir(project_id)
        ws_dir.mkdir(parents=True, exist_ok=True)

        for subdir in ["docs", "src", "logs"]:
            (ws_dir / subdir).mkdir(exist_ok=True)

        artifacts_dir = ws_dir / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)
        for stage_key in self.STAGE_KEYS:
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

    def delete_workspace(self, project_id: str) -> bool:
        import shutil
        ws_dir = self._workspace_dir(project_id)
        if not ws_dir.exists():
            return False
        shutil.rmtree(ws_dir)
        return True

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
