"""
冲突仲裁系统

当多个 Agent 对同一问题给出不同结论时，自动触发仲裁流程：
1. 检测冲突：识别 Agent 间的观点分歧
2. 投票轮次：各 Agent 阐述理由并投票
3. 元 Agent 裁决：由架构师或 Guardian 做出最终决定
4. 记录决议：仲裁结果写入任务历史
"""

import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field

from app.core.llm import Message as LLMMessage
from app.services.collaboration.message_bus import message_bus, Message, MessageType


class ArbitrationStatus(str, Enum):
    PENDING = "pending"
    VOTING = "voting"
    RESOLVED = "resolved"
    DEADLOCKED = "deadlocked"  # 无法裁决，升级人工


class VoteType(str, Enum):
    AGREE = "agree"
    DISAGREE = "disagree"
    ABSTAIN = "abstain"


@dataclass
class ArbitrationIssue:
    """仲裁议题"""
    id: str
    task_id: str
    title: str
    description: str
    proposals: List[Dict[str, str]]  # [{agent_id, agent_name, position, reasoning}]
    status: ArbitrationStatus = ArbitrationStatus.PENDING
    votes: Dict[str, VoteType] = field(default_factory=dict)  # agent_id -> vote
    resolution: Optional[str] = None
    resolved_by: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    resolved_at: Optional[str] = None


class ConflictArbitrator:
    """
    冲突仲裁器

    触发条件：
    - 多个 Agent 对同一任务产生不同结论
    - Pipeline Review 阶段发现结果矛盾
    - 手动触发仲裁

    流程：
    1. 创建仲裁议题 → 通知相关 Agent
    2. 各 Agent 投票并阐述理由
    3. 统计投票 → 多数决 / 元 Agent 裁决
    4. 记录最终决议
    """

    def __init__(self):
        self._issues: Dict[str, ArbitrationIssue] = {}
        self._lock = asyncio.Lock()
        # 仲裁者优先级：架构师 > PM > 第一个参与的 Agent
        self._arbitrator_priority = ["architect", "product_manager"]

    async def detect_conflict(
        self,
        task_id: str,
        agent_results: List[Dict[str, Any]]
    ) -> Optional[ArbitrationIssue]:
        """
        检测是否存在冲突

        agent_results: [{agent_id, agent_name, conclusion, confidence}]
        当两个以上 Agent 的结论存在实质性分歧时，创建仲裁议题
        """
        if len(agent_results) < 2:
            return None

        # 简单冲突检测：结论字符串的编辑距离
        conclusions = [r.get("conclusion", "") for r in agent_results if r.get("conclusion")]
        if len(conclusions) < 2:
            return None

        # 如果所有结论都一致（完全匹配），无需仲裁
        unique_conclusions = set(conclusions)
        if len(unique_conclusions) <= 1:
            return None

        # 创建仲裁议题
        issue = ArbitrationIssue(
            id=f"arb_{uuid.uuid4().hex[:8]}",
            task_id=task_id,
            title=f"任务 {task_id} 的结论冲突",
            description=f"发现 {len(unique_conclusions)} 种不同的结论，需要仲裁",
            proposals=[
                {
                    "agent_id": r["agent_id"],
                    "agent_name": r.get("agent_name", "Unknown"),
                    "position": r.get("conclusion", ""),
                    "reasoning": r.get("reasoning", "无详细理由"),
                }
                for r in agent_results
            ]
        )

        async with self._lock:
            self._issues[issue.id] = issue

        return issue

    async def start_arbitration(self, issue_id: str) -> ArbitrationIssue:
        """启动仲裁流程"""
        async with self._lock:
            issue = self._issues.get(issue_id)
            if not issue:
                raise ValueError(f"Arbitration issue not found: {issue_id}")

            issue.status = ArbitrationStatus.VOTING

            # 通知所有相关 Agent
            agent_names = [p["agent_name"] for p in issue.proposals]
            msg = Message(
                sender_id="arbitrator",
                sender_name="Arbitrator",
                channel=f"task:{issue.task_id}",
                content=f"⚖️ 仲裁开始: {issue.title}\n"
                       f"参与方: {', '.join(agent_names)}\n"
                       f"请各方阐述观点并投票",
                message_type=MessageType.SYSTEM
            )
            await message_bus.send_to_task(msg, issue.task_id)

        return issue

    async def cast_vote(
        self,
        issue_id: str,
        agent_id: str,
        vote: VoteType,
        reasoning: str = ""
    ) -> Dict[str, Any]:
        """Agent 投票"""
        async with self._lock:
            issue = self._issues.get(issue_id)
            if not issue:
                raise ValueError(f"Arbitration issue not found: {issue_id}")

            if issue.status != ArbitrationStatus.VOTING:
                return {"error": "仲裁不在投票阶段"}

            issue.votes[agent_id] = vote

            # 检查是否可以结束投票
            total_agents = len(issue.proposals)
            votes_cast = len(issue.votes)

            if votes_cast >= total_agents:
                return await self._resolve(issue)

        return {
            "issue_id": issue_id,
            "agent_id": agent_id,
            "vote": vote.value,
            "votes_cast": votes_cast,
            "total_agents": total_agents,
            "status": "voting"
        }

    async def _resolve(self, issue: ArbitrationIssue) -> Dict[str, Any]:
        """裁决冲突"""
        # 统计投票
        agree_count = sum(1 for v in issue.votes.values() if v == VoteType.AGREE)
        disagree_count = sum(1 for v in issue.votes.values() if v == VoteType.DISAGREE)
        abstain_count = sum(1 for v in issue.votes.values() if v == VoteType.ABSTAIN)

        if agree_count > disagree_count:
            # 多数同意
            issue.resolution = "多数Agent同意当前方案，予以通过"
            issue.status = ArbitrationStatus.RESOLVED
            issue.resolved_by = "majority_vote"
        elif disagree_count > agree_count:
            # 多数反对 → 调用元 Agent 裁决
            resolution = await self._meta_agent_resolve(issue)
            issue.resolution = resolution
            issue.status = ArbitrationStatus.RESOLVED
            issue.resolved_by = "meta_agent"
        else:
            # 平局 → 升级人工
            issue.status = ArbitrationStatus.DEADLOCKED
            issue.resolution = "投票平局，需要人工裁决"

        issue.resolved_at = datetime.now().isoformat()

        # 通知结果
        msg = Message(
            sender_id="arbitrator",
            sender_name="Arbitrator",
            channel=f"task:{issue.task_id}",
            content=f"⚖️ 仲裁结果: {issue.resolution}\n"
                   f"同意: {agree_count} | 反对: {disagree_count} | 弃权: {abstain_count}",
            message_type=MessageType.SYSTEM
        )
        await message_bus.send_to_task(msg, issue.task_id)

        return {
            "issue_id": issue.id,
            "status": issue.status.value,
            "resolution": issue.resolution,
            "resolved_by": issue.resolved_by,
            "votes": {k: v.value for k, v in issue.votes.items()},
        }

    async def _meta_agent_resolve(self, issue: ArbitrationIssue) -> str:
        """元 Agent 裁决（使用 LLM 分析各方观点）"""
        from app.services.llm.llm_service import llm_service

        proposals_text = "\n".join([
            f"Agent {p['agent_name']} ({p['agent_id']}): {p['position']}\n理由: {p['reasoning']}"
            for p in issue.proposals
        ])

        votes_text = "\n".join([
            f"Agent {aid}: {v.value}" for aid, v in issue.votes.items()
        ])

        prompt = f"""你是一位首席架构师，需要对以下技术争议做出最终裁决：

议题: {issue.title}
描述: {issue.description}

各方观点:
{proposals_text}

投票情况:
{votes_text}

请分析各方观点的优劣，给出最终裁决并说明理由。
裁决应该具体明确，不能被解读为模棱两可。"""

        try:
            messages = [
                LLMMessage(role="system", content="你是一位公正的架构师裁决者，擅长分析技术争议并做出明确裁决。"),
                LLMMessage(role="user", content=prompt)
            ]
            response = await llm_service.chat(messages, track_cost=False)
            return response.content
        except Exception as e:
            return f"元Agent裁决失败: {str(e)}，建议人工裁决"

    async def escalate_to_human(self, issue_id: str) -> Dict[str, Any]:
        """将死锁的仲裁升级给人工"""
        async with self._lock:
            issue = self._issues.get(issue_id)
            if not issue:
                raise ValueError(f"Arbitration issue not found: {issue_id}")

            issue.status = ArbitrationStatus.DEADLOCKED

            # 通知人工干预队列
            from app.services.collaboration.pipeline_orchestrator import pipeline_orchestrator

            msg = Message(
                sender_id="arbitrator",
                sender_name="Arbitrator",
                content=f"🔴 仲裁死锁: {issue.title}\n需要人工裁决\n各方观点:\n" +
                       "\n".join([f"- {p['agent_name']}: {p['position']}" for p in issue.proposals]),
                message_type=MessageType.SYSTEM
            )
            await message_bus.broadcast(msg)

        return {
            "issue_id": issue_id,
            "status": ArbitrationStatus.DEADLOCKED.value,
            "message": "已升级至人工裁决",
            "proposals": issue.proposals,
            "votes": {k: v.value for k, v in issue.votes.items()},
        }

    def get_issue(self, issue_id: str) -> Optional[ArbitrationIssue]:
        return self._issues.get(issue_id)

    def list_issues(
        self,
        status: Optional[ArbitrationStatus] = None,
        task_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """列出仲裁议题"""
        issues = list(self._issues.values())
        if status:
            issues = [i for i in issues if i.status == status]
        if task_id:
            issues = [i for i in issues if i.task_id == task_id]
        return [
            {
                "id": i.id,
                "task_id": i.task_id,
                "title": i.title,
                "description": i.description,
                "status": i.status.value,
                "proposals": i.proposals,
                "votes": {k: v.value for k, v in i.votes.items()},
                "resolution": i.resolution,
                "resolved_by": i.resolved_by,
                "created_at": i.created_at,
                "resolved_at": i.resolved_at,
            }
            for i in issues
        ]

    def manually_resolve(
        self,
        issue_id: str,
        resolution: str,
        resolved_by: str
    ) -> Optional[Dict[str, Any]]:
        """人工裁决死锁议题"""
        issue = self._issues.get(issue_id)
        if not issue:
            return None

        issue.resolution = resolution
        issue.resolved_by = resolved_by
        issue.status = ArbitrationStatus.RESOLVED
        issue.resolved_at = datetime.now().isoformat()

        return {
            "issue_id": issue.id,
            "status": issue.status.value,
            "resolution": issue.resolution,
            "resolved_by": resolved_by,
        }


arbitrator = ConflictArbitrator()
