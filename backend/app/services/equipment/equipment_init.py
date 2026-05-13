"""
工具注册表初始化 - Phase 5

注册系统内置的工具、技能和记忆模块
"""

from app.services.equipment.equipment_service import (
    equipment_service,
    ToolMetadata,
    ToolType,
    ResourceCost,
)


def init_default_tools():
    """初始化默认工具"""
    
    # === MCP工具 ===
    
    equipment_service.register_tool(ToolMetadata(
        id="mcp_file_system",
        name="文件系统工具",
        type=ToolType.MCP,
        version="1.0",
        description="提供文件读写、创建、删除等文件系统操作能力",
        capabilities=["file_operation", "file_read", "file_write", "file_create", "file_delete"],
        suitable_tasks=["文件操作", "代码保存", "配置管理"],
        resource_cost=ResourceCost(tokens=100, memory_mb=10, seconds=1),
        usage_count=0,
        success_rate=0.95,
        avg_execution_time=0.5,
    ))
    
    equipment_service.register_tool(ToolMetadata(
        id="mcp_terminal",
        name="终端工具",
        type=ToolType.MCP,
        version="1.0",
        description="提供命令行终端执行能力",
        capabilities=["terminal", "command", "shell_execution"],
        suitable_tasks=["命令执行", "脚本运行", "系统管理"],
        resource_cost=ResourceCost(tokens=50, memory_mb=50, seconds=5),
        usage_count=0,
        success_rate=0.98,
        avg_execution_time=2.0,
    ))
    
    equipment_service.register_tool(ToolMetadata(
        id="mcp_git",
        name="Git工具",
        type=ToolType.MCP,
        version="1.0",
        description="提供Git版本控制操作能力",
        capabilities=["git", "version_control", "code_commit"],
        suitable_tasks=["代码提交", "分支管理", "代码同步"],
        resource_cost=ResourceCost(tokens=80, memory_mb=20, seconds=3),
        usage_count=0,
        success_rate=0.96,
        avg_execution_time=1.5,
    ))
    
    equipment_service.register_tool(ToolMetadata(
        id="mcp_code_exec",
        name="代码执行工具",
        type=ToolType.MCP,
        version="1.0",
        description="提供Python代码执行能力",
        capabilities=["code_execution", "python_run", "script_exec"],
        suitable_tasks=["代码测试", "脚本运行", "数据分析"],
        resource_cost=ResourceCost(tokens=200, memory_mb=100, seconds=10),
        depends_on=["mcp_terminal"],
        usage_count=0,
        success_rate=0.92,
        avg_execution_time=3.0,
    ))
    
    # === 技能工具 ===
    
    equipment_service.register_tool(ToolMetadata(
        id="skill_code_review",
        name="代码审查技能",
        type=ToolType.SKILL,
        version="1.0",
        description="提供代码审查和质量检查能力",
        capabilities=["code_review", "code_inspection", "quality_check"],
        suitable_tasks=["代码审查", "代码优化", "bug检测"],
        resource_cost=ResourceCost(tokens=1000, memory_mb=50, seconds=30),
        usage_count=0,
        success_rate=0.88,
        avg_execution_time=15.0,
    ))
    
    equipment_service.register_tool(ToolMetadata(
        id="skill_code_generation",
        name="代码生成技能",
        type=ToolType.SKILL,
        version="1.0",
        description="提供代码生成能力",
        capabilities=["code_generation", "code_writing", "api_design"],
        suitable_tasks=["功能开发", "API设计", "代码编写"],
        resource_cost=ResourceCost(tokens=1500, memory_mb=80, seconds=60),
        usage_count=0,
        success_rate=0.90,
        avg_execution_time=25.0,
    ))
    
    equipment_service.register_tool(ToolMetadata(
        id="skill_code_optimization",
        name="代码优化技能",
        type=ToolType.SKILL,
        version="1.0",
        description="提供代码优化和重构能力",
        capabilities=["code_optimization", "code_refactoring", "performance"],
        suitable_tasks=["性能优化", "代码重构", "技术债务清理"],
        resource_cost=ResourceCost(tokens=1200, memory_mb=60, seconds=45),
        usage_count=0,
        success_rate=0.85,
        avg_execution_time=20.0,
    ))
    
    equipment_service.register_tool(ToolMetadata(
        id="skill_documentation",
        name="文档编写技能",
        type=ToolType.SKILL,
        version="1.0",
        description="提供技术文档编写能力",
        capabilities=["documentation", "tech_writing", "spec_writing"],
        suitable_tasks=["文档编写", "技术规范", "API文档"],
        resource_cost=ResourceCost(tokens=800, memory_mb=30, seconds=40),
        usage_count=0,
        success_rate=0.92,
        avg_execution_time=18.0,
    ))
    
    equipment_service.register_tool(ToolMetadata(
        id="skill_testing",
        name="测试技能",
        type=ToolType.SKILL,
        version="1.0",
        description="提供测试用例编写和测试执行能力",
        capabilities=["testing", "test_writing", "test_execution"],
        suitable_tasks=["测试开发", "自动化测试", "质量保证"],
        resource_cost=ResourceCost(tokens=600, memory_mb=40, seconds=35),
        usage_count=0,
        success_rate=0.94,
        avg_execution_time=12.0,
    ))
    
    equipment_service.register_tool(ToolMetadata(
        id="skill_design",
        name="架构设计技能",
        type=ToolType.SKILL,
        version="1.0",
        description="提供系统架构设计能力",
        capabilities=["design", "architecture", "system_design"],
        suitable_tasks=["架构设计", "系统设计", "技术选型"],
        resource_cost=ResourceCost(tokens=1500, memory_mb=70, seconds=60),
        usage_count=0,
        success_rate=0.86,
        avg_execution_time=30.0,
    ))
    
    # === 知识库工具 ===
    
    equipment_service.register_tool(ToolMetadata(
        id="knowledge_api_docs",
        name="API文档知识库",
        type=ToolType.KNOWLEDGE,
        version="1.0",
        description="提供API文档查询能力",
        capabilities=["api_documentation", "api_reference", "api_usage"],
        suitable_tasks=["API开发", "接口调用", "集成开发"],
        resource_cost=ResourceCost(tokens=300, memory_mb=100, seconds=5),
        usage_count=0,
        success_rate=0.97,
        avg_execution_time=2.0,
    ))
    
    equipment_service.register_tool(ToolMetadata(
        id="knowledge_best_practices",
        name="最佳实践知识库",
        type=ToolType.KNOWLEDGE,
        version="1.0",
        description="提供开发最佳实践查询能力",
        capabilities=["best_practices", "coding_standards", "patterns"],
        suitable_tasks=["代码规范", "模式应用", "最佳实践"],
        resource_cost=ResourceCost(tokens=200, memory_mb=80, seconds=4),
        usage_count=0,
        success_rate=0.95,
        avg_execution_time=1.5,
    ))
    
    equipment_service.register_tool(ToolMetadata(
        id="knowledge_tech_guides",
        name="技术指南知识库",
        type=ToolType.KNOWLEDGE,
        version="1.0",
        description="提供技术指南和教程查询能力",
        capabilities=["technical_knowledge", "guides", "tutorials"],
        suitable_tasks=["技术学习", "方案调研", "技术决策"],
        resource_cost=ResourceCost(tokens=400, memory_mb=120, seconds=6),
        usage_count=0,
        success_rate=0.93,
        avg_execution_time=2.5,
    ))
    
    # === 记忆模块 ===
    
    equipment_service.register_tool(ToolMetadata(
        id="memory_short_term",
        name="短期记忆模块",
        type=ToolType.MEMORY,
        version="1.0",
        description="提供会话级短期记忆访问能力",
        capabilities=["short_term_memory", "session_context", "recent_history"],
        suitable_tasks=["上下文理解", "会话追踪", "短期记忆"],
        resource_cost=ResourceCost(tokens=100, memory_mb=50, seconds=1),
        usage_count=0,
        success_rate=0.99,
        avg_execution_time=0.5,
    ))
    
    equipment_service.register_tool(ToolMetadata(
        id="memory_long_term",
        name="长期记忆模块",
        type=ToolType.MEMORY,
        version="1.0",
        description="提供长期记忆检索和存储能力",
        capabilities=["long_term_memory", "knowledge_retrieval", "experience"],
        suitable_tasks=["知识检索", "经验复用", "长期记忆"],
        resource_cost=ResourceCost(tokens=200, memory_mb=100, seconds=3),
        usage_count=0,
        success_rate=0.96,
        avg_execution_time=1.0,
    ))
    
    equipment_service.register_tool(ToolMetadata(
        id="memory_project",
        name="项目记忆模块",
        type=ToolType.MEMORY,
        version="1.0",
        description="提供项目级记忆管理能力",
        capabilities=["project_memory", "team_context", "project_history"],
        suitable_tasks=["项目追踪", "团队协作", "项目记忆"],
        resource_cost=ResourceCost(tokens=150, memory_mb=80, seconds=2),
        usage_count=0,
        success_rate=0.98,
        avg_execution_time=0.8,
    ))
    
    # === 模板工具 ===
    
    equipment_service.register_tool(ToolMetadata(
        id="template_code",
        name="代码模板",
        type=ToolType.TEMPLATE,
        version="1.0",
        description="提供代码模板生成能力",
        capabilities=["code_templates", "boilerplate", "patterns"],
        suitable_tasks=["快速开发", "代码生成", "模式应用"],
        resource_cost=ResourceCost(tokens=300, memory_mb=20, seconds=5),
        usage_count=0,
        success_rate=0.94,
        avg_execution_time=2.0,
    ))
    
    equipment_service.register_tool(ToolMetadata(
        id="template_document",
        name="文档模板",
        type=ToolType.TEMPLATE,
        version="1.0",
        description="提供文档模板生成能力",
        capabilities=["document_templates", "report_templates", "spec_templates"],
        suitable_tasks=["文档编写", "报告生成", "规范编写"],
        resource_cost=ResourceCost(tokens=250, memory_mb=15, seconds=4),
        usage_count=0,
        success_rate=0.95,
        avg_execution_time=1.5,
    ))


def get_tool_stats() -> dict:
    """获取工具统计信息"""
    all_tools = equipment_service.tool_registry.find_all()
    
    by_type = {}
    for tool in all_tools:
        t = tool.type.value
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(tool)
    
    return {
        "total_tools": len(all_tools),
        "by_type": {k: len(v) for k, v in by_type.items()},
        "types": [t.value for t in ToolType],
    }
