"""Golden Path 轨迹录制与回放框架。

使用方式：

    # 录制模式（需要真实 LLM）
    recorder = GoldenPathRecorder("investigation")
    # ... 运行 pipeline，每轮 LLM 调用经过 recorder ...
    recorder.save()

    # 回放模式（Mock LLM）
    replayer = GoldenPathReplayer("investigation")
    mock_provider = replayer.create_mock_provider()
    # ... 运行 pipeline，验证行为一致性 ...
    replayer.verify()
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_DIR = Path(__file__).parent / "golden_paths"


class GoldenPathRecorder:
    """录制真实 LLM trace 为 golden path 场景文件。"""

    def __init__(self, name: str, directory: Optional[Path] = None):
        self.name = name
        self.directory = directory or _DEFAULT_DIR
        self._trace: List[Dict[str, Any]] = []
        self._call_index = 0
        self._started_at = datetime.now().isoformat()

    def record_llm_call(
        self,
        messages: List[Any],
        response: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """记录一次 LLM 调用（输入 + 输出）。"""
        self._call_index += 1
        entry = {
            "step": self._call_index,
            "timestamp": datetime.now().isoformat(),
            "input": {
                "messages": [
                    {"role": m.role, "content": m.content[:2000]}
                    for m in messages
                ],
            },
            "output": {
                "content": response[:2000],
            },
        }
        if tool_calls:
            entry["output"]["tool_calls"] = tool_calls
        if metadata:
            entry["metadata"] = metadata
        self._trace.append(entry)

    def save(self) -> str:
        """保存 trace 到 golden path 文件。"""
        self.directory.mkdir(parents=True, exist_ok=True)
        file_path = self.directory / f"{self.name}.json"

        data = {
            "name": self.name,
            "description": f"Golden path: {self.name}",
            "recorded_at": self._started_at,
            "total_calls": len(self._trace),
            "trace": self._trace,
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Golden path saved: {file_path} ({len(self._trace)} calls)")
        return str(file_path)

    @property
    def call_count(self) -> int:
        return len(self._trace)


class GoldenPathReplayer:
    """回放录制的 golden path，用于回归测试。"""

    def __init__(self, name: str, directory: Optional[Path] = None):
        self.name = name
        self.directory = directory or _DEFAULT_DIR
        self._trace: List[Dict[str, Any]] = []
        self._replay_index = 0
        self._mismatches: List[Dict[str, Any]] = []
        self._loaded = False

    def load(self) -> None:
        """加载 golden path 文件。"""
        file_path = self.directory / f"{self.name}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Golden path not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._trace = data.get("trace", [])
        self._loaded = True
        logger.info(f"Golden path loaded: {file_path} ({len(self._trace)} calls)")

    def next_response(self) -> Optional[str]:
        """获取下一个录制的 LLM 响应（用于 Mock LLM）。"""
        if not self._loaded:
            self.load()

        if self._replay_index >= len(self._trace):
            logger.warning(
                f"Golden path {self.name}: exhausted ({len(self._trace)} calls recorded, "
                f"but more calls were requested)"
            )
            return None

        entry = self._trace[self._replay_index]
        self._replay_index += 1
        return entry["output"]["content"]

    def next_tool_calls(self) -> Optional[List[Dict[str, Any]]]:
        """获取下一个录制的 tool_calls（如果有）。"""
        if not self._loaded:
            self.load()

        idx = self._replay_index - 1  # next_response 已经推进了 index
        if 0 <= idx < len(self._trace):
            return self._trace[idx]["output"].get("tool_calls")
        return None

    def verify(self) -> Dict[str, Any]:
        """验证回放是否完整（所有录制的调用都被回放了）。"""
        if not self._loaded:
            self.load()

        total = len(self._trace)
        replayed = self._replay_index
        complete = replayed >= total

        return {
            "name": self.name,
            "complete": complete,
            "total_calls": total,
            "replayed_calls": replayed,
            "remaining": max(0, total - replayed),
            "mismatches": len(self._mismatches),
            "details": self._mismatches[:10],
        }

    def reset(self) -> None:
        """重置回放位置。"""
        self._replay_index = 0
        self._mismatches = []

    def create_mock_provider(self):
        """创建一个使用 golden path 响应的 MockLLMProvider。"""
        from app.core.mock_llm import MockLLMProvider

        provider = MockLLMProvider()

        # 存储 golden path 响应序列
        if not self._loaded:
            self.load()

        self.reset()
        responses = [entry["output"]["content"] for entry in self._trace]

        # 用自定义场景注入 golden path 响应
        provider._custom_scenarios = [
            {
                "name": f"golden_{self.name}",
                "prompt_pattern": ".*",  # 匹配所有
                "response": {"__golden_path_response__": True},
            }
        ]

        # 重写匹配方法以返回 golden path 响应
        original_match = provider._match_scenario

        def golden_match(messages):
            resp = self.next_response()
            if resp is not None:
                return resp
            return original_match(messages)

        provider._match_scenario = golden_match
        return provider

    @property
    def total_calls(self) -> int:
        if not self._loaded:
            self.load()
        return len(self._trace)
