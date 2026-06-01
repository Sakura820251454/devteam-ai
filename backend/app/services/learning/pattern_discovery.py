"""
模式发现服务 - 从多个任务执行数据中自动发现模式

模式类型：
- 成功特征：成功任务的共同因素（至少 3 个成功案例）
- 陷阱模式：失败任务的共同原因（至少 2 个失败案例）
- 协作模式：高效协作的共同特征（至少 5 个任务）
- 技术栈模式：项目中频繁使用的技术（至少 3 个代码片段）
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredPattern:
    """发现的模式"""
    id: str
    pattern_type: str  # success_factor / pitfall / collaboration / tech_stack
    title: str
    description: str
    evidence_count: int
    confidence: float  # 0.0 - 1.0
    examples: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class PatternDiscovery:
    """模式发现引擎"""

    # 置信度阈值
    MIN_EVIDENCE = {
        "success_factor": 3,
        "pitfall": 2,
        "collaboration": 5,
        "tech_stack": 3,
    }

    async def discover_patterns(
        self,
        trajectories: List[Dict[str, Any]],
    ) -> List[DiscoveredPattern]:
        """
        从多个轨迹中发现模式。

        Args:
            trajectories: 轨迹数据列表，每条包含:
                - task: 任务描述
                - status: success/failure
                - agent_id: Agent ID
                - decisions: 决策列表
                - error: 错误信息（如有）

        Returns:
            发现的模式列表
        """
        if len(trajectories) < 2:
            return []

        # 分类轨迹
        successes = [t for t in trajectories if t.get("status") == "success"]
        failures = [t for t in trajectories if t.get("status") == "failure"]

        patterns = []

        # 1. 成功特征
        if len(successes) >= self.MIN_EVIDENCE["success_factor"]:
            success_patterns = await self._find_success_patterns(successes)
            patterns.extend(success_patterns)

        # 2. 陷阱模式
        if len(failures) >= self.MIN_EVIDENCE["pitfall"]:
            pitfall_patterns = await self._find_pitfall_patterns(failures)
            patterns.extend(pitfall_patterns)

        # 3. 协作模式
        if len(trajectories) >= self.MIN_EVIDENCE["collaboration"]:
            collab_patterns = await self._find_collaboration_patterns(trajectories)
            patterns.extend(collab_patterns)

        # 4. 技术栈模式
        tech_patterns = await self._find_tech_stack_patterns(trajectories)
        patterns.extend(tech_patterns)

        return patterns

    async def _find_success_patterns(
        self, successes: List[Dict[str, Any]]
    ) -> List[DiscoveredPattern]:
        """发现成功任务的共同因素"""
        try:
            from app.services.llm.llm_service import llm_service
            from app.core.llm import Message as LLMMessage

            summaries = []
            for t in successes[:10]:
                decisions = t.get("decisions", [])
                decision_text = "; ".join(d.get("action", "")[:80] for d in decisions[:3])
                summaries.append(f"- {t.get('task', '')[:100]} | 决策: {decision_text}")

            prompt = (
                "分析以下成功任务，找出共同的成功因素。\n\n"
                f"成功任务 ({len(successes)} 个):\n" + "\n".join(summaries) + "\n\n"
                "请输出 JSON 格式:\n"
                '{"patterns": [{"title": "模式标题", "description": "描述", '
                '"evidence": ["证据1", "证据2"]}]}'
            )

            messages = [LLMMessage(role="user", content=prompt)]
            resp = await llm_service.chat(messages, temperature=0.3, max_tokens=600)

            import json
            result = json.loads(resp.content.strip())
            patterns = []
            for i, p in enumerate(result.get("patterns", [])):
                patterns.append(DiscoveredPattern(
                    id=f"success_{i}",
                    pattern_type="success_factor",
                    title=p.get("title", ""),
                    description=p.get("description", ""),
                    evidence_count=len(p.get("evidence", [])),
                    confidence=min(1.0, len(p.get("evidence", [])) / 5),
                    examples=p.get("evidence", []),
                ))
            return patterns

        except Exception as e:
            logger.warning("发现成功模式失败: %s", e)
            return []

    async def _find_pitfall_patterns(
        self, failures: List[Dict[str, Any]]
    ) -> List[DiscoveredPattern]:
        """发现失败任务的共同原因"""
        try:
            from app.services.llm.llm_service import llm_service
            from app.core.llm import Message as LLMMessage

            summaries = []
            for t in failures[:10]:
                error = t.get("error", "")[:150]
                summaries.append(f"- {t.get('task', '')[:100]} | 错误: {error}")

            prompt = (
                "分析以下失败任务，找出共同的失败原因和陷阱。\n\n"
                f"失败任务 ({len(failures)} 个):\n" + "\n".join(summaries) + "\n\n"
                "请输出 JSON 格式:\n"
                '{"patterns": [{"title": "陷阱标题", "description": "描述", '
                '"evidence": ["证据1", "证据2"]}]}'
            )

            messages = [LLMMessage(role="user", content=prompt)]
            resp = await llm_service.chat(messages, temperature=0.3, max_tokens=600)

            import json
            result = json.loads(resp.content.strip())
            patterns = []
            for i, p in enumerate(result.get("patterns", [])):
                patterns.append(DiscoveredPattern(
                    id=f"pitfall_{i}",
                    pattern_type="pitfall",
                    title=p.get("title", ""),
                    description=p.get("description", ""),
                    evidence_count=len(p.get("evidence", [])),
                    confidence=min(1.0, len(p.get("evidence", [])) / 4),
                    examples=p.get("evidence", []),
                ))
            return patterns

        except Exception as e:
            logger.warning("发现陷阱模式失败: %s", e)
            return []

    async def _find_collaboration_patterns(
        self, trajectories: List[Dict[str, Any]]
    ) -> List[DiscoveredPattern]:
        """发现高效协作的共同特征"""
        try:
            from app.services.llm.llm_service import llm_service
            from app.core.llm import Message as LLMMessage

            # 统计 Agent 参与情况
            agent_counts: Dict[str, int] = {}
            for t in trajectories:
                aid = t.get("agent_id", "unknown")
                agent_counts[aid] = agent_counts.get(aid, 0) + 1

            agent_summary = ", ".join(f"{aid}({cnt}次)" for aid, cnt in agent_counts.items())

            prompt = (
                "分析以下任务执行数据，发现协作模式。\n\n"
                f"总任务数: {len(trajectories)}\n"
                f"Agent 参与: {agent_summary}\n\n"
                "请输出 JSON 格式:\n"
                '{"patterns": [{"title": "协作模式标题", "description": "描述"}]}'
            )

            messages = [LLMMessage(role="user", content=prompt)]
            resp = await llm_service.chat(messages, temperature=0.3, max_tokens=400)

            import json
            result = json.loads(resp.content.strip())
            patterns = []
            for i, p in enumerate(result.get("patterns", [])):
                patterns.append(DiscoveredPattern(
                    id=f"collab_{i}",
                    pattern_type="collaboration",
                    title=p.get("title", ""),
                    description=p.get("description", ""),
                    evidence_count=len(trajectories),
                    confidence=min(1.0, len(trajectories) / 10),
                ))
            return patterns

        except Exception as e:
            logger.warning("发现协作模式失败: %s", e)
            return []

    async def _find_tech_stack_patterns(
        self, trajectories: List[Dict[str, Any]]
    ) -> List[DiscoveredPattern]:
        """发现频繁使用的技术栈"""
        # 从任务描述和决策中提取技术关键词
        tech_keywords: Dict[str, int] = {}
        tech_terms = [
            "python", "javascript", "typescript", "react", "vue", "fastapi",
            "flask", "django", "postgresql", "mysql", "redis", "docker",
            "kubernetes", "aws", "api", "rest", "graphql", "grpc",
            "pytest", "jest", "unittest", "ci/cd", "git", "sql",
            "html", "css", "tailwind", "webpack", "vite",
        ]

        for t in trajectories:
            text = (t.get("task", "") + " " + str(t.get("decisions", ""))).lower()
            for term in tech_terms:
                if term in text:
                    tech_keywords[term] = tech_keywords.get(term, 0) + 1

        patterns = []
        for term, count in sorted(tech_keywords.items(), key=lambda x: -x[1]):
            if count >= self.MIN_EVIDENCE["tech_stack"]:
                patterns.append(DiscoveredPattern(
                    id=f"tech_{term}",
                    pattern_type="tech_stack",
                    title=f"频繁使用: {term}",
                    description=f"在 {count}/{len(trajectories)} 个任务中使用了 {term}",
                    evidence_count=count,
                    confidence=min(1.0, count / len(trajectories)) if trajectories else 0,
                ))

        return patterns[:5]  # 最多返回 5 个


pattern_discovery = PatternDiscovery()
