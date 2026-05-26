"""任务分析 API — Step 2"""

import dataclasses

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.task.task_analyzer import task_analyzer

router = APIRouter(prefix="/api/task-analysis", tags=["任务分析"])


class AnalyzeTaskRequest(BaseModel):
    task_description: str


@router.post("/")
async def analyze_task(request: AnalyzeTaskRequest):
    analysis = await task_analyzer.analyze(request.task_description)
    return dataclasses.asdict(analysis)
