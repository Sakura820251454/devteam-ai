"""Agent 工具系统单元测试。

测试 ToolDef / ToolRegistry 的注册、导出、执行。
纯逻辑测试，不依赖 LLM 或文件系统。
"""

import pytest

from app.services.agent.tools import ToolDef, ToolRegistry, get_tool_registry


# ========== ToolDef ==========


class TestToolDef:
    """ToolDef 定义和 OpenAI 格式导出。"""

    def test_to_openai_format(self):
        tool = ToolDef(
            name="test_tool",
            description="一个测试工具",
            parameters={
                "type": "object",
                "properties": {"arg1": {"type": "string"}},
                "required": ["arg1"],
            },
            fn=lambda **kwargs: "ok",
        )
        result = tool.to_openai()
        assert result["type"] == "function"
        assert result["function"]["name"] == "test_tool"
        assert result["function"]["description"] == "一个测试工具"
        assert "arg1" in result["function"]["parameters"]["properties"]

    def test_to_openai_has_required_section(self):
        tool = ToolDef(
            name="tool_with_params",
            description="带参数的工具",
            parameters={"type": "object", "properties": {}, "required": []},
            fn=lambda **kwargs: "done",
        )
        result = tool.to_openai()
        assert result["function"]["parameters"]["required"] == []


# ========== ToolRegistry ==========


class TestToolRegistry:
    """ToolRegistry 注册和查询。"""

    @pytest.fixture
    def registry(self):
        return ToolRegistry()

    def test_register_and_get(self, registry):
        tool = ToolDef(name="tool1", description="d1", parameters={}, fn=lambda **k: "r")
        registry.register(tool)
        assert registry.get("tool1") is tool

    def test_get_unknown_returns_none(self, registry):
        assert registry.get("nonexistent") is None

    def test_get_openai_tools_empty(self, registry):
        assert registry.get_openai_tools() == []

    def test_get_openai_tools_with_registered(self, registry):
        registry.register(ToolDef(name="t1", description="d1", parameters={}, fn=lambda **k: "r1"))
        registry.register(ToolDef(name="t2", description="d2", parameters={}, fn=lambda **k: "r2"))
        tools = registry.get_openai_tools()
        assert len(tools) == 2
        names = [t["function"]["name"] for t in tools]
        assert "t1" in names
        assert "t2" in names

    @pytest.mark.asyncio
    async def test_execute_sync_function(self, registry):
        """同步函数被注册为工具时应正常执行。"""
        def sync_fn(project_id, **kwargs):
            return f"project={project_id}, args={kwargs}"

        registry.register(ToolDef(name="sync_tool", description="", parameters={}, fn=sync_fn))
        result = await registry.execute("sync_tool", {"key": "val"}, project_id="proj-1")
        assert "proj-1" in result
        assert "key" in result

    @pytest.mark.asyncio
    async def test_execute_async_function(self, registry):
        """异步函数被注册为工具时应正常执行。"""
        async def async_fn(project_id, **kwargs):
            return f"async result for {project_id}"

        registry.register(ToolDef(name="async_tool", description="", parameters={}, fn=async_fn))
        result = await registry.execute("async_tool", {}, project_id="proj-2")
        assert result == "async result for proj-2"

    @pytest.mark.asyncio
    async def test_execute_unknown_tool_returns_error(self, registry):
        result = await registry.execute("no_such_tool", {}, project_id="proj")
        assert "[Error]" in result
        assert "Unknown tool" in result

    @pytest.mark.asyncio
    async def test_execute_tool_error_returns_error_message(self, registry):
        def failing_fn(project_id, **kwargs):
            raise ValueError("something went wrong")

        registry.register(ToolDef(name="bad_tool", description="", parameters={}, fn=failing_fn))
        result = await registry.execute("bad_tool", {}, project_id="proj")
        assert "[Error]" in result
        assert "something went wrong" in result


# ========== 全局工具注册 ==========


class TestGlobalRegistry:
    """全局 _file_tool_registry 的初始状态。"""

    def test_global_registry_has_five_tools(self):
        reg = get_tool_registry()
        tools = reg.get_openai_tools()
        tool_names = [t["function"]["name"] for t in tools]
        assert "list_files" in tool_names
        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "search_content" in tool_names
        assert "run_command" in tool_names

    def test_global_tool_parameters_have_schema(self):
        """每个工具都有合法的 JSON Schema parameters。"""
        reg = get_tool_registry()
        for tool_def_dict in reg.get_openai_tools():
            params = tool_def_dict["function"]["parameters"]
            assert params["type"] == "object", f"{tool_def_dict['function']['name']} 的 parameters.type 应为 object"
            assert "properties" in params, f"{tool_def_dict['function']['name']} 缺少 properties"
