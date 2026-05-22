from enum import Enum


class LLMProviderType(str, Enum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    MOCK = "mock"


class LLMModelInfo:
    def __init__(
        self,
        name: str,
        provider: LLMProviderType,
        input_cost_per_1k: float = 0.0,
        output_cost_per_1k: float = 0.0,
        max_tokens: int = 4096,
        supports_streaming: bool = True,
        description: str = ""
    ):
        self.name = name
        self.provider = provider
        self.input_cost_per_1k = input_cost_per_1k
        self.output_cost_per_1k = output_cost_per_1k
        self.max_tokens = max_tokens
        self.supports_streaming = supports_streaming
        self.description = description


AVAILABLE_MODELS = {
    "gpt-4o": LLMModelInfo(
        name="gpt-4o",
        provider=LLMProviderType.OPENAI,
        input_cost_per_1k=5.0,
        output_cost_per_1k=15.0,
        max_tokens=128000,
        description="OpenAI最新旗舰模型，功能强大"
    ),
    "gpt-4o-mini": LLMModelInfo(
        name="gpt-4o-mini",
        provider=LLMProviderType.OPENAI,
        input_cost_per_1k=0.15,
        output_cost_per_1k=0.6,
        max_tokens=128000,
        description="轻量级GPT-4，性价比高"
    ),
    "gpt-3.5-turbo": LLMModelInfo(
        name="gpt-3.5-turbo",
        provider=LLMProviderType.OPENAI,
        input_cost_per_1k=0.5,
        output_cost_per_1k=1.5,
        max_tokens=16385,
        description="经典模型，稳定可靠"
    ),
    "deepseek-v4-flash": LLMModelInfo(
        name="deepseek-v4-flash",
        provider=LLMProviderType.DEEPSEEK,
        input_cost_per_1k=0.001,
        output_cost_per_1k=0.002,
        max_tokens=384000,
        supports_streaming=True,
        description="DeepSeek V4 Flash — 快速低成本模型 (284B/13B active)，1M上下文"
    ),
    "deepseek-v4-pro": LLMModelInfo(
        name="deepseek-v4-pro",
        provider=LLMProviderType.DEEPSEEK,
        input_cost_per_1k=0.012,
        output_cost_per_1k=0.024,
        max_tokens=384000,
        supports_streaming=True,
        description="DeepSeek V4 Pro — 旗舰模型 (1.6T/49B active)，1M上下文"
    ),
    "deepseek-chat": LLMModelInfo(
        name="deepseek-chat",
        provider=LLMProviderType.DEEPSEEK,
        input_cost_per_1k=0.001,
        output_cost_per_1k=0.002,
        max_tokens=64000,
        description="[旧版] DeepSeek V3 通用对话模型，将于2026-07-24退役，请迁移至 deepseek-v4-flash"
    ),
    "deepseek-coder": LLMModelInfo(
        name="deepseek-coder",
        provider=LLMProviderType.DEEPSEEK,
        input_cost_per_1k=0.001,
        output_cost_per_1k=0.002,
        max_tokens=64000,
        description="[旧版] DeepSeek代码专用模型，将于2026-07-24退役"
    ),
    "claude-3-5-sonnet": LLMModelInfo(
        name="claude-3-5-sonnet",
        provider=LLMProviderType.ANTHROPIC,
        input_cost_per_1k=3.0,
        output_cost_per_1k=15.0,
        max_tokens=200000,
        description="Anthropic最新模型，擅长分析"
    ),
    "claude-3-opus": LLMModelInfo(
        name="claude-3-opus",
        provider=LLMProviderType.ANTHROPIC,
        input_cost_per_1k=15.0,
        output_cost_per_1k=75.0,
        max_tokens=200000,
        description="Anthropic最强模型"
    ),
    "mock-model": LLMModelInfo(
        name="mock-model",
        provider=LLMProviderType.MOCK,
        input_cost_per_1k=0.0,
        output_cost_per_1k=0.0,
        max_tokens=10000,
        description="Mock模型，仅用于开发测试"
    ),
}


def get_model_info(model_name: str) -> LLMModelInfo:
    return AVAILABLE_MODELS.get(model_name, AVAILABLE_MODELS["deepseek-v4-flash"])


def calculate_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    model_info = get_model_info(model_name)
    prompt_cost = (prompt_tokens / 1000) * model_info.input_cost_per_1k
    completion_cost = (completion_tokens / 1000) * model_info.output_cost_per_1k
    return round(prompt_cost + completion_cost, 6)
