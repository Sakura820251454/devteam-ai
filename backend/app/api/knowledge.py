"""
知识进化模块API - Phase 5.4

提供知识资产管理的REST接口，实现设计文档3.6节的知识进化功能
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.knowledge.knowledge_evolution import (
    knowledge_evolution_service,
    KnowledgeAsset,
    ExplicitKnowledge,
    ImplicitKnowledge,
    KnowledgeType,
    KnowledgeConfidence,
    ExplicitKnowledgeType,
    ImplicitKnowledgeType,
    DiscoveredPattern,
    SkillFromKnowledge,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/discover")
async def discover_knowledge(
    content: str,
    agent_id: str,
    task_type: str = Query(default=""),
):
    """从讨论内容中提取知识"""
    knowledge_ids = knowledge_evolution_service.extract_and_save(
        content, agent_id, task_type
    )
    
    return {
        "message": f"成功提取{len(knowledge_ids)}条知识",
        "knowledge_ids": knowledge_ids,
        "total_knowledge": knowledge_evolution_service.get_knowledge_stats()["total_knowledge"],
    }


@router.post("/success-case")
async def record_success_case(
    task_description: str,
    context: str,
    method: str,
    effect: str,
    success_factors: List[str],
    agent_id: str,
    task_type: str = Query(default=""),
):
    """记录成功案例"""
    knowledge = knowledge_evolution_service.extractor.extract_success_case(
        task_description,
        context,
        method,
        effect,
        success_factors,
        agent_id,
        task_type,
    )
    
    knowledge_evolution_service.add_knowledge(knowledge)
    
    return {
        "message": "成功案例已记录",
        "knowledge": _knowledge_to_dict(knowledge),
    }


@router.post("/failure-lesson")
async def record_failure_lesson(
    task_description: str,
    problem: str,
    failed_attempts: List[str],
    final_solution: str,
    prevention_tips: List[str],
    agent_id: str,
    task_type: str = Query(default=""),
):
    """记录失败教训"""
    knowledge = knowledge_evolution_service.extractor.extract_failure_lesson(
        task_description,
        problem,
        failed_attempts,
        final_solution,
        prevention_tips,
        agent_id,
        task_type,
    )
    
    knowledge_evolution_service.add_knowledge(knowledge)
    
    return {
        "message": "失败教训已记录",
        "knowledge": _knowledge_to_dict(knowledge),
    }


@router.post("/code-snippet")
async def add_code_snippet(
    code: str,
    description: str,
    language: str,
    use_case: str,
    agent_id: str,
):
    """添加代码片段"""
    knowledge = knowledge_evolution_service.extractor.extract_code_snippet(
        code, description, language, use_case, agent_id
    )
    
    knowledge_evolution_service.add_knowledge(knowledge)
    
    return {
        "message": "代码片段已保存",
        "knowledge": _knowledge_to_dict(knowledge),
    }


@router.get("/search")
async def search_knowledge(
    query: str,
    knowledge_type: Optional[str] = Query(None),
    min_confidence: Optional[str] = Query(None),
    limit: int = Query(default=10),
):
    """搜索知识资产"""
    k_type = KnowledgeType(knowledge_type) if knowledge_type else None
    m_confidence = KnowledgeConfidence(min_confidence) if min_confidence else None
    
    results = knowledge_evolution_service.search_knowledge(
        query, k_type, m_confidence, limit
    )
    
    return {
        "query": query,
        "results": [
            {
                "knowledge": _knowledge_to_dict(k),
                "relevance": r,
            }
            for k, r in results
        ],
        "count": len(results),
    }


@router.get("/{knowledge_id}")
async def get_knowledge(knowledge_id: str):
    """获取知识资产详情"""
    knowledge = knowledge_evolution_service.get_knowledge(knowledge_id)
    
    if not knowledge:
        raise HTTPException(status_code=404, detail="知识资产不存在")
    
    return _knowledge_to_dict(knowledge)


@router.post("/{knowledge_id}/use")
async def use_knowledge(knowledge_id: str, success: bool = Query(default=True)):
    """标记知识资产的使用情况"""
    knowledge = knowledge_evolution_service.get_knowledge(knowledge_id)
    
    if not knowledge:
        raise HTTPException(status_code=404, detail="知识资产不存在")
    
    knowledge.use(success)
    
    return {
        "message": "使用记录已更新",
        "success_rate": knowledge.success_rate,
        "usage_count": knowledge.usage_count,
    }


@router.post("/patterns/discover")
async def discover_patterns(task_history: List[Dict[str, Any]]):
    """从历史数据中发现模式"""
    count = knowledge_evolution_service.discover_and_save_patterns(task_history)
    
    return {
        "message": f"发现{count}个新模式",
        "total_patterns": len(knowledge_evolution_service.patterns),
    }


@router.get("/patterns")
async def get_patterns():
    """获取所有发现的模式"""
    patterns = knowledge_evolution_service.patterns
    
    return {
        "patterns": [_pattern_to_dict(p) for p in patterns],
        "count": len(patterns),
    }


@router.post("/skills/generate")
async def generate_skills(agent_id: str):
    """从成功案例生成技能"""
    skills = knowledge_evolution_service.generate_skills(agent_id)
    
    return {
        "message": f"成功生成{len(skills)}个技能",
        "skills": [_skill_to_dict(s) for s in skills],
    }


@router.get("/skills")
async def get_skills():
    """获取所有生成的技能"""
    skills = list(knowledge_evolution_service.generated_skills.values())
    
    return {
        "skills": [_skill_to_dict(s) for s in skills],
        "count": len(skills),
    }


@router.get("/stats")
async def get_knowledge_stats():
    """获取知识库统计"""
    return knowledge_evolution_service.get_knowledge_stats()


def _knowledge_to_dict(knowledge: KnowledgeAsset) -> Dict[str, Any]:
    """知识资产转字典"""
    base = {
        "id": knowledge.id,
        "title": knowledge.title,
        "content": knowledge.content,
        "knowledge_type": knowledge.knowledge_type.value,
        "confidence": knowledge.confidence.value,
        "usage_count": knowledge.usage_count,
        "success_rate": knowledge.success_rate,
        "tags": knowledge.tags,
        "created_at": knowledge.created_at,
        "created_by": knowledge.created_by,
        "related_task_types": knowledge.related_task_types,
        "source": knowledge.source,
    }
    
    if isinstance(knowledge, ExplicitKnowledge):
        base.update({
            "explicit_type": knowledge.explicit_type.value,
            "domain": knowledge.domain,
            "tech_stack": knowledge.tech_stack,
            "code_language": knowledge.code_language,
            "metadata": knowledge.metadata,
        })
    elif isinstance(knowledge, ImplicitKnowledge):
        base.update({
            "implicit_type": knowledge.implicit_type.value,
            "context": knowledge.context,
            "method": knowledge.method,
            "effect": knowledge.effect,
            "success_factors": knowledge.success_factors,
            "failure_factors": knowledge.failure_factors,
            "prevention_tips": knowledge.prevention_tips,
        })
    
    return base


def _pattern_to_dict(pattern: DiscoveredPattern) -> Dict[str, Any]:
    """模式转字典"""
    return {
        "id": pattern.id,
        "name": pattern.name,
        "description": pattern.description,
        "pattern_type": pattern.pattern_type,
        "evidence_count": pattern.evidence_count,
        "confidence": pattern.confidence,
        "discovered_at": pattern.discovered_at,
        "related_knowledge_ids": pattern.related_knowledge_ids,
    }


def _skill_to_dict(skill: SkillFromKnowledge) -> Dict[str, Any]:
    """技能转字典"""
    return {
        "id": skill.id,
        "name": skill.name,
        "description": skill.description,
        "source_knowledge_id": skill.source_knowledge_id,
        "process_steps": skill.process_steps,
        "checklist": skill.checklist,
        "template": skill.template,
        "generated_at": skill.generated_at,
    }
