"""
冲突仲裁 API
- 仲裁议题查询
- 投票
- 人工裁决
- 检测冲突
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from app.services.collaboration.arbitrator import (
    arbitrator,
    ArbitrationStatus,
    VoteType,
)

router = APIRouter(prefix="/api/arbitration", tags=["冲突仲裁"])


class DetectConflictRequest(BaseModel):
    task_id: str
    agent_results: List[dict]


class CastVoteRequest(BaseModel):
    agent_id: str
    vote: str  # agree, disagree, abstain
    reasoning: str = ""


class ManualResolveRequest(BaseModel):
    resolution: str
    resolved_by: str


@router.post("/detect")
async def detect_conflict(request: DetectConflictRequest):
    """检测并创建仲裁议题"""
    issue = await arbitrator.detect_conflict(
        task_id=request.task_id,
        agent_results=request.agent_results
    )
    if not issue:
        return {"conflict_detected": False, "message": "没有发现结论冲突"}
    return {
        "conflict_detected": True,
        "issue": {
            "id": issue.id,
            "task_id": issue.task_id,
            "title": issue.title,
            "proposals": issue.proposals,
            "status": issue.status.value,
        }
    }


@router.get("/issues")
async def list_issues(
    status: Optional[str] = None,
    task_id: Optional[str] = None
):
    """列出所有仲裁议题"""
    arb_status = None
    if status:
        try:
            arb_status = ArbitrationStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    issues = arbitrator.list_issues(status=arb_status, task_id=task_id)
    return {"total": len(issues), "issues": issues}


@router.get("/issues/{issue_id}")
async def get_issue(issue_id: str):
    """获取仲裁议题详情"""
    issue = arbitrator.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Arbitration issue not found")
    return {
        "id": issue.id,
        "task_id": issue.task_id,
        "title": issue.title,
        "description": issue.description,
        "status": issue.status.value,
        "proposals": issue.proposals,
        "votes": {k: v.value for k, v in issue.votes.items()},
        "resolution": issue.resolution,
        "resolved_by": issue.resolved_by,
        "created_at": issue.created_at,
        "resolved_at": issue.resolved_at,
    }


@router.post("/issues/{issue_id}/start")
async def start_arbitration(issue_id: str):
    """启动仲裁流程"""
    try:
        issue = await arbitrator.start_arbitration(issue_id)
        return {
            "issue_id": issue.id,
            "status": issue.status.value,
            "message": "仲裁已启动，等待各方投票",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/issues/{issue_id}/vote")
async def cast_vote(issue_id: str, request: CastVoteRequest):
    """对仲裁议题投票"""
    try:
        vote = VoteType(request.vote)
    except ValueError:
        raise HTTPException(status_code=400,
            detail=f"Invalid vote type: {request.vote}. Use agree/disagree/abstain")

    try:
        result = await arbitrator.cast_vote(
            issue_id=issue_id,
            agent_id=request.agent_id,
            vote=vote,
            reasoning=request.reasoning
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/issues/{issue_id}/escalate")
async def escalate_to_human(issue_id: str):
    """将死锁议题升级给人工"""
    try:
        result = await arbitrator.escalate_to_human(issue_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/issues/{issue_id}/resolve")
async def manually_resolve(issue_id: str, request: ManualResolveRequest):
    """人工裁决死锁议题"""
    result = arbitrator.manually_resolve(
        issue_id=issue_id,
        resolution=request.resolution,
        resolved_by=request.resolved_by
    )
    if not result:
        raise HTTPException(status_code=404, detail="Arbitration issue not found")
    return result
