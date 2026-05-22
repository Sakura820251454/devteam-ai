#!/usr/bin/env python3
"""
从 Prompt Registry YAML 自动生成 VitePress 文档。

用法:
    python scripts/prompt_doc_gen.py              # 生成文档
    python scripts/prompt_doc_gen.py --check      # CI 模式：检查文档是否同步
"""

import hashlib
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required. Install with: pip install pyyaml")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "backend" / "app" / "prompts" / "registry.yaml"
OUTPUT_PATH = ROOT / "docs" / "04-modules" / "backend" / "prompt-registry.md"


def load_registry():
    """加载 YAML 注册表"""
    if not REGISTRY_PATH.exists():
        print(f"ERROR: Registry not found: {REGISTRY_PATH}")
        sys.exit(1)
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def render_doc(data: dict) -> str:
    """渲染 VitePress Markdown 文档"""
    meta = data.get("metadata", {})
    prompts = data.get("prompts", {})

    # 按模块分组
    modules: dict[str, list] = {}
    for pid, entry in prompts.items():
        module = pid.split(".")[0]
        if module not in modules:
            modules[module] = []
        modules[module].append((pid, entry))

    lines = [
        "# Prompt Registry",
        "",
        f'**Total prompts**: {len(prompts)}  ',
        f'**Last updated**: {meta.get("updated", "N/A")}  ',
        f'**Version**: {meta.get("version", "N/A")}  ',
        "",
        "::: warning 自动生成",
        f"本文档由 `scripts/prompt_doc_gen.py` 从 `{REGISTRY_PATH.relative_to(ROOT)}` 自动生成。",
        "请勿手动编辑。修改 prompt 请编辑 registry.yaml 后重新运行脚本。",
        ":::",
        "",
        "## 概述",
        "",
        "Prompt Registry 是 DevTeam-AI 中所有 LLM prompt 的**唯一真相源**。",
        "所有 prompt 模板集中管理在此 YAML 文件中，代码通过 `registry.render(id, vars)` 调用。",
        "",
        "### 使用方式",
        "",
        "```python",
        "from app.services.shared.prompt_registry import registry",
        "",
        'prompt = registry.render("agent.executor.plan_steps", {',
        '    "task_title": task.title,',
        '    "task_description": task.description,',
        "})",
        "```",
        "",
        "### 命名规范",
        "",
        "`{module}.{file_short}.{purpose}[.{variant}]`",
        "",
        "---",
        "",
    ]

    # 按模块输出
    for module_name in sorted(modules.keys()):
        entries = modules[module_name]
        renderable = [(pid, e) for pid, e in entries if not e.get("code_managed")]
        code_managed = [(pid, e) for pid, e in entries if e.get("code_managed")]

        lines.append(f"## {module_name.title()} Module ({len(entries)} prompts)")
        lines.append("")

        if renderable:
            lines.append("| ID | Description | Variables | Output | Source |")
            lines.append("|----|-------------|-----------|--------|--------|")
            for pid, entry in renderable:
                vars_list = ", ".join(v["name"] for v in entry.get("variables", [])) or "—"
                output = entry.get("output_format", "text")
                source = entry.get("source_file", "").split(":")[-1] if entry.get("source_file") else "—"
                desc = entry.get("description", "")[:80]
                lines.append(
                    f"| `{pid}` | {desc} | {vars_list} | {output} | {source} |"
                )
            lines.append("")

        if code_managed:
            lines.append("### Code-Managed Prompts")
            lines.append("")
            lines.append("以下 prompt 由于逻辑复杂，模板主体保留在 Python 代码中，注册表仅记录信息和位置。")
            lines.append("")
            lines.append("| ID | Description | Source |")
            lines.append("|----|-------------|--------|")
            for pid, entry in code_managed:
                desc = entry.get("description", "")[:80]
                source = entry.get("source_file", "").split(":")[-1] if entry.get("source_file") else "—"
                lines.append(f"| `{pid}` | {desc} | {source} |")
            lines.append("")

    # Changelog
    lines.append("---")
    lines.append("")
    lines.append("## 版本历史")
    lines.append("")
    lines.append("| Version | Date | Description |")
    lines.append("|---------|------|-------------|")
    lines.append(f'| {meta.get("version", "1.0.0")} | {meta.get("updated", "N/A")} | 从源码迁移，初始注册表创建 |')

    return "\n".join(lines) + "\n"


def get_file_hash(filepath: Path) -> str:
    """获取文件 SHA256"""
    if not filepath.exists():
        return ""
    return hashlib.sha256(filepath.read_bytes()).hexdigest()


def main():
    check_mode = "--check" in sys.argv

    data = load_registry()
    new_doc = render_doc(data)

    if check_mode:
        if not OUTPUT_PATH.exists():
            print("ERROR: Documentation file does not exist. Run without --check to generate.")
            sys.exit(1)

        existing = OUTPUT_PATH.read_text(encoding="utf-8")
        if existing.strip() != new_doc.strip():
            print("ERROR: Prompt documentation is out of sync with registry.")
            print("Run: python scripts/prompt_doc_gen.py")
            sys.exit(1)

        print("OK: Prompt documentation is in sync with registry.")
    else:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(new_doc, encoding="utf-8")
        print(f"Generated: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
