"""SoulParser 单元测试 — Agent 人格文件解析。

覆盖 parse / _extract_section / _extract_field / load / soul_to_system_prompt。
"""
import pytest
from pathlib import Path
from unittest.mock import patch

from app.services.shared.soul_parser import (
    SoulParser, SoulFile, load_agent_from_soul, load_all_agents, soul_to_system_prompt,
)


SAMPLE_SOUL = """# Soul: 测试角色

## Core Principles
- 始终保持冷静
- 优先考虑安全性
- 以用户为中心

## Execution Rules
- 每个任务开始前先分析
- 不确定时主动询问
- 输出要有结构化格式

## Skills
- skill_a: 擅长数据分析
- skill_b: 擅长文档撰写

## Knowledge
- 了解 Python 生态
- 了解 Web 开发
"""


class TestSoulParserParse:
    """核心解析逻辑。"""

    def _write_soul(self, tmp_path, agent_dir_name, content):
        """在 tmp_path 下创建 agent_xxx/soul.md。"""
        agent_dir = tmp_path / agent_dir_name
        agent_dir.mkdir()
        soul_file = agent_dir / "soul.md"
        soul_file.write_text(content, encoding="utf-8")
        return soul_file

    def test_extract_name_from_dir(self, tmp_path):
        """从目录名 agent_xiaoming 提取 name=xiaoming。"""
        soul_file = self._write_soul(tmp_path, "agent_xiaoming", SAMPLE_SOUL)
        parser = SoulParser(str(soul_file))
        result = parser.parse()
        assert result.name == "xiaoming"

    def test_extract_name_without_prefix(self, tmp_path):
        """目录名没有 agent_ 前缀时直接用作 name。"""
        soul_file = self._write_soul(tmp_path, "custom_agent", SAMPLE_SOUL)
        parser = SoulParser(str(soul_file))
        result = parser.parse()
        assert result.name == "custom_agent"

    def test_extract_core_principles(self, tmp_path):
        soul_file = self._write_soul(tmp_path, "agent_test", SAMPLE_SOUL)
        parser = SoulParser(str(soul_file))
        result = parser.parse()
        assert "始终保持冷静" in result.core_principles
        assert len(result.core_principles) == 3

    def test_extract_execution_rules(self, tmp_path):
        soul_file = self._write_soul(tmp_path, "agent_test", SAMPLE_SOUL)
        parser = SoulParser(str(soul_file))
        result = parser.parse()
        assert "每个任务开始前先分析" in result.execution_rules
        assert len(result.execution_rules) == 3

    def test_extract_role_definitions(self, tmp_path):
        soul_file = self._write_soul(tmp_path, "agent_test", SAMPLE_SOUL)
        parser = SoulParser(str(soul_file))
        result = parser.parse()
        assert "skills" in result.role_definitions
        assert "knowledge" in result.role_definitions

    def test_empty_soul(self, tmp_path):
        """空 soul.md 返回默认值。"""
        soul_file = self._write_soul(tmp_path, "agent_empty", "# Empty Agent\n")
        parser = SoulParser(str(soul_file))
        result = parser.parse()
        assert result.core_principles == []
        assert result.execution_rules == []
        assert result.role_definitions == {}

    def test_list_item_formats(self, tmp_path):
        """支持 -, *, • 三种列表标记。"""
        content = """# Test
## Core Principles
- item1
* item2
• item3
"""
        soul_file = self._write_soul(tmp_path, "agent_test", content)
        parser = SoulParser(str(soul_file))
        result = parser.parse()
        assert len(result.core_principles) == 3


class TestExtractSection:
    """_extract_section 边界情况。"""

    def test_section_not_found(self):
        parser = SoulParser.__new__(SoulParser)
        parser.content = "# No such section"
        result = parser._extract_section(parser.content, "Skills")
        assert result == []

    def test_section_with_empty_content(self):
        parser = SoulParser.__new__(SoulParser)
        parser.content = "## Skills\n\n## Next Section"
        result = parser._extract_section(parser.content, "Skills")
        assert result == []

    def test_section_at_end_of_file(self):
        parser = SoulParser.__new__(SoulParser)
        parser.content = "## Skills\n- skill1\n- skill2"
        result = parser._extract_section(parser.content, "Skills")
        assert len(result) == 2

    def test_skips_short_lines(self):
        """少于10字符的非列表行应被跳过。"""
        parser = SoulParser.__new__(SoulParser)
        parser.content = "## Skills\n- valid item here\nab\ncd"
        result = parser._extract_section(parser.content, "Skills")
        # "ab" 和 "cd" 太短，应被跳过
        assert len(result) == 1


class TestExtractField:
    """_extract_field 正则提取。"""

    def test_extract_basic(self):
        parser = SoulParser.__new__(SoulParser)
        content = "Name: TestAgent\nRole: Tester"
        name = parser._extract_field(content, r'Name:\s*(.+)')
        assert name == "TestAgent"

    def test_extract_not_found(self):
        parser = SoulParser.__new__(SoulParser)
        result = parser._extract_field("no match", r'Name:\s*(.+)')
        assert result == ""

    def test_extract_case_insensitive(self):
        parser = SoulParser.__new__(SoulParser)
        content = "NAME: MyAgent"
        result = parser._extract_field(content, r'Name:\s*(.+)')
        assert result == "MyAgent"


class TestLoadFunctions:
    """load_agent_from_soul / load_all_agents。"""

    def test_load_agent_from_soul(self, tmp_path):
        agent_dir = tmp_path / "agent_test"
        agent_dir.mkdir()
        soul_file = agent_dir / "soul.md"
        soul_file.write_text(SAMPLE_SOUL, encoding="utf-8")

        soul = load_agent_from_soul(str(soul_file))
        assert soul.name == "test"
        assert len(soul.core_principles) == 3

    def test_load_all_agents(self, tmp_path):
        for name in ["agent_a", "agent_b"]:
            agent_dir = tmp_path / name
            agent_dir.mkdir()
            soul_file = agent_dir / "soul.md"
            soul_file.write_text(SAMPLE_SOUL, encoding="utf-8")

        agents = load_all_agents(str(tmp_path))
        assert len(agents) == 2
        assert "a" in agents
        assert "b" in agents

    def test_load_all_agents_empty_dir(self, tmp_path):
        agents = load_all_agents(str(tmp_path))
        assert agents == {}

    def test_load_all_agents_nonexistent_dir(self):
        agents = load_all_agents("/no/such/directory")
        assert agents == {}


class TestSoulToSystemPrompt:
    """soul_to_system_prompt 转换。"""

    def test_with_principles_and_rules(self):
        soul = SoulFile(
            name="test",
            core_principles=["原则1", "原则2"],
            execution_rules=["规则1"],
        )
        with patch("app.services.shared.soul_parser.registry") as mock_reg:
            mock_reg.render.side_effect = lambda key, vars: f"[{key}]"
            prompt = soul_to_system_prompt(soul)
            assert "shared.soul.header" in prompt
            assert "shared.soul.core_principles" in prompt
            assert "shared.soul.execution_rules" in prompt

    def test_empty_soul_fallback(self):
        soul = SoulFile(name="empty")
        with patch("app.services.shared.soul_parser.registry") as mock_reg:
            mock_reg.render.side_effect = lambda key, vars: f"[{key}]"
            prompt = soul_to_system_prompt(soul)
            assert "shared.soul.fallback" in prompt

    def test_with_role_definitions_list(self):
        soul = SoulFile(
            name="test",
            role_definitions={"skills": ["skill_a", "skill_b"], "knowledge": ["领域知识"]},
        )
        with patch("app.services.shared.soul_parser.registry") as mock_reg:
            mock_reg.render.side_effect = lambda key, vars: f"[{key}]"
            prompt = soul_to_system_prompt(soul)
            assert "Skills" in prompt
            assert "Knowledge" in prompt
