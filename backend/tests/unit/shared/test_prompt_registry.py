"""Prompt Registry 单元测试"""

import pytest
from app.services.shared.prompt_registry import PromptRegistry, PromptEntry, registry


class TestPromptRegistry:
    """测试 PromptRegistry 核心功能"""

    def test_load_registry(self):
        """加载注册表，验证所有条目可解析"""
        reg = PromptRegistry()
        reg.load()
        entries = reg.list_entries()
        assert len(entries) > 0, "注册表不应为空"
        # 验证至少包含所有模块的条目
        modules = set()
        for pid in entries:
            modules.add(pid.split(".")[0])
        assert "agent" in modules
        assert "collaboration" in modules
        assert "execution" in modules

    def test_render_simple_no_variables(self):
        """渲染无变量的 prompt"""
        reg = PromptRegistry()
        reg.load()
        result = reg.render("collaboration.pipeline.requirement_analysis_system", {"analyst_role": "资深产品经理"})
        assert "资深产品经理" in result

    def test_render_with_variables(self):
        """渲染有变量的 prompt"""
        reg = PromptRegistry()
        reg.load()
        result = reg.render("agent.executor.plan_steps", {
            "task_title": "测试任务",
            "task_description": "这是一个测试",
        })
        assert "测试任务" in result
        assert "这是一个测试" in result
        assert '"steps"' in result  # JSON 格式约束存在

    def test_render_unknown_prompt_raises(self):
        """渲染不存在的 prompt 应抛出 KeyError"""
        reg = PromptRegistry()
        reg.load()
        with pytest.raises(KeyError):
            reg.render("nonexistent.prompt.id")

    def test_code_managed_prompt_raises(self):
        """渲染 code_managed prompt 应抛出 ValueError"""
        reg = PromptRegistry()
        reg.load()
        with pytest.raises(ValueError, match="code-managed"):
            reg.render("agent.executor.feedback_context")

    def test_get_entry(self):
        """获取 prompt 元数据"""
        reg = PromptRegistry()
        reg.load()
        entry = reg.get_entry("agent.executor.plan_steps")
        assert entry is not None
        assert entry.id == "agent.executor.plan_steps"
        assert len(entry.variables) == 2
        assert entry.output_format == "json"

    def test_list_entries(self):
        """列出所有 prompt"""
        reg = PromptRegistry()
        reg.load()
        entries = reg.list_entries()
        assert "agent.executor.plan_steps" in entries
        assert "agent.template.generic" in entries
        assert "collaboration.arbitrator.meta_resolve" in entries

    def test_get_ids_by_source(self):
        """按源文件筛选 prompt"""
        reg = PromptRegistry()
        reg.load()
        ids = reg.get_ids_by_source(
            "backend/app/services/collaboration/arbitrator.py"
        )
        assert len(ids) >= 1
        assert any("arbitrator" in pid for pid in ids)

    def test_reload(self):
        """重新加载注册表"""
        reg = PromptRegistry()
        reg.load()
        count1 = len(reg.list_entries())
        reg.reload()
        count2 = len(reg.list_entries())
        assert count1 == count2

    def test_validate_no_errors(self):
        """校验注册表变量一致性"""
        reg = PromptRegistry()
        reg.load()
        errors = reg.validate()
        assert errors == [], f"Registry validation errors:\n" + "\n".join(errors)

    def test_custom_path(self):
        """自定义路径加载"""
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "app", "prompts", "registry.yaml",
        )
        path = os.path.abspath(path)
        reg = PromptRegistry(registry_path=path)
        reg.load()
        assert len(reg.list_entries()) > 0

    def test_render_json_escaping(self):
        """JSON 花括号转义正确"""
        reg = PromptRegistry()
        reg.load()
        result = reg.render("agent.trait.generate", {
            "agent_name": "测试",
            "principles": "- 测试原则",
            "rules": "- 测试规则",
        })
        # 验证 JSON 示例中的花括号是单层的（说明 {{ }} 转义正确）
        assert '"role_label"' in result
        assert '"skills"' in result
        assert '{{' not in result  # 不应有双花括号残留
