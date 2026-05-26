"""
Agent 工具调用执行器 —— LLM ↔ 工具调用循环。

对标 Claude Code 的交互模式：LLM 决定调用哪些工具，框架执行并返回结果，
循环直到 LLM 给出最终文本回复。
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from app.core.llm import Message, LLMResponse
from app.services.agent.tools import ToolRegistry

logger = logging.getLogger(__name__)


class ToolExecutor:
    def __init__(
        self,
        tool_registry: ToolRegistry,
        max_iterations: int = 8,
    ):
        self.registry = tool_registry
        self.max_iterations = max_iterations

    def _get_registry(self):
        if self.registry is None:
            from app.services.agent.tools import get_tool_registry
            self.registry = get_tool_registry()
        return self.registry

    async def run(
        self,
        messages: List[Message],
        tools: List[Dict[str, Any]],
        project_id: str,
        cancellation_token: Optional[asyncio.Event] = None,
    ) -> str:
        """
        工具调用循环。

        1. 调用 LLM（带 tools 定义）
        2. 收到 tool_calls → 并行执行 → 追加 tool 结果消息
        3. 收到 text → 返回
        4. 达到 max_iterations → 强制终止，让 LLM 基于已有信息回答
        """
        from app.services.llm.llm_service import llm_service

        registry = self._get_registry()
        messages = list(messages)  # 不修改调用方传入的列表

        for iteration in range(self.max_iterations):
            if cancellation_token and cancellation_token.is_set():
                raise asyncio.CancelledError("Tool execution cancelled")

            response: LLMResponse = await llm_service.chat(
                messages=messages,
                tools=tools,
                track_cost=True,
                timeout=120.0,
                cancellation_token=cancellation_token,
            )

            # 有 tool_calls → 执行工具
            if response.tool_calls:
                # 将 assistant 消息（含 tool_calls）追加到对话
                assistant_msg = Message(
                    role="assistant",
                    content=response.content or "",
                    tool_calls=response.tool_calls,
                )
                messages.append(assistant_msg)

                # 并行执行所有工具调用
                tool_results = await asyncio.gather(
                    *[
                        self._execute_tool_call(tc, project_id)
                        for tc in response.tool_calls
                    ],
                    return_exceptions=True,
                )

                # 将 tool 结果消息追加到对话
                for tc, result in zip(response.tool_calls, tool_results):
                    if isinstance(result, Exception):
                        result = f"[Error] Tool execution failed: {result}"
                    func = tc.get("function", {})
                    tool_name = func.get("name", "unknown")
                    tool_call_id = tc.get("id", "")
                    messages.append(Message.tool_result(
                        tool_call_id=tool_call_id,
                        name=tool_name,
                        content=str(result),
                    ))

                continue

            # 有 text content → 最终结果
            if response.content:
                return response.content

            # 既无 tool_calls 也无 content（罕见）→ 让 LLM 继续
            messages.append(Message(
                role="user",
                content="请继续。如果已完成，请给出最终结果。",
            ))

        # 达到最大迭代次数 → 强制要求总结
        messages.append(Message(
            role="user",
            content="已达到最大工具调用次数。请基于已获取的信息，直接给出最终结果，不要再调用工具。",
        ))
        final_response = await llm_service.chat(
            messages=messages,
            track_cost=True,
            timeout=120.0,
            cancellation_token=cancellation_token,
        )
        return final_response.content or "[Agent did not produce a final response]"

    async def _execute_tool_call(
        self, tool_call: Dict[str, Any], project_id: str
    ) -> str:
        func = tool_call.get("function", {})
        name = func.get("name", "")
        raw_args = func.get("arguments", "{}")

        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {}
        else:
            args = raw_args

        logger.info(f"Tool call: {name}({args})")
        registry = self._get_registry()
        result = await registry.execute(name, args, project_id)
        preview = result[:200] + "..." if len(result) > 200 else result
        logger.info(f"Tool result ({name}): {preview}")
        return result


# 全局单例
tool_executor = ToolExecutor(
    tool_registry=None,  # 将在 agent_executor 初始化时注入
    max_iterations=8,
)


def init_tool_executor() -> ToolExecutor:
    """在 lifespan 中调用，注入 tool_registry。"""
    from app.services.agent.tools import get_tool_registry
    global tool_executor
    tool_executor = ToolExecutor(
        tool_registry=get_tool_registry(),
        max_iterations=8,
    )
    return tool_executor
