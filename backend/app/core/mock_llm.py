import asyncio
import json
import os
import random
import re
import logging
from pathlib import Path
from typing import AsyncIterator, Optional, List, Dict, Any

from app.core.llm import Message, LLMResponse
from app.core.llm_providers import BaseLLMProvider

logger = logging.getLogger(__name__)


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM Provider，支持场景文件驱动 + 关键词回退。

    优先从 tests/scenarios/llm_scenarios/*.json 加载场景文件，
    按 prompt_pattern 正则匹配请求内容。未匹配时回退到关键词匹配。
    """

    MOCK_RESPONSES = {
        "greeting": [
            "你好！我是开发者小王，很高兴为你服务。有什么开发任务需要我帮忙吗？",
            "你好！作为后端开发工程师，我可以帮助你解决技术问题、设计系统架构、编写代码等。",
            "你好！我是团队中的开发者，专注于编写清晰易维护的代码。有什么我可以帮助你的吗？"
        ],
        "default": [
            "这是一个很好的问题。让我从开发者的角度来分析：\n\n1. 首先，我们需要考虑系统的整体架构\n2. 然后确定技术选型\n3. 最后进行具体实现\n\n你觉得这个思路怎么样？",
            "好的，让我来帮你分析这个问题。\n\n从技术角度来看，我们需要：\n- 明确需求和目标\n- 设计合理的数据结构\n- 实现核心功能\n- 进行测试验证\n\n每一步都需要仔细考虑。",
            "明白了！这是一个需要综合考虑的问题。\n\n我的建议是：\n1. 先进行技术调研\n2. 制定详细的开发计划\n3. 分阶段实现\n4. 持续优化改进\n\n你更关心哪个方面呢？"
        ],
        "code": [
            "好的，我来帮你看看代码实现。\n\n```python\ndef hello_world():\n    print('Hello, World!')\n```\n\n这是一个简单的示例，如果你有具体的代码需要审查，请分享给我。"
        ],
        "architecture": [
            "关于系统架构设计，我有以下建议：\n\n1. **分层架构**：将系统分为表现层、业务层、数据层\n2. **模块化设计**：每个模块职责单一，便于维护\n3. **接口抽象**：通过接口解耦依赖\n4. **可扩展性**：预留扩展点，支持后续功能迭代\n\n需要我详细展开某个方面吗？"
        ],
    }

    _scenarios: List[Dict[str, Any]] = []
    _scenarios_loaded: bool = False

    def __init__(self, scenarios_dir: Optional[str] = None):
        self.call_count = 0
        self.total_tokens = 0
        self._custom_scenarios: List[Dict[str, Any]] = []

        # 加载场景文件
        search_dir = scenarios_dir
        if search_dir is None:
            # 自动探测场景文件目录
            candidates = [
                Path(__file__).parent.parent / "tests" / "scenarios" / "llm_scenarios",
                Path(os.getcwd()) / "tests" / "scenarios" / "llm_scenarios",
            ]
            for c in candidates:
                if c.is_dir():
                    search_dir = str(c)
                    break

        if search_dir and not MockLLMProvider._scenarios_loaded:
            MockLLMProvider._load_scenarios(search_dir)
            MockLLMProvider._scenarios_loaded = True

    @classmethod
    def _load_scenarios(cls, directory: str) -> None:
        """从目录加载所有场景 JSON 文件。"""
        dir_path = Path(directory)
        if not dir_path.is_dir():
            return

        for file_path in dir_path.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    scenario = json.load(f)
                scenario["_file"] = str(file_path)
                cls._scenarios.append(scenario)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"场景文件加载失败 {file_path}: {e}")

        if cls._scenarios:
            logger.info(f"加载了 {len(cls._scenarios)} 个 LLM 场景文件")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def _match_scenario(self, messages: List[Message]) -> Optional[str]:
        """尝试匹配场景文件。返回 JSON 字符串响应或 None。"""
        combined = " ".join(m.content for m in messages if m.content)

        all_scenarios = self._custom_scenarios + MockLLMProvider._scenarios
        for scenario in all_scenarios:
            pattern = scenario.get("prompt_pattern", "")
            if pattern and re.search(pattern, combined, re.IGNORECASE):
                response = scenario.get("response")
                if response is not None:
                    return json.dumps(response, ensure_ascii=False)

        return None

    def _get_keyword_response(self, messages: List[Message]) -> str:
        """关键词匹配回退（兼容旧行为）。"""
        last_message = messages[-1].content if messages else ""

        self.call_count += 1

        if any(word in last_message.lower() for word in ["你好", "hi", "hello", "嗨"]):
            return random.choice(self.MOCK_RESPONSES["greeting"])
        elif any(word in last_message.lower() for word in ["代码", "code", "实现", "写"]):
            return random.choice(self.MOCK_RESPONSES["code"])
        elif any(word in last_message.lower() for word in ["架构", "设计", "架构师", "system design"]):
            return random.choice(self.MOCK_RESPONSES["architecture"])
        else:
            return random.choice(self.MOCK_RESPONSES["default"])

    def _get_mock_response(self, messages: List[Message]) -> str:
        """主入口：优先场景匹配，回退关键词。"""
        scenario_response = self._match_scenario(messages)
        if scenario_response is not None:
            self.call_count += 1
            return scenario_response

        return self._get_keyword_response(messages)

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        cancellation_token: Optional[asyncio.Event] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        await asyncio.sleep(random.uniform(0.01, 0.05))

        if cancellation_token and cancellation_token.is_set():
            raise asyncio.CancelledError("Mock LLM call cancelled")

        content = self._get_mock_response(messages)

        usage = {
            "prompt_tokens": sum(len(m.content) // 4 for m in messages),
            "completion_tokens": len(content) // 4,
            "total_tokens": (sum(len(m.content) // 4 for m in messages) + len(content) // 4)
        }
        self.total_tokens += usage["total_tokens"]

        return LLMResponse(
            content=content,
            usage=usage,
            model=model or "mock-model",
            finish_reason="stop"
        )

    async def stream_chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        cancellation_token: Optional[asyncio.Event] = None
    ) -> AsyncIterator[str]:
        content = self._get_mock_response(messages)

        for char in content:
            if cancellation_token and cancellation_token.is_set():
                raise asyncio.CancelledError("Mock LLM stream cancelled")
            await asyncio.sleep(random.uniform(0.01, 0.03))
            yield char

        await asyncio.sleep(0.05)

    def get_stats(self) -> Dict[str, int]:
        return {
            "call_count": self.call_count,
            "total_tokens": self.total_tokens
        }

    def reset_stats(self):
        self.call_count = 0
        self.total_tokens = 0


async def create_mock_provider(scenarios_dir: Optional[str] = None) -> MockLLMProvider:
    return MockLLMProvider(scenarios_dir=scenarios_dir)
