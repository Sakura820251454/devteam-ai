"""任务分析服务 — Step 2: 分析任务领域、类型、复杂度"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import List

from app.core.llm import Message as LLMMessage
from app.services.shared.prompt_registry import registry

logger = logging.getLogger(__name__)


@dataclass
class TaskAnalysis:
    domain: str
    task_type: str
    sub_types: List[str] = field(default_factory=list)
    complexity: str = "中"
    breakdown: List[str] = field(default_factory=list)
    key_challenge: str = ""
    analysis_summary: str = ""


class TaskAnalyzer:
    """LLM 任务分析器"""

    async def analyze(self, task_description: str) -> TaskAnalysis:
        prompt = registry.render("task.analyze", {"task_description": task_description})

        try:
            from app.services.llm.llm_service import llm_service

            response = await asyncio.wait_for(
                llm_service.chat(
                    messages=[
                        LLMMessage(
                            role="system",
                            content=registry.render("task.analyze_system", {}),
                        ),
                        LLMMessage(role="user", content=prompt),
                    ],
                    track_cost=False,
                    timeout=45.0,
                ),
                timeout=55.0,
            )

            return self._parse_analysis(response.content)
        except Exception as e:
            logger.warning(f"Task analysis failed: {e}")
            return TaskAnalysis(
                domain="其他领域",
                task_type="探索研究型",
                complexity="中",
                analysis_summary=f"分析失败 ({e})，使用默认分析结果",
            )

    def _parse_analysis(self, text: str) -> TaskAnalysis:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return TaskAnalysis(
                domain="其他领域",
                task_type="探索研究型",
                breakdown=[],
                analysis_summary="无法解析分析结果",
            )

        try:
            data = json.loads(match.group())
        except json.JSONDecodeError:
            return TaskAnalysis(
                domain="其他领域",
                task_type="探索研究型",
                breakdown=[],
                analysis_summary="JSON解析失败",
            )

        return TaskAnalysis(
            domain=data.get("domain", "其他领域"),
            task_type=data.get("task_type", "探索研究型"),
            sub_types=data.get("sub_types", []),
            complexity=data.get("complexity", "中"),
            breakdown=data.get("breakdown", []),
            key_challenge=data.get("key_challenge", ""),
            analysis_summary=data.get("analysis_summary", ""),
        )


task_analyzer = TaskAnalyzer()
