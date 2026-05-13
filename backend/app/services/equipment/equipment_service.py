"""
智能装备模块 - Phase 5

实现文档3.5节定义的智能装备系统：
1. 工具注册表 - 管理所有可用工具
2. 任务需求分析 - 分析任务需要哪些工具
3. 智能匹配与自动装备 - 根据任务匹配最佳工具

参考文档: docs/specs/2026-05-09-devteam-ai-design.md#3.5
"""

from typing import List, Dict, Any, Optional, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid
from abc import ABC, abstractmethod


class ToolType(str, Enum):
    """工具类型"""
    MCP = "mcp"           # MCP工具
    SKILL = "skill"       # 技能
    KNOWLEDGE = "knowledge" # 知识库
    MEMORY = "memory"     # 记忆模块
    TEMPLATE = "template" # 模板


@dataclass
class ResourceCost:
    """资源消耗预估"""
    tokens: int = 0       # Token消耗
    memory_mb: int = 0    # 内存消耗(MB)
    seconds: float = 0    # 时间消耗(秒)


@dataclass
class ToolMetadata:
    """工具元数据"""
    id: str
    name: str
    type: ToolType
    version: str
    description: str
    
    capabilities: List[str] = field(default_factory=list)
    suitable_tasks: List[str] = field(default_factory=list)
    resource_cost: ResourceCost = field(default_factory=ResourceCost)
    depends_on: List[str] = field(default_factory=list)
    excludes: List[str] = field(default_factory=list)
    
    usage_count: int = 0
    success_rate: float = 0.0
    avg_execution_time: float = 0.0
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, ToolMetadata] = {}
        self._capability_index: Dict[str, List[str]] = {}
        self._task_index: Dict[str, List[str]] = {}
    
    def register(self, tool: ToolMetadata) -> None:
        """注册工具"""
        self._tools[tool.id] = tool
        
        for capability in tool.capabilities:
            if capability not in self._capability_index:
                self._capability_index[capability] = []
            self._capability_index[capability].append(tool.id)
        
        for task in tool.suitable_tasks:
            if task not in self._task_index:
                self._task_index[task] = []
            self._task_index[task].append(tool.id)
        
        tool.updated_at = datetime.now()
    
    def get(self, tool_id: str) -> Optional[ToolMetadata]:
        """获取工具"""
        return self._tools.get(tool_id)
    
    def find_by_capability(self, capability: str) -> List[ToolMetadata]:
        """按能力查找工具"""
        tool_ids = self._capability_index.get(capability, [])
        return [self._tools[id] for id in tool_ids if id in self._tools]
    
    def find_by_task(self, task_type: str) -> List[ToolMetadata]:
        """按任务类型查找工具"""
        tool_ids = self._task_index.get(task_type, [])
        return [self._tools[id] for id in tool_ids if id in self._tools]
    
    def find_all(self) -> List[ToolMetadata]:
        """获取所有工具"""
        return list(self._tools.values())
    
    def unregister(self, tool_id: str) -> bool:
        """注销工具"""
        tool = self._tools.pop(tool_id, None)
        if tool:
            for capability in tool.capabilities:
                if capability in self._capability_index:
                    self._capability_index[capability].remove(tool_id)
            for task in tool.suitable_tasks:
                if task in self._task_index:
                    self._task_index[task].remove(tool_id)
            return True
        return False
    
    def update_usage_stats(
        self,
        tool_id: str,
        success: bool,
        execution_time: float
    ) -> None:
        """更新使用统计"""
        tool = self._tools.get(tool_id)
        if tool:
            tool.usage_count += 1
            tool.avg_execution_time = (
                (tool.avg_execution_time * (tool.usage_count - 1) + execution_time)
                / tool.usage_count
            )
            if success:
                tool.success_rate = (
                    (tool.success_rate * (tool.usage_count - 1) + 1.0)
                    / tool.usage_count
                )
            tool.updated_at = datetime.now()


class TaskAnalyzer:
    """任务需求分析器"""
    
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
    
    def analyze(self, task_description: str) -> 'TaskRequirements':
        """分析任务需求"""
        requirements = TaskRequirements(task_description=task_description)
        
        keywords = self._extract_keywords(task_description)
        
        for keyword in keywords:
            tools = self.tool_registry.find_by_capability(keyword)
            for tool in tools:
                requirements.add_required_tool(tool)
            
            task_tools = self.tool_registry.find_by_task(keyword)
            for tool in task_tools:
                requirements.add_optional_tool(tool)
        
        self._estimate_resources(requirements)
        
        return requirements
    
    def _extract_keywords(self, task_description: str) -> List[str]:
        """提取关键词"""
        keywords = []
        
        task_lower = task_description.lower()
        
        mcp_keywords = {
            '文件': 'file_operation',
            '读取': 'file_read',
            '写入': 'file_write',
            '创建': 'file_create',
            '删除': 'file_delete',
            '终端': 'terminal',
            '命令': 'command',
            'git': 'git',
            'github': 'git',
            '代码': 'code_execution',
            '执行': 'code_execution',
            '运行': 'code_execution',
        }
        
        skill_keywords = {
            '审查': 'code_review',
            '审核': 'code_review',
            '优化': 'code_optimization',
            '重构': 'code_refactoring',
            '生成': 'code_generation',
            '测试': 'testing',
            '文档': 'documentation',
            '设计': 'design',
            '架构': 'architecture',
        }
        
        knowledge_keywords = {
            'api': 'api_documentation',
            '技术': 'technical_knowledge',
            '最佳': 'best_practices',
            '指南': 'guides',
        }
        
        memory_keywords = {
            '记忆': 'short_term_memory',
            '历史': 'recent_history',
            '上下文': 'session_context',
        }
        
        for keyword, capability in {**mcp_keywords, **skill_keywords, **knowledge_keywords, **memory_keywords}.items():
            if keyword in task_lower:
                keywords.append(capability)
        
        return keywords
    
    def _estimate_resources(self, requirements: 'TaskRequirements') -> None:
        """估算资源消耗"""
        total_tokens = 0
        total_memory = 0
        total_time = 0
        
        for tool in requirements.required_tools:
            total_tokens += tool.resource_cost.tokens
            total_memory += tool.resource_cost.memory_mb
            total_time += tool.resource_cost.seconds
        
        requirements.resource_estimate = ResourceCost(
            tokens=total_tokens,
            memory_mb=total_memory,
            seconds=total_time
        )


@dataclass
class TaskRequirements:
    """任务需求"""
    task_description: str
    required_tools: List[ToolMetadata] = field(default_factory=list)
    optional_tools: List[ToolMetadata] = field(default_factory=list)
    priority_estimate: float = 0.5
    resource_estimate: ResourceCost = field(default_factory=ResourceCost)
    confidence: float = 0.8
    
    def add_required_tool(self, tool: ToolMetadata) -> None:
        """添加必需工具"""
        if tool not in self.required_tools:
            self.required_tools.append(tool)
    
    def add_optional_tool(self, tool: ToolMetadata) -> None:
        """添加可选工具"""
        if tool not in self.optional_tools and tool not in self.required_tools:
            self.optional_tools.append(tool)
    
    def has_tool(self, tool_id: str) -> bool:
        """检查是否包含工具"""
        return any(t.id == tool_id for t in self.required_tools + self.optional_tools)


class ToolMatcher:
    """工具匹配器"""
    
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
    
    def match(
        self,
        requirements: TaskRequirements,
        max_tools: int = 10,
        budget_tokens: int = 10000
    ) -> List[ToolMetadata]:
        """匹配工具"""
        candidates = []
        
        candidates.extend(requirements.required_tools)
        
        for tool in requirements.optional_tools:
            if not self._has_conflict(candidates, tool):
                candidates.append(tool)
        
        candidates = self._resolve_dependencies(candidates)
        
        candidates = self._filter_by_budget(candidates, budget_tokens)
        
        candidates = self._sort_by_priority(candidates, requirements)
        
        return candidates[:max_tools]
    
    def _has_conflict(self, selected: List[ToolMetadata], tool: ToolMetadata) -> bool:
        """检查冲突"""
        for selected_tool in selected:
            if selected_tool.id in tool.excludes or tool.id in selected_tool.excludes:
                return True
        return False
    
    def _resolve_dependencies(self, tools: List[ToolMetadata]) -> List[ToolMetadata]:
        """解析依赖"""
        result = list(tools)
        added = True
        
        while added:
            added = False
            for tool in list(result):
                for dep_id in tool.depends_on:
                    dep_tool = self.tool_registry.get(dep_id)
                    if dep_tool and dep_tool not in result:
                        result.append(dep_tool)
                        added = True
        
        return result
    
    def _filter_by_budget(self, tools: List[ToolMetadata], budget: int) -> List[ToolMetadata]:
        """按预算过滤"""
        sorted_tools = sorted(
            tools,
            key=lambda t: (t.success_rate, -t.resource_cost.tokens),
            reverse=True
        )
        
        result = []
        total_cost = 0
        
        for tool in sorted_tools:
            if total_cost + tool.resource_cost.tokens <= budget:
                result.append(tool)
                total_cost += tool.resource_cost.tokens
        
        return result
    
    def _sort_by_priority(
        self,
        tools: List[ToolMetadata],
        requirements: TaskRequirements
    ) -> List[ToolMetadata]:
        """按优先级排序"""
        def priority_score(tool: ToolMetadata) -> float:
            score = tool.success_rate * 0.5
            
            if tool in requirements.required_tools:
                score += 0.3
            
            score += (1 - tool.resource_cost.tokens / 1000) * 0.2
            
            return score
        
        return sorted(tools, key=priority_score, reverse=True)


class AgentEquipmentContext:
    """Agent装备上下文"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.equipped_tools: List[ToolMetadata] = []
        self.last_equipped_at: Optional[datetime] = None
        self.resource_usage: Dict[str, float] = {}
    
    def equip(self, tools: List[ToolMetadata]) -> List[str]:
        """装备工具"""
        equipped_ids = []
        
        for tool in tools:
            if tool not in self.equipped_tools:
                if not self._has_conflict(tool):
                    self.equipped_tools.append(tool)
                    equipped_ids.append(tool.id)
        
        self.last_equipped_at = datetime.now()
        return equipped_ids
    
    def unequip(self, tool_id: str) -> bool:
        """卸载工具"""
        for i, tool in enumerate(self.equipped_tools):
            if tool.id == tool_id:
                del self.equipped_tools[i]
                return True
        return False
    
    def unequip_all(self) -> None:
        """卸载所有工具"""
        self.equipped_tools.clear()
    
    def _has_conflict(self, tool: ToolMetadata) -> bool:
        """检查冲突"""
        for equipped in self.equipped_tools:
            if equipped.id in tool.excludes or tool.id in equipped.excludes:
                return True
        return False
    
    def get_equipped_capabilities(self) -> List[str]:
        """获取已装备的能力"""
        capabilities = []
        for tool in self.equipped_tools:
            capabilities.extend(tool.capabilities)
        return list(set(capabilities))
    
    def can_perform(self, capability: str) -> bool:
        """检查是否具备能力"""
        return capability in self.get_equipped_capabilities()


class EquipmentService:
    """装备服务"""
    
    def __init__(self):
        self.tool_registry = ToolRegistry()
        self.task_analyzer = TaskAnalyzer(self.tool_registry)
        self.tool_matcher = ToolMatcher(self.tool_registry)
        self.agent_contexts: Dict[str, AgentEquipmentContext] = {}
    
    def register_tool(self, tool: ToolMetadata) -> None:
        """注册工具"""
        self.tool_registry.register(tool)
    
    def analyze_and_equip(self, agent_id: str, task_description: str) -> Tuple[List[str], float]:
        """分析任务并自动装备工具"""
        requirements = self.task_analyzer.analyze(task_description)
        
        matched_tools = self.tool_matcher.match(requirements)
        
        if agent_id not in self.agent_contexts:
            self.agent_contexts[agent_id] = AgentEquipmentContext(agent_id)
        
        context = self.agent_contexts[agent_id]
        equipped_ids = context.equip(matched_tools)
        
        return equipped_ids, requirements.confidence
    
    def get_agent_equipment(self, agent_id: str) -> Optional[AgentEquipmentContext]:
        """获取Agent装备上下文"""
        return self.agent_contexts.get(agent_id)
    
    def update_tool_usage(self, agent_id: str, tool_id: str, success: bool, execution_time: float) -> None:
        """更新工具使用统计"""
        self.tool_registry.update_usage_stats(tool_id, success, execution_time)


# 全局装备服务实例
equipment_service = EquipmentService()
