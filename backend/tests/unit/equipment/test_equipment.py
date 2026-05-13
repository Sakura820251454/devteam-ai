"""
装备系统测试 - Phase 5

测试智能装备模块的核心功能
"""

import pytest

from app.services.equipment.equipment_service import (
    equipment_service,
    ToolMetadata,
    ToolType,
    ResourceCost,
    TaskAnalyzer,
    ToolMatcher,
    AgentEquipmentContext,
)
from app.services.equipment.equipment_init import init_default_tools


class TestToolRegistry:
    """工具注册表测试"""
    
    def setup_method(self):
        """设置测试环境"""
        init_default_tools()
    
    def test_register_tool(self):
        """测试注册工具"""
        tool = ToolMetadata(
            id="test_tool",
            name="测试工具",
            type=ToolType.SKILL,
            version="1.0",
            description="测试工具描述",
            capabilities=["test_capability"],
            suitable_tasks=["测试任务"],
        )
        
        equipment_service.register_tool(tool)
        
        retrieved = equipment_service.tool_registry.get("test_tool")
        assert retrieved is not None
        assert retrieved.name == "测试工具"
    
    def test_get_tool(self):
        """测试获取工具"""
        tool = equipment_service.tool_registry.get("mcp_file_system")
        assert tool is not None
        assert tool.name == "文件系统工具"
    
    def test_find_by_capability(self):
        """测试按能力查找"""
        tools = equipment_service.tool_registry.find_by_capability("file_read")
        assert len(tools) > 0
        assert any(t.name == "文件系统工具" for t in tools)
    
    def test_find_by_task(self):
        """测试按任务查找"""
        tools = equipment_service.tool_registry.find_by_task("代码审查")
        assert len(tools) > 0
        assert any(t.name == "代码审查技能" for t in tools)
    
    def test_update_usage_stats(self):
        """测试更新使用统计"""
        equipment_service.tool_registry.update_usage_stats(
            "mcp_file_system", success=True, execution_time=0.5
        )
        
        tool = equipment_service.tool_registry.get("mcp_file_system")
        assert tool.usage_count == 1
        assert tool.success_rate == 1.0
        assert tool.avg_execution_time == 0.5


class TestTaskAnalyzer:
    """任务分析器测试"""
    
    def setup_method(self):
        """设置测试环境"""
        init_default_tools()
    
    def test_analyze_simple_task(self):
        """测试分析简单任务"""
        analyzer = TaskAnalyzer(equipment_service.tool_registry)
        requirements = analyzer.analyze("读取一个文件")
        
        assert len(requirements.required_tools) > 0
        assert any(t.id == "mcp_file_system" for t in requirements.required_tools)
    
    def test_analyze_complex_task(self):
        """测试分析复杂任务"""
        analyzer = TaskAnalyzer(equipment_service.tool_registry)
        requirements = analyzer.analyze("编写Python代码并执行测试")
        
        has_code_gen = any(t.id == "skill_code_generation" for t in requirements.required_tools)
        has_test = any(t.id == "skill_testing" for t in requirements.required_tools)
        has_exec = any(t.id == "mcp_code_exec" for t in requirements.required_tools)
        
        assert has_code_gen or has_test or has_exec
    
    def test_analyze_with_memory(self):
        """测试分析需要记忆的任务"""
        analyzer = TaskAnalyzer(equipment_service.tool_registry)
        requirements = analyzer.analyze("查询记忆中的历史数据")
        
        has_memory = any(t.type == ToolType.MEMORY for t in requirements.required_tools)
        assert has_memory


class TestToolMatcher:
    """工具匹配器测试"""
    
    def setup_method(self):
        """设置测试环境"""
        init_default_tools()
    
    def test_match_tools(self):
        """测试匹配工具"""
        analyzer = TaskAnalyzer(equipment_service.tool_registry)
        requirements = analyzer.analyze("读取文件并审查代码")
        
        matcher = ToolMatcher(equipment_service.tool_registry)
        matched = matcher.match(requirements)
        
        assert len(matched) > 0
        assert any(t.id == "mcp_file_system" for t in matched)
    
    def test_budget_filtering(self):
        """测试预算过滤"""
        analyzer = TaskAnalyzer(equipment_service.tool_registry)
        requirements = analyzer.analyze("执行复杂的代码审查任务")
        
        matcher = ToolMatcher(equipment_service.tool_registry)
        matched = matcher.match(requirements, budget_tokens=500)
        
        total_cost = sum(t.resource_cost.tokens for t in matched)
        assert total_cost <= 500
    
    def test_dependency_resolution(self):
        """测试依赖解析"""
        analyzer = TaskAnalyzer(equipment_service.tool_registry)
        requirements = analyzer.analyze("执行Python代码")
        
        matcher = ToolMatcher(equipment_service.tool_registry)
        matched = matcher.match(requirements)
        
        has_code_exec = any(t.id == "mcp_code_exec" for t in matched)
        has_terminal = any(t.id == "mcp_terminal" for t in matched)
        
        assert has_code_exec
        assert has_terminal


class TestAgentEquipmentContext:
    """Agent装备上下文测试"""
    
    def test_equip_tools(self):
        """测试装备工具"""
        context = AgentEquipmentContext("test_agent")
        
        tool1 = ToolMetadata(id="tool1", name="工具1", type=ToolType.SKILL, version="1.0", description="")
        tool2 = ToolMetadata(id="tool2", name="工具2", type=ToolType.SKILL, version="1.0", description="")
        
        result = context.equip([tool1, tool2])
        
        assert len(result) == 2
        assert "tool1" in result
        assert "tool2" in result
        assert len(context.equipped_tools) == 2
    
    def test_unequip_tool(self):
        """测试卸载工具"""
        context = AgentEquipmentContext("test_agent")
        tool = ToolMetadata(id="tool1", name="工具1", type=ToolType.SKILL, version="1.0", description="")
        context.equip([tool])
        
        result = context.unequip("tool1")
        
        assert result is True
        assert len(context.equipped_tools) == 0
    
    def test_conflict_detection(self):
        """测试冲突检测"""
        context = AgentEquipmentContext("test_agent")
        tool1 = ToolMetadata(id="tool1", name="工具1", type=ToolType.SKILL, version="1.0", description="", excludes=["tool2"])
        tool2 = ToolMetadata(id="tool2", name="工具2", type=ToolType.SKILL, version="1.0", description="")
        
        context.equip([tool1])
        result = context.equip([tool2])
        
        assert len(result) == 0
        assert len(context.equipped_tools) == 1
    
    def test_get_capabilities(self):
        """测试获取能力"""
        context = AgentEquipmentContext("test_agent")
        tool = ToolMetadata(
            id="tool1", 
            name="工具1", 
            type=ToolType.SKILL, 
            version="1.0", 
            description="",
            capabilities=["cap1", "cap2"]
        )
        context.equip([tool])
        
        capabilities = context.get_equipped_capabilities()
        
        assert "cap1" in capabilities
        assert "cap2" in capabilities


class TestEquipmentService:
    """装备服务测试"""
    
    def setup_method(self):
        """设置测试环境"""
        init_default_tools()
    
    def test_analyze_and_equip(self):
        """测试分析并装备"""
        equipped_ids, confidence = equipment_service.analyze_and_equip(
            "test_agent", "读取文件并编写代码"
        )
        
        assert len(equipped_ids) > 0
        assert confidence > 0
    
    def test_get_agent_equipment(self):
        """测试获取Agent装备"""
        equipment_service.analyze_and_equip("test_agent2", "执行代码审查")
        
        context = equipment_service.get_agent_equipment("test_agent2")
        
        assert context is not None
        assert len(context.equipped_tools) > 0


class TestIntegration:
    """集成测试"""
    
    def test_full_workflow(self):
        """测试完整工作流程"""
        init_default_tools()
        
        result = equipment_service.analyze_and_equip(
            "dev_agent", "分析代码性能问题并进行优化"
        )
        
        equipped_ids, confidence = result
        assert len(equipped_ids) > 0
        assert confidence >= 0.7
        
        context = equipment_service.get_agent_equipment("dev_agent")
        assert context is not None
        
        capabilities = context.get_equipped_capabilities()
        assert len(capabilities) > 0
        
        equipment_service.update_tool_usage("dev_agent", equipped_ids[0], success=True, execution_time=1.5)
        
        tool = equipment_service.tool_registry.get(equipped_ids[0])
        assert tool.usage_count == 1
        
        context.unequip(equipped_ids[0])
        assert len(context.equipped_tools) == len(equipped_ids) - 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
