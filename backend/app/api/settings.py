import json
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/settings", tags=["系统设置"])

SETTINGS_FILE = Path(__file__).parent.parent.parent / "data" / "settings.json"


def _get_default_workspace_root() -> str:
    from app.core.config import get_settings
    return get_settings().workspace_root


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    default_root = _get_default_workspace_root()
    return {"workspace_root": default_root}


def save_settings(data: dict) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_workspace_root() -> str:
    settings = load_settings()
    root = settings.get("workspace_root", _get_default_workspace_root())
    if not Path(root).is_absolute():
        root = str((Path(__file__).parent.parent.parent / root).resolve())
    return root


class UpdateSettingsRequest(BaseModel):
    workspace_root: str


@router.get("/")
def get_settings():
    from app.core.config import get_settings as get_core_settings
    settings = load_settings()
    root = settings.get("workspace_root", _get_default_workspace_root())
    resolved = root
    if not Path(root).is_absolute():
        resolved = str((Path(__file__).parent.parent.parent / root).resolve())
    return {
        "workspace_root": root,
        "workspace_root_resolved": resolved,
        "llm_mode": get_core_settings().llm_mode.value,
    }


@router.patch("/")
def update_settings(request: UpdateSettingsRequest):
    settings = load_settings()
    settings["workspace_root"] = request.workspace_root
    save_settings(settings)

    root = request.workspace_root
    resolved = root
    if not Path(root).is_absolute():
        resolved = str((Path(__file__).parent.parent.parent / root).resolve())
    return {
        "workspace_root": root,
        "workspace_root_resolved": resolved,
    }
