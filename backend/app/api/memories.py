from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from app.database import get_db
from app.services.memory.persistent_memory_manager import PersistentMemoryManager
from app.models.agent_context import MemoryLevel

router = APIRouter(prefix="/memories", tags=["记忆管理"])


class AddMemoryRequest(BaseModel):
    agent_id: str = Field(..., description="Agent ID")
    content: str = Field(..., description="记忆内容")
    level: str = Field(default=MemoryLevel.WORKING, description="记忆层级")
    tags: List[str] = Field(default_factory=list, description="标签")
    source: Optional[str] = Field(default=None, description="来源")
    session_id: Optional[str] = Field(default=None, description="会话 ID")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")


class UpdateMemoryRequest(BaseModel):
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    relevance_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class CreateContextRequest(BaseModel):
    agent_id: str
    role: str
    system_prompt: str = ""
    personality: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None


class MemoryResponse(BaseModel):
    id: str
    content: str
    level: str
    tags: List[str]
    relevance_score: float
    created_at: str
    last_accessed_at: str


class StatisticsResponse(BaseModel):
    working: int
    short_term: int
    long_term: int
    total: int


@router.post("/", response_model=MemoryResponse)
async def add_memory(
    request: AddMemoryRequest,
    db: AsyncSession = Depends(get_db)
):
    """添加记忆"""
    manager = PersistentMemoryManager(db)
    entry = await manager.add_memory(
        agent_id=request.agent_id,
        content=request.content,
        level=request.level,
        tags=request.tags,
        source=request.source,
        session_id=request.session_id,
        metadata=request.metadata
    )
    
    return MemoryResponse(
        id=entry.id,
        content=entry.content,
        level=entry.level,
        tags=entry.tags,
        relevance_score=entry.relevance_score,
        created_at=entry.created_at.isoformat(),
        last_accessed_at=entry.last_accessed_at.isoformat()
    )


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取记忆"""
    manager = PersistentMemoryManager(db)
    entry = await manager.get_memory(memory_id)
    
    if not entry:
        raise HTTPException(status_code=404, detail="记忆不存在")
    
    return MemoryResponse(
        id=entry.id,
        content=entry.content,
        level=entry.level,
        tags=entry.tags,
        relevance_score=entry.relevance_score,
        created_at=entry.created_at.isoformat(),
        last_accessed_at=entry.last_accessed_at.isoformat()
    )


@router.get("/agent/{agent_id}", response_model=List[MemoryResponse])
async def get_agent_memories(
    agent_id: str,
    level: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """获取 Agent 的所有记忆"""
    manager = PersistentMemoryManager(db)
    entries = await manager.get_agent_memories(
        agent_id=agent_id,
        level=level,
        limit=limit,
        offset=offset
    )
    
    return [
        MemoryResponse(
            id=entry.id,
            content=entry.content,
            level=entry.level,
            tags=entry.tags,
            relevance_score=entry.relevance_score,
            created_at=entry.created_at.isoformat(),
            last_accessed_at=entry.last_accessed_at.isoformat()
        )
        for entry in entries
    ]


class RetrieveMemoryRequest(BaseModel):
    agent_id: str
    search_query: str
    level: Optional[str] = None
    max_results: int = 10
    use_semantic: bool = True


@router.post("/retrieve", response_model=List[MemoryResponse])
async def retrieve_memory(
    request: RetrieveMemoryRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """检索相关记忆 (支持语义检索)"""
    manager = PersistentMemoryManager(db)
    entries = await manager.retrieve_memory(
        agent_id=request.agent_id,
        query=request.search_query,
        level=request.level,
        max_results=request.max_results,
        use_semantic=request.use_semantic
    )
    
    return [
        MemoryResponse(
            id=entry.id,
            content=entry.content,
            level=entry.level,
            tags=entry.tags,
            relevance_score=entry.relevance_score,
            created_at=entry.created_at.isoformat(),
            last_accessed_at=entry.last_accessed_at.isoformat()
        )
        for entry in entries
    ]


@router.put("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: str,
    request: UpdateMemoryRequest,
    db: AsyncSession = Depends(get_db)
):
    """更新记忆"""
    manager = PersistentMemoryManager(db)
    entry = await manager.update_memory(
        memory_id=memory_id,
        content=request.content,
        tags=request.tags,
        relevance_score=request.relevance_score,
        metadata=request.metadata
    )
    
    if not entry:
        raise HTTPException(status_code=404, detail="记忆不存在")
    
    return MemoryResponse(
        id=entry.id,
        content=entry.content,
        level=entry.level,
        tags=entry.tags,
        relevance_score=entry.relevance_score,
        created_at=entry.created_at.isoformat(),
        last_accessed_at=entry.last_accessed_at.isoformat()
    )


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    db: AsyncSession = Depends(get_db)
):
    """删除记忆"""
    manager = PersistentMemoryManager(db)
    success = await manager.delete_memory(memory_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="记忆不存在")
    
    return {"message": "记忆已删除"}


@router.post("/promote/{memory_id}", response_model=MemoryResponse)
async def promote_memory(
    memory_id: str,
    to_level: str,
    db: AsyncSession = Depends(get_db)
):
    """提升记忆到更高层级"""
    manager = PersistentMemoryManager(db)
    entry = await manager.promote_memory(memory_id, to_level)
    
    if not entry:
        raise HTTPException(status_code=404, detail="记忆不存在")
    
    return MemoryResponse(
        id=entry.id,
        content=entry.content,
        level=entry.level,
        tags=entry.tags,
        relevance_score=entry.relevance_score,
        created_at=entry.created_at.isoformat(),
        last_accessed_at=entry.last_accessed_at.isoformat()
    )


@router.get("/context/{agent_id}/prompt")
async def get_context_prompt(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取 Agent 的上下文提示词"""
    manager = PersistentMemoryManager(db)
    prompt = await manager.get_context_prompt(agent_id)
    
    return {"prompt": prompt}


@router.post("/context", response_model=dict)
async def create_or_update_context(
    request: CreateContextRequest,
    db: AsyncSession = Depends(get_db)
):
    """创建或更新 Agent 上下文"""
    manager = PersistentMemoryManager(db)
    context = await manager.create_or_update_context(
        agent_id=request.agent_id,
        role=request.role,
        system_prompt=request.system_prompt,
        personality=request.personality,
        session_id=request.session_id
    )
    
    return {"message": "上下文已创建/更新", "agent_id": context.agent_id}


@router.get("/agent/{agent_id}/statistics", response_model=StatisticsResponse)
async def get_statistics(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取 Agent 的记忆统计"""
    manager = PersistentMemoryManager(db)
    stats = await manager.get_statistics(agent_id)
    
    return StatisticsResponse(**stats)


# ===== 高级记忆管理 API =====

@router.post("/agent/{agent_id}/refresh-scores")
async def refresh_memory_scores(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
):
    """刷新记忆分数并触发自动晋升"""
    manager = PersistentMemoryManager(db)
    stats = await manager.refresh_memory_scores(agent_id)
    
    return {
        "agent_id": agent_id,
        "statistics": stats,
        "message": "记忆分数已刷新"
    }


@router.post("/agent/{agent_id}/deduplicate")
async def deduplicate_memories(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
):
    """去重并合并重复记忆"""
    manager = PersistentMemoryManager(db)
    result = await manager.deduplicate_memories(agent_id)
    
    return {
        "agent_id": agent_id,
        "result": result,
        "message": f"完成去重，合并 {result['merged_count']} 条记忆"
    }


@router.get("/quality/{memory_id}")
async def get_memory_quality(
    memory_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取记忆质量评分"""
    manager = PersistentMemoryManager(db)
    quality = await manager.get_memory_quality(memory_id)
    
    if not quality:
        raise HTTPException(status_code=404, detail="记忆不存在")
    
    return quality


@router.get("/agent/{agent_id}/sensitive")
async def get_sensitive_memories(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取标记为敏感的记忆"""
    manager = PersistentMemoryManager(db)
    sensitive = await manager.get_sensitive_memories(agent_id)
    
    return {
        "agent_id": agent_id,
        "count": len(sensitive),
        "memories": sensitive
    }


@router.post("/export")
async def export_memories(
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """导出记忆数据"""
    agent_id = request.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=400, detail="缺少 agent_id")
    
    manager = PersistentMemoryManager(db)
    memories = await manager.get_agent_memories(agent_id)
    
    exported = [
        {
            "id": m.id,
            "content": m.content,
            "level": m.level,
            "tags": m.tags or [],
            "relevance_score": m.relevance_score,
            "usage_count": m.usage_count,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "last_accessed_at": m.last_accessed_at.isoformat() if m.last_accessed_at else None,
        }
        for m in memories
    ]
    
    return {
        "agent_id": agent_id,
        "count": len(exported),
        "memories": exported
    }


# ===== 遗忘管理 API =====

@router.post("/agent/{agent_id}/forget-plan")
async def get_forget_plan(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取遗忘计划"""
    manager = PersistentMemoryManager(db)
    plan = await manager.get_forget_plan(agent_id)
    
    return plan


@router.post("/agent/{agent_id}/auto-forget")
async def auto_forget(
    agent_id: str,
    dry_run: bool = Query(default=False),
    db: AsyncSession = Depends(get_db)
):
    """
    自动遗忘低质量或过期记忆
    
    Args:
        dry_run: True=只返回计划不删除，False=执行遗忘
    """
    manager = PersistentMemoryManager(db)
    result = await manager.auto_forget(agent_id, dry_run)
    
    if dry_run:
        return {
            "agent_id": agent_id,
            "dry_run": True,
            "message": "这是遗忘计划预览，实际执行请设置 dry_run=False",
            "result": result,
        }
    
    return {
        "agent_id": agent_id,
        "message": f"已遗忘 {result['total_forgotten']} 条记忆",
        "result": result,
    }


@router.post("/agent/{agent_id}/capacity-check")
async def check_capacity(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
):
    """检查记忆容量状态"""
    manager = PersistentMemoryManager(db)
    capacity = await manager.check_capacity(agent_id)
    
    return {
        "agent_id": agent_id,
        "capacity": capacity,
        "recommendations": _generate_capacity_recommendations(capacity),
    }


def _generate_capacity_recommendations(capacity: Dict) -> List[str]:
    """生成容量建议"""
    recommendations = []
    
    if capacity.get("total_exceeded"):
        recommendations.append(f"总记忆数超过限制，建议遗忘 {capacity['total'] - 500} 条记忆")
    
    for level, exceeded in capacity.get("level_exceeded", {}).items():
        if exceeded:
            recommendations.append(f"{level} 层记忆超过 {capacity['by_level'].get(level, 0)} 条限制")
    
    if not recommendations:
        recommendations.append("容量状态良好")
    
    return recommendations


# ===== 上下文压缩 API =====

@router.post("/agent/{agent_id}/compress")
async def compress_context(
    agent_id: str,
    max_tokens: int = Query(default=4096),
    strategy: str = Query(default="auto"),
    db: AsyncSession = Depends(get_db)
):
    """
    压缩Agent上下文记忆
    
    Args:
        max_tokens: 最大token数
        strategy: 压缩策略 (auto/summary/importance/token_limit/merge_adjacent/truncate)
    """
    manager = PersistentMemoryManager(db)
    result = await manager.compress_context(agent_id, max_tokens, strategy)
    
    return {
        "agent_id": agent_id,
        "message": f"压缩完成，压缩率: {result['compression_ratio']:.2%}",
        "result": result,
    }


@router.get("/agent/{agent_id}/compressed-prompt")
async def get_compressed_prompt(
    agent_id: str,
    max_tokens: int = Query(default=4096),
    db: AsyncSession = Depends(get_db)
):
    """获取压缩后的上下文提示词"""
    manager = PersistentMemoryManager(db)
    prompt = await manager.get_compressed_context_prompt(agent_id, max_tokens)
    
    return {
        "agent_id": agent_id,
        "prompt": prompt,
        "token_estimate": len(prompt) // 4,
    }
