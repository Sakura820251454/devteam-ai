"""讨论协调器 — 多 Agent 真实对话引擎。

每个 agent 使用自己的 soul.md system prompt 参与讨论，
并非模拟——每次发言都是独立的 LLM 调用，agent 用独特视角贡献。
"""

import asyncio
import json
import uuid
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple

from pydantic import BaseModel, Field

from app.core.llm import Message as LLMMessage
from app.services.shared.prompt_registry import registry

logger = logging.getLogger(__name__)


class DiscussionMode(str, Enum):
    ROUND_ROBIN = "round_robin"  # 每人每轮发言一次
    FREE = "free"  # 自由发言（当前未实现，保留）
    MODERATED = "moderated"  # 协调者决定下一个发言者（当前未实现）


class DiscussionMessage(BaseModel):
    agent_id: str
    agent_name: str
    role_label: str
    content: str
    round_number: int
    turn_number: int
    timestamp: datetime = Field(default_factory=datetime.now)


class DiscussionResult(BaseModel):
    topic: str
    concluded: bool
    consensus_reached: bool
    conclusion: Optional[str] = None
    summary: str = ""
    transcript: List[DiscussionMessage] = Field(default_factory=list)
    participant_agents: List[str] = Field(default_factory=list)
    rounds_conducted: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DiscussionOrchestrator:
    """多 Agent 多轮讨论管理器"""

    def __init__(self):
        self._active_discussions: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def conduct_discussion(
        self,
        pipeline_id: str,
        project_id: str,
        topic: str,
        context: Dict[str, Any],
        agent_ids: List[str],
        mode: DiscussionMode = DiscussionMode.ROUND_ROBIN,
        max_rounds: int = 2,
        consensus_threshold: float = 0.7,
    ) -> DiscussionResult:
        """主入口——运行一次多 Agent 讨论。

        Args:
            pipeline_id: 流水线 ID
            project_id: 项目 ID
            topic: 讨论主题
            context: 项目上下文（需求、约束等）
            agent_ids: 参与讨论的 agent ID 列表
            mode: 讨论模式
            max_rounds: 最大轮数
            consensus_threshold: 共识阈值（当前未使用）
        """
        discussion_id = f"disc_{uuid.uuid4().hex[:8]}"
        transcript: List[DiscussionMessage] = []

        # 预生成所有 agent 特质
        from app.services.agent.agent_trait_service import agent_trait_service
        await agent_trait_service.ensure_traits_batch(agent_ids)

        from app.services.agent.agent_service import agent_service
        from app.services.collaboration.message_bus import message_bus, Message, MessageType

        channel = f"discussion:{pipeline_id}"

        # 广播开场
        msg = Message(
            sender_id="discussion",
            sender_name="DiscussionOrchestrator",
            channel=channel,
            content=f"讨论开始 — 主题: {topic}",
            message_type=MessageType.SYSTEM,
            metadata={"discussion_id": discussion_id},
        )
        await message_bus.send_to_stage(msg, project_id, channel)

        consensus = False
        conclusion = None

        for round_num in range(1, max_rounds + 1):
            round_msg = Message(
                sender_id="discussion",
                sender_name="DiscussionOrchestrator",
                channel=channel,
                content=f"--- 第 {round_num}/{max_rounds} 轮 ---",
                message_type=MessageType.SYSTEM,
            )
            await message_bus.send_to_stage(round_msg, project_id, channel)

            for turn_num, agent_id in enumerate(agent_ids):
                agent = agent_service.get_agent(agent_id)
                if not agent:
                    continue

                try:
                    response = await self._agent_speak(
                        agent_id=agent_id,
                        agent=agent,
                        topic=topic,
                        context=context,
                        transcript=transcript,
                        current_round=round_num,
                        max_rounds=max_rounds,
                    )
                except asyncio.TimeoutError:
                    response = f"[{agent.get('name', agent_id)} 超时未响应]"
                except Exception as e:
                    logger.warning(f"Agent {agent_id} speak failed: {e}")
                    response = f"[{agent.get('name', agent_id)} 发言时出错]"

                traits = agent_trait_service.get_trait(agent_id)
                dm = DiscussionMessage(
                    agent_id=agent_id,
                    agent_name=agent.get("name", agent_id),
                    role_label=traits.role_label if traits else agent.get("type", "成员"),
                    content=response,
                    round_number=round_num,
                    turn_number=turn_num,
                )
                transcript.append(dm)

                # 广播到消息总线
                bus_msg = Message(
                    sender_id=agent_id,
                    sender_name=dm.agent_name,
                    channel=channel,
                    content=response,
                    message_type=MessageType.TEXT,
                    metadata={
                        "discussion_id": discussion_id,
                        "round": round_num,
                        "turn": turn_num,
                    },
                )
                await message_bus.send_to_stage(bus_msg, project_id, channel)

            # 第 2 轮起检查共识
            if round_num >= 2:
                consensus, conclusion = await self._check_consensus(
                    transcript, topic
                )
                if consensus:
                    break

        # 生成总结
        summary = await self._summarize_discussion(
            transcript, topic, concluded=consensus or (round_num >= max_rounds)
        )

        end_msg = Message(
            sender_id="discussion",
            sender_name="DiscussionOrchestrator",
            channel=channel,
            content=f"讨论结束 — {'达成共识' if consensus else '达到最大轮数'}",
            message_type=MessageType.SYSTEM,
        )
        await message_bus.send_to_stage(end_msg, project_id, channel)

        return DiscussionResult(
            topic=topic,
            concluded=consensus or (round_num >= max_rounds),
            consensus_reached=consensus,
            conclusion=conclusion or summary,
            summary=summary,
            transcript=transcript,
            participant_agents=agent_ids,
            rounds_conducted=round_num,
            metadata={
                "discussion_id": discussion_id,
                "pipeline_id": pipeline_id,
            },
        )

    async def _agent_speak(
        self,
        agent_id: str,
        agent: Dict[str, Any],
        topic: str,
        context: Dict[str, Any],
        transcript: List[DiscussionMessage],
        current_round: int,
        max_rounds: int,
    ) -> str:
        """让一个 agent 在讨论中发言。使用其 soul.md system prompt。"""
        from app.services.agent.agent_trait_service import agent_trait_service
        from app.services.llm.llm_service import llm_service

        traits = agent_trait_service.get_trait(agent_id)
        system_prompt = agent.get("system_prompt") or registry.render("collaboration.discussion.agent_speak_fallback_system", {})

        user_prompt = self._build_agent_speak_prompt(
            agent=agent,
            traits=traits,
            topic=topic,
            context=context,
            transcript=transcript,
            current_round=current_round,
            max_rounds=max_rounds,
        )

        response = await asyncio.wait_for(
            llm_service.chat(
                messages=[
                    LLMMessage(role="system", content=system_prompt),
                    LLMMessage(role="user", content=user_prompt),
                ],
                track_cost=True,
                task_id=agent_id,
                timeout=60.0,
            ),
            timeout=70.0,
        )

        return response.content

    def _build_agent_speak_prompt(
        self,
        agent: Dict[str, Any],
        traits: Any,
        topic: str,
        context: Dict[str, Any],
        transcript: List[DiscussionMessage],
        current_round: int,
        max_rounds: int,
    ) -> str:
        """构建 agent 发言时收到的提示词"""
        agent_name = agent.get("name", "Agent")
        role_label = traits.role_label if traits else agent.get("type", "团队成员")
        trait_summary = traits.summary if traits else ""

        # 构建讨论历史
        history_lines = []
        for dm in transcript:
            history_lines.append(
                f"[第{dm.round_number}轮] **{dm.agent_name}** ({dm.role_label}): {dm.content}"
            )

        history_text = "\n\n".join(history_lines) if history_lines else "（这是第一轮讨论，尚无人发言）"

        # 上下文文本
        context_text = "\n".join(
            f"- **{k}**: {v}" for k, v in context.items()
        ) if context else "（无额外上下文）"

        is_final = current_round == max_rounds
        final_instruction = "- **这是最后一轮，请明确表述你的最终立场或建议**" if is_final else ""

        return registry.render("collaboration.discussion.agent_speak", {
            "topic": topic,
            "context_text": context_text,
            "agent_name": agent_name,
            "role_label": role_label,
            "trait_summary": trait_summary,
            "history_text": history_text,
            "current_round": current_round,
            "max_rounds": max_rounds,
            "final_instruction": final_instruction,
        })

    async def _check_consensus(
        self,
        transcript: List[DiscussionMessage],
        topic: str,
    ) -> Tuple[bool, Optional[str]]:
        """用 LLM 分析讨论记录，判断是否达成共识。"""
        if len(transcript) < 2:
            return False, None

        # 按 agent 分组发言
        speakers: Dict[str, List[DiscussionMessage]] = {}
        for dm in transcript:
            if dm.agent_id not in speakers:
                speakers[dm.agent_id] = []
            speakers[dm.agent_id].append(dm)

        position_blocks = []
        for agent_id, msgs in speakers.items():
            if not msgs:
                continue
            name = msgs[0].agent_name
            role = msgs[0].role_label
            texts = [f"  [第{m.round_number}轮] {m.content[:500]}" for m in msgs]
            position_blocks.append(f"**{name}** ({role}):\n" + "\n".join(texts))
        positions_text = "\n\n".join(position_blocks)

        try:
            from app.services.llm.llm_service import llm_service

            response = await asyncio.wait_for(
                llm_service.chat(
                    messages=[
                        LLMMessage(
                            role="system",
                            content=registry.render("collaboration.discussion.consensus_check_system", {}),
                        ),
                        LLMMessage(
                            role="user",
                            content=registry.render("collaboration.discussion.consensus_check", {
                                "topic": topic,
                                "positions_text": positions_text,
                            }),
                        ),
                    ],
                    track_cost=False,
                    timeout=15.0,
                ),
                timeout=20.0,
            )

            data = self._parse_json(response.content)
            return data.get("consensus", False), data.get("conclusion")
        except Exception as e:
            logger.warning(f"Consensus check failed: {e}")
            return False, None

    async def _summarize_discussion(
        self,
        transcript: List[DiscussionMessage],
        topic: str,
        concluded: bool,
    ) -> str:
        """生成讨论总结"""
        if not transcript:
            return "无讨论内容"

        history = "\n".join(
            f"[R{dm.round_number}] {dm.agent_name}: {dm.content[:300]}"
            for dm in transcript
        )

        try:
            from app.services.llm.llm_service import llm_service

            response = await asyncio.wait_for(
                llm_service.chat(
                    messages=[
                        LLMMessage(
                            role="system",
                            content=registry.render("collaboration.discussion.summarize_system", {}),
                        ),
                        LLMMessage(
                            role="user",
                            content=registry.render("collaboration.discussion.summarize", {
                                "topic": topic,
                                "history": history,
                                "conclusion_type": "最终结论" if concluded else "可选方向",
                            }),
                        ),
                    ],
                    track_cost=False,
                    timeout=15.0,
                ),
                timeout=20.0,
            )

            return response.content
        except Exception as e:
            logger.warning(f"Discussion summary failed: {e}")
            return f"讨论于 {datetime.now().isoformat()} 结束，共 {len(transcript)} 条发言。"

    def _parse_json(self, text: str) -> dict:
        import re

        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {}

    # ---- Coordinator Election ----

    async def run_coordinator_election(
        self,
        pipeline_id: str,
        project_id: str,
        agent_ids: List[str],
        project_context: Dict[str, Any],
    ) -> str:
        """运行 coordinator 选举讨论。先让各 agent 自荐，再让 LLM 根据发言质量决定。

        Returns: 选出的 agent_id
        """
        if not agent_ids:
            return ""
        if len(agent_ids) == 1:
            return agent_ids[0]

        topic = "请推选一位 Coordinator（协调者）来统筹项目执行"
        context = {
            **project_context,
            "选举目的": "选出一位最适合统筹此项目的协调者。协调者负责拆解任务、分派工作、汇总结果。",
        }

        result = await self.conduct_discussion(
            pipeline_id=pipeline_id,
            project_id=project_id,
            topic=topic,
            context=context,
            agent_ids=agent_ids,
            mode=DiscussionMode.ROUND_ROBIN,
            max_rounds=2,
        )

        # LLM 评估讨论质量，选出 coordinator
        elected = await self._make_election_decision(
            transcript=result.transcript,
            agent_ids=agent_ids,
            project_context=project_context,
        )

        return elected or agent_ids[0]

    async def _make_election_decision(
        self,
        transcript: List[DiscussionMessage],
        agent_ids: List[str],
        project_context: Dict[str, Any],
    ) -> Optional[str]:
        """LLM 评估选举讨论记录，选出最佳 coordinator"""
        if not transcript:
            return agent_ids[0] if agent_ids else None

        speakers_text = "\n".join(
            f"- {dm.agent_name} ({dm.role_label}): {dm.content[:200]}"
            for dm in transcript
        )

        agents_text = "\n".join(f"- {aid}" for aid in agent_ids)

        try:
            from app.services.llm.llm_service import llm_service

            response = await asyncio.wait_for(
                llm_service.chat(
                    messages=[
                        LLMMessage(
                            role="system",
                            content=registry.render("collaboration.discussion.election_system", {}),
                        ),
                        LLMMessage(
                            role="user",
                            content=registry.render("collaboration.discussion.election", {
                                "project_name": project_context.get("name", "未命名"),
                                "project_description": project_context.get("description", "无"),
                                "agents_text": agents_text,
                                "speakers_text": speakers_text,
                            }),
                        ),
                    ],
                    track_cost=False,
                    timeout=15.0,
                ),
                timeout=20.0,
            )

            data = self._parse_json(response.content)
            elected = data.get("elected_agent_id", "")
            if elected and elected in agent_ids:
                return elected
        except Exception as e:
            logger.warning(f"Election decision failed: {e}")

        return agent_ids[0]


discussion_orchestrator = DiscussionOrchestrator()
