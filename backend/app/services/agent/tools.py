"""
Agent 工具系统 — 对标 Claude Code 的工具风格。

每个工具由 ToolDef 定义：name / description / parameters (JSON Schema) / fn (async callable)。
ToolRegistry 负责注册、导出 OpenAI 格式、执行工具调用。
"""

import asyncio
import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    fn: Callable[..., Any]  # async (project_id: str, **kwargs) -> str

    def to_openai(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDef] = {}

    def register(self, tool: ToolDef) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolDef]:
        return self._tools.get(name)

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        return [t.to_openai() for t in self._tools.values()]

    async def execute(self, name: str, args: Dict[str, Any], project_id: str) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"[Error] Unknown tool: {name}"
        try:
            result = tool.fn(project_id=project_id, **args)
            if asyncio.iscoroutine(result):
                result = await result
            return str(result) if result is not None else "[tool returned no output]"
        except Exception as e:
            return f"[Error] Tool '{name}' failed: {e}"


# ============================================================
# 工具实现函数
# ============================================================

async def _list_files(project_id: str, pattern: str = "*") -> str:
    """列出项目工作区文件，支持 glob 模式匹配。"""
    from app.services.project.workspace_manager import workspace_manager

    files = workspace_manager.list_files(project_id)

    def _collect(files, prefix=""):
        lines = []
        for f in files:
            name = f["name"]
            ftype = f["type"]
            fpath = f["path"]
            if fnmatch.fnmatch(fpath, pattern) or fnmatch.fnmatch(name, pattern):
                size_info = f" ({f.get('size', 0)} bytes)" if f.get("size") else ""
                lines.append(f"{prefix}{'[DIR] ' if ftype == 'directory' else '[FILE] '}{fpath}{size_info}")
            if "children" in f and f["children"]:
                lines.extend(_collect(f["children"], prefix + "  "))
        return lines

    result = _collect(files)
    if not result:
        return f"No files match pattern '{pattern}' in project {project_id}"
    return "\n".join(result)


async def _read_file(project_id: str, file_path: str, offset: int = 0, limit: int = 200) -> str:
    """读取工作区中的文件内容，支持行范围。"""
    from app.services.project.workspace_manager import workspace_manager

    content = workspace_manager.read_file(project_id, file_path)
    if content is None:
        return f"[Error] File not found: {file_path}"

    lines = content.split("\n")
    total_lines = len(lines)

    if offset > 0 or limit < total_lines:
        end = min(offset + limit, total_lines)
        selected = lines[offset:end]
        header = f"[{file_path} — lines {offset + 1}-{end} of {total_lines}]\n"
        return header + "\n".join(selected)

    return f"[{file_path} — {total_lines} lines]\n{content}"


async def _write_file(project_id: str, file_path: str, content: str) -> str:
    """写入或覆盖工作区文件。"""
    from app.services.project.workspace_manager import workspace_manager
    from pathlib import Path

    # Extract stage_key from path (e.g. "artifacts/coding/foo.py" → "coding")
    stage_key = Path(file_path).parent.name if "/" in file_path else "artifacts"
    filename = Path(file_path).name

    result = workspace_manager.add_artifact(project_id, stage_key, filename, content)
    if result:
        return f"File written: {result}"
    return "[Error] Failed to write file"


async def _search_content(project_id: str, pattern: str, glob: str = "*") -> str:
    """在工作区文件中搜索匹配内容（ripgrep 风格）。"""
    import re
    from app.services.project.workspace_manager import workspace_manager

    files = workspace_manager.list_files(project_id)

    def _find_files(files):
        result = []
        for f in files:
            if fnmatch.fnmatch(f["name"], glob) or fnmatch.fnmatch(f.get("path", ""), glob):
                if f["type"] == "file":
                    result.append(f["path"])
            if "children" in f and f["children"]:
                result.extend(_find_files(f["children"]))
        return result

    all_files = _find_files(files)
    output_lines = []

    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"[Error] Invalid regex pattern: {e}"

    for file_path in all_files:
        content = workspace_manager.read_file(project_id, file_path)
        if content is None:
            continue
        for i, line in enumerate(content.split("\n"), 1):
            if regex.search(line):
                output_lines.append(f"{file_path}:{i}: {line.strip()[:200]}")

    if not output_lines:
        return f"No matches for '{pattern}' in project {project_id}"
    return "\n".join(output_lines[:50])  # max 50 results


async def _run_command(project_id: str, command: str) -> str:
    """在工作区目录中执行 shell 命令。"""
    import subprocess
    from app.services.project.workspace_manager import workspace_manager

    ws = workspace_manager.get_workspace(project_id)
    if not ws:
        return "[Error] Workspace not found"

    ws_path = ws.get("workspace_path", "")
    if not ws_path:
        return "[Error] Workspace path not found"

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=ws_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n[exit code: {result.returncode}]"
        return output or "[command produced no output]"
    except subprocess.TimeoutExpired:
        return "[Error] Command timed out (30s)"
    except Exception as e:
        return f"[Error] Command failed: {e}"


# ============================================================
# 全局注册中心实例
# ============================================================

_file_tool_registry = ToolRegistry()

_file_tool_registry.register(ToolDef(
    name="list_files",
    description="列出项目工作区中的文件和目录。用于了解项目结构、查看有哪些产出物。支持 glob 模式过滤（如 '**/*.py' 或 '*.md'）。",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "glob 模式，用于过滤文件名/路径。默认 '*' 列出所有。",
            },
        },
        "required": [],
    },
    fn=_list_files,
))

_file_tool_registry.register(ToolDef(
    name="read_file",
    description="读取工作区中指定文件的内容。用于查看调研报告、代码、JSON 数据等产出物的完整内容。支持行范围分页读取。",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "文件路径，相对于工作区根目录。例如 'artifacts/coding/report.md'。先用 list_files 确认路径。",
            },
            "offset": {
                "type": "integer",
                "description": "起始行号（0-indexed），用于分页读取长文件。",
            },
            "limit": {
                "type": "integer",
                "description": "读取行数上限，默认 200。",
            },
        },
        "required": ["file_path"],
    },
    fn=_read_file,
))

_file_tool_registry.register(ToolDef(
    name="write_file",
    description="写入或覆盖工作区中的文件。用于保存产出物、报告、代码等。",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "文件路径。例如 'artifacts/coding/summary.md'。",
            },
            "content": {
                "type": "string",
                "description": "要写入的文件内容。",
            },
        },
        "required": ["file_path", "content"],
    },
    fn=_write_file,
))

_file_tool_registry.register(ToolDef(
    name="search_content",
    description="在工作区文件中搜索匹配正则表达式的内容。用于查找特定代码模式、关键词、数据等。返回文件路径:行号:内容。",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "正则表达式搜索模式。例如 'def test_' 或 'TODO|FIXME'。",
            },
            "glob": {
                "type": "string",
                "description": "glob 模式过滤搜索范围的文件名。默认 '*' 搜索所有。",
            },
        },
        "required": ["pattern"],
    },
    fn=_search_content,
))

_file_tool_registry.register(ToolDef(
    name="run_command",
    description="在项目工作区目录中执行 shell 命令。用于运行脚本、安装依赖、执行代码等。超时 30 秒。",
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "要执行的 shell 命令。",
            },
        },
        "required": ["command"],
    },
    fn=_run_command,
))


def get_tool_registry() -> ToolRegistry:
    return _file_tool_registry
