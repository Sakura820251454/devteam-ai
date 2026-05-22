"""
Prompt Registry — 统一 Prompt 管理。

所有 LLM prompt 的单一真相源。从 YAML 加载模板，通过 str.format() 渲染。

用法:
    from app.services.shared.prompt_registry import registry

    prompt = registry.render("agent.executor.plan_task_steps", {
        "task_title": task.title,
        "task_description": task.description,
    })
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PromptEntry:
    """单条 prompt 模板条目。"""

    def __init__(
        self,
        id: str,
        description: str = "",
        template: Optional[str] = None,
        variables: Optional[List[Dict[str, str]]] = None,
        output_format: str = "text",
        source_file: str = "",
        code_managed: bool = False,
        conditional: str = "",
        version: str = "1.0.0",
        changelog: Optional[List[Dict[str, str]]] = None,
    ):
        self.id = id
        self.description = description
        self.template = template
        self.variables = variables or []
        self.output_format = output_format
        self.source_file = source_file
        self.code_managed = code_managed
        self.conditional = conditional
        self.version = version
        self.changelog = changelog or []


class PromptRegistry:
    """中央 prompt 注册表。惰性加载，线程安全（加载后只读）。"""

    def __init__(self, registry_path: Optional[str] = None):
        self._entries: Dict[str, PromptEntry] = {}
        self._registry_path = registry_path
        self._loaded = False

    def _default_path(self) -> str:
        return str(Path(__file__).parent.parent.parent / "prompts" / "registry.yaml")

    @property
    def path(self) -> str:
        if self._registry_path is None:
            self._registry_path = self._default_path()
        return self._registry_path

    def load(self) -> None:
        if self._loaded:
            return
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "PyYAML is required for the Prompt Registry. "
                "Install it with: pip install pyyaml"
            )

        path = Path(self.path)
        if not path.exists():
            logger.warning("Registry file not found: %s", path)
            return

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "prompts" not in data:
            logger.error("Invalid registry file: missing 'prompts' key")
            return

        meta = data.get("metadata", {})
        registry_version = meta.get("version", "1.0.0")

        for prompt_id, entry_data in data["prompts"].items():
            self._entries[prompt_id] = PromptEntry(
                id=prompt_id,
                description=entry_data.get("description", ""),
                template=entry_data.get("template"),
                variables=entry_data.get("variables", []),
                output_format=entry_data.get("output_format", "text"),
                source_file=entry_data.get("source_file", ""),
                code_managed=entry_data.get("code_managed", False),
                conditional=entry_data.get("conditional", ""),
                version=entry_data.get("version", registry_version),
                changelog=entry_data.get("changelog", []),
            )

        self._loaded = True
        logger.info("Loaded %d prompts from registry", len(self._entries))

    def reload(self) -> None:
        self._loaded = False
        self.load()

    def get_entry(self, prompt_id: str) -> Optional[PromptEntry]:
        self._ensure_loaded()
        return self._entries.get(prompt_id)

    def list_entries(self) -> Dict[str, PromptEntry]:
        self._ensure_loaded()
        return dict(self._entries)

    def render(self, prompt_id: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """
        渲染 prompt 模板。

        Args:
            prompt_id: 注册表中的 prompt ID。
            variables: 变量名到值的映射。

        Returns:
            渲染后的 prompt 字符串。

        Raises:
            KeyError: prompt_id 未找到。
            ValueError: 该 prompt 是 code_managed，不能通过 registry 渲染。
        """
        self._ensure_loaded()
        entry = self._entries.get(prompt_id)
        if not entry:
            raise KeyError(f"Prompt not found: {prompt_id}")

        if entry.code_managed:
            raise ValueError(
                f"Prompt '{prompt_id}' is code-managed and cannot be "
                f"rendered by the registry. See {entry.source_file}"
            )

        if entry.template is None:
            raise ValueError(f"Prompt '{prompt_id}' has no template defined")

        if variables:
            return entry.template.format(**variables)
        return entry.template

    def get_ids_by_source(self, source_file: str) -> List[str]:
        self._ensure_loaded()
        return [
            pid for pid, entry in self._entries.items()
            if entry.source_file.startswith(source_file)
        ]

    def validate(self) -> List[str]:
        """
        校验所有模板的变量一致性。
        返回错误列表，空列表表示全部通过。
        """
        errors = []
        for pid, entry in self._entries.items():
            if entry.code_managed or entry.template is None:
                continue
            found = set(re.findall(r'\{(\w+)\}', entry.template))
            declared = {v["name"] for v in entry.variables}
            for f in found:
                if f not in declared:
                    errors.append(
                        f"{pid}: variable '{{{f}}}' used in template but not declared"
                    )
            for d in declared:
                if d not in found:
                    errors.append(
                        f"{pid}: declared variable '{d}' not found in template"
                    )
        return errors

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()


# 全局单例
registry = PromptRegistry()
