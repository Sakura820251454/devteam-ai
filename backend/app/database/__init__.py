from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


async def get_db():
    """获取数据库会话"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """初始化数据库，创建所有表"""
    from app.models.memory_db import MemoryEntryModel, AgentContextModel, TrajectoryModel, SkillModel, AgentSkillModel
    from app.models.gear_db import GearModel  # noqa: F401
    from app.models.execution_db import TaskExecutionModel, TaskCheckpointModel  # noqa: F401
    from app.models.core_db import ProjectModel, TaskModel, PipelineModel, SessionModel, MessageModel  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
