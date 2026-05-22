import re
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from app.services.shared.prompt_registry import registry


@dataclass
class SoulFile:
    """从 soul.md 解析出的 Agent 灵魂定义"""
    
    # 基本信息（可选）
    name: str = ""
    role: str = ""
    title: str = ""
    avatar_emoji: str = ""
    avatar_color: str = "#6B7280"
    
    # 核心原则
    core_principles: List[str] = field(default_factory=list)
    
    # 执行规则
    execution_rules: List[str] = field(default_factory=list)
    
    # 额外的角色定义（可选，用于特殊角色）
    role_definitions: Dict[str, str] = field(default_factory=dict)


class SoulParser:
    """解析 soul.md 文件的解析器"""
    
    def __init__(self, soul_file_path: str):
        self.file_path = Path(soul_file_path)
        self.content = self._read_file()
    
    def _read_file(self) -> str:
        """读取 soul.md 文件"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def parse(self) -> SoulFile:
        """解析 soul.md 文件"""
        content = self.content
        
        # 从目录名提取 Agent 名字
        dir_name = self.file_path.parent.name
        if dir_name.startswith('agent_'):
            name = dir_name[6:]  # 移除 "agent_" 前缀
        else:
            name = dir_name
        
        # 提取 Core Principles
        core_principles = self._extract_section(content, 'Core Principles')
        
        # 提取 Execution Rules
        execution_rules = self._extract_section(content, 'Execution Rules')
        
        # 提取其他可能的角色定义
        role_definitions = {}
        for section in ['Skills', 'Knowledge', 'Boundaries']:
            section_content = self._extract_section(content, section)
            if section_content:
                role_definitions[section.lower()] = section_content
        
        return SoulFile(
            name=name,
            core_principles=core_principles,
            execution_rules=execution_rules,
            role_definitions=role_definitions
        )
    
    def _extract_field(self, content: str, pattern: str, default: str = '') -> str:
        """提取字段"""
        match = re.search(pattern, content, re.IGNORECASE)
        return match.group(1).strip() if match else default
    
    def _extract_section(self, content: str, section_name: str) -> List[str]:
        """提取部分内容作为列表"""
        # 匹配 ## Section Name 后的内容，直到下一个 ## 或文件结束
        pattern = rf'##\s+{re.escape(section_name)}\s*\n+(.*?)(?=\n##|\n#\n|\Z)'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        
        if not match:
            return []
        
        section_content = match.group(1).strip()
        
        # 解析列表项
        items = []
        lines = section_content.split('\n')
        for line in lines:
            line = line.strip()
            # 匹配常见的列表格式: -, *, •, 或直接是句子
            if line.startswith(('- ', '* ', '• ')):
                item = line[2:].strip()
                if item:
                    items.append(item)
            elif line and not line.startswith('#'):
                # 如果不是空行且不是标题，可能是无标记的列表
                if len(line) > 10:  # 排除太短的行
                    items.append(line)
        
        return items


def load_agent_from_soul(soul_file_path: str) -> SoulFile:
    """从 soul.md 文件加载 Agent 定义"""
    parser = SoulParser(soul_file_path)
    return parser.parse()


def load_all_agents(agents_dir: str = "agents") -> Dict[str, SoulFile]:
    """从 agents 目录加载所有 Agent"""
    agents = {}
    agents_path = Path(agents_dir)
    
    if not agents_path.exists():
        return agents
    
    for agent_dir in agents_path.iterdir():
        if agent_dir.is_dir():
            soul_file = agent_dir / "soul.md"
            if soul_file.exists():
                try:
                    soul = load_agent_from_soul(str(soul_file))
                    agents[soul.name] = soul
                except Exception as e:
                    print(f"Error loading agent from {soul_file}: {e}")
    
    return agents


def soul_to_system_prompt(soul: SoulFile) -> str:
    """将 SoulFile 转换为系统提示词"""
    parts = []

    parts.append(registry.render("shared.soul.header", {}))

    if soul.core_principles:
        principles_lines = "\n".join(f"- {p}" for p in soul.core_principles)
        parts.append(registry.render("shared.soul.core_principles", {
            "principles_lines": principles_lines,
        }))

    if soul.execution_rules:
        rules_lines = "\n".join(f"- {r}" for r in soul.execution_rules)
        parts.append(registry.render("shared.soul.execution_rules", {
            "rules_lines": rules_lines,
        }))

    # 如果有角色定义，添加角色定义
    if soul.role_definitions:
        for section, content in soul.role_definitions.items():
            if isinstance(content, list):
                parts.append(f"## {section.title()}\n")
                for item in content:
                    parts.append(f"- {item}")
            else:
                parts.append(f"## {section.title()}\n{content}")
            parts.append("")

    # 默认行为指示
    if not soul.core_principles and not soul.execution_rules:
        parts.append(registry.render("shared.soul.fallback", {}))

    return "\n".join(parts)
