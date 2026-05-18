from app.api.agents import router as agents_router
from app.api.chat import router as chat_router
from app.api.sessions import router as sessions_router
from app.api.messages import router as messages_router
from app.api.speaking import router as speaking_router
from app.api.tasks import router as tasks_router
from app.api.projects import router as projects_router
from app.api.pipelines import router as pipelines_router
from app.api.memories import router as memories_router
from app.api.skills import router as skills_router
from app.api.equipment import router as equipment_router
from app.api.knowledge import router as knowledge_router
from app.api.llm import router as llm_router
from app.api.security import router as security_router
from app.api.arbitration import router as arbitration_router
from app.api.workspaces import router as workspaces_router
from app.api.settings import router as settings_router
from app.api.execution import router as execution_router

__all__ = [
    "agents_router",
    "chat_router",
    "sessions_router",
    "messages_router",
    "speaking_router",
    "tasks_router",
    "projects_router",
    "pipelines_router",
    "memories_router",
    "skills_router",
    "equipment_router",
    "knowledge_router",
    "llm_router",
    "security_router",
    "arbitration_router",
    "workspaces_router",
    "settings_router",
    "execution_router",
]
