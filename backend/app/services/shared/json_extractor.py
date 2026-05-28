r"""统一的 JSON 提取与校验工具。

替代代码中 9 处重复的 re.search 模式。
使用平衡括号匹配，正确处理嵌套 JSON、中文标点、尾随逗号等边界情况。
"""

import json
import logging
import re
from typing import Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class JSONExtractionError(Exception):
    """JSON 提取失败：文本中未找到合法的 JSON 对象。"""

    def __init__(self, message: str, raw_text_snippet: str = ""):
        super().__init__(message)
        self.raw_text_snippet = raw_text_snippet[:500]


class JSONValidationError(Exception):
    """JSON 校验失败：数据不符合 Schema 定义。"""

    def __init__(self, message: str, validation_errors: list = None):
        super().__init__(message)
        self.validation_errors = validation_errors or []


# LLM 常见的非标准 JSON 模式，按优先级排列
_JSON_FIXUPS = [
    # 尾随逗号（LLM 最爱犯的错）
    (re.compile(r",\s*(\}|\])"), r"\1"),
    # 中文逗号/冒号
    (re.compile(r"，"), ","),
    (re.compile(r"："), ":"),
    # 单引号 key/value
    (re.compile(r"'([^']*)'\s*:"), r'"\1":'),
    # 单引号 value（保守：只替换 : 后面的）
    (re.compile(r":\s*'([^']*)'"), r': "\1"'),
    # 注释行 // ... 和 # ...
    (re.compile(r"//[^\n]*"), ""),
    (re.compile(r"#[^\n]*"), ""),
    # 三引号
    (re.compile(r'"""'), '"'),
    (re.compile(r"'''"), '"'),
    # markdown 代码块标记
    (re.compile(r"```(?:json)?\s*"), ""),
]


def _fixup_json_text(text: str) -> str:
    """对 LLM 常见的非标准 JSON 格式做修正。"""
    for pattern, replacement in _JSON_FIXUPS:
        text = pattern.sub(replacement, text)
    return text


def _find_json_balanced(text: str) -> Optional[str]:
    r"""用平衡括号匹配找到第一个完整的 JSON 对象。

    遍历字符，跟踪嵌套深度（大括号和方括号），深度归零时返回匹配到的子串。
    这比正则表达式更准确，因为后者遇到嵌套大括号会提前截断或太贪婪。
    """
    start = -1
    depth = 0
    in_string = False
    escape = False

    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ("{", "["):
            if depth == 0:
                start = i
            depth += 1
        elif ch in ("}", "]"):
            depth -= 1
            if depth == 0 and start >= 0:
                return text[start : i + 1]

    return None


def extract_json(text: str) -> dict:
    """从文本中提取并解析 JSON 对象。

    返回解析后的 dict。失败时抛出 JSONExtractionError。
    """
    if not text or not text.strip():
        raise JSONExtractionError("输入文本为空")

    # 先尝试平衡括号匹配
    json_str = _find_json_balanced(text)
    if json_str:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass  # 原始 JSON 无效，尝试修复后再解析

    # 用 fixup 修复常见问题后再次尝试平衡匹配
    fixed_text = _fixup_json_text(text)
    json_str = _find_json_balanced(fixed_text)
    if json_str:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise JSONExtractionError(
                f"JSON 解析失败，已尝试格式修正: {e}",
                raw_text_snippet=text,
            )

    # 最后的尝试：在整个修复后的文本中找 JSON
    fixed = _fixup_json_text(text).strip()
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    raise JSONExtractionError(
        "未找到有效的 JSON 对象（已尝试平衡括号匹配和格式修正）",
        raw_text_snippet=text,
    )


def extract_and_validate(text: str, schema_class: Type[T]) -> T:
    """从文本中提取 JSON 并用 Pydantic Schema 校验。

    返回校验后的 Pydantic 对象。失败时抛出 JSONExtractionError 或 JSONValidationError。
    """
    raw = extract_json(text)

    try:
        return schema_class(**raw)
    except ValidationError as e:
        # 提供有意义的错误信息
        field_errors = []
        for err in e.errors():
            loc = " → ".join(str(x) for x in err["loc"])
            msg = err["msg"]
            field_errors.append(f"{loc}: {msg}")

        raise JSONValidationError(
            f"{schema_class.__name__} 校验失败: {'; '.join(field_errors[:5])}",
            validation_errors=field_errors,
        ) from e
