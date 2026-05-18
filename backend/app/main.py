from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api import agents_router, chat_router, sessions_router, messages_router, speaking_router, tasks_router, projects_router, pipelines_router, memories_router, skills_router, equipment_router, knowledge_router, llm_router, security_router, arbitration_router, workspaces_router, settings_router, execution_router
from app.core import get_settings
from app.database import init_db, async_session_maker
from app.services.equipment.equipment_init import init_default_tools
from app.services.execution.task_persistence_service import task_persistence_service
from app.services.execution.stuck_detector import stuck_detector


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    init_default_tools()

    task_persistence_service.initialize(async_session_maker)

    await stuck_detector.start_monitoring()

    yield

    await stuck_detector.stop_monitoring()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Multi-agent collaborative development platform",
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(agents_router)
    app.include_router(chat_router)
    app.include_router(sessions_router)
    app.include_router(messages_router)
    app.include_router(speaking_router)
    app.include_router(tasks_router)
    app.include_router(projects_router)
    app.include_router(pipelines_router)
    app.include_router(memories_router)
    app.include_router(skills_router)
    app.include_router(equipment_router)
    app.include_router(knowledge_router)
    app.include_router(llm_router)
    app.include_router(security_router)
    app.include_router(arbitration_router)
    app.include_router(workspaces_router)
    app.include_router(settings_router)
    app.include_router(execution_router)

    @app.get("/")
    async def root():
        return {
            "name": settings.app_name,
            "version": "0.1.0",
            "status": "running"
        }

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
