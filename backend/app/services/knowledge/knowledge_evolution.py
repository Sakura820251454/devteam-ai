"""
知识进化模块 - Phase 5.4

实现设计文档3.6节定义的知识进化系统：
1. 知识类型体系 - 显性知识和隐性知识
2. 自动知识提取 - 从讨论和任务中提取知识
3. 模式发现与技能生成 - 从历史数据中发现模式，生成可复用技能
4. 知识检索与应用 - 按相关性和置信度排序

核心价值: 将Agent执行任务过程中的可复用、有价值的技能和知识沉淀成资产
"""

from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import re


class KnowledgeType(str, Enum):
    """知识类型"""
    EXPLICIT = "explicit"       # 显性知识
    IMPLICIT = "implicit"       # 隐性知识


class ExplicitKnowledgeType(str, Enum):
    """显性知识类型"""
    TECHNICAL_DOC = "technical_doc"       # 技术文档
    BEST_PRACTICE = "best_practice"      # 最佳实践
    CODE_SNIPPET = "code_snippet"        # 代码片段
    API_SPEC = "api_spec"                 # API规范
    TEST_CASE = "test_case"               # 测试用例


class ImplicitKnowledgeType(str, Enum):
    """隐性知识类型"""
    DISCUSSION_CONSENSUS = "consensus"     # 讨论共识
    SOLUTION = "solution"                 # 问题解决方案
    SUCCESS_CASE = "success_case"        # 成功案例
    FAILURE_LESSON = "failure_lesson"    # 失败教训
    COLLABORATION_PATTERN = "collab_pattern"  # 协作模式
    DISCOVERED_PATTERN = "discovered_pattern"  # 发现的模式


class KnowledgeConfidence(str, Enum):
    """知识置信度"""
    HIGH = "high"     # 高置信度，可直接推荐
    MEDIUM = "medium" # 中置信度，建议参考
    LOW = "low"      # 低置信度，需人工确认


@dataclass
class KnowledgeAsset:
    """知识资产基类"""
    id: str
    title: str
    content: str
    knowledge_type: Optional[KnowledgeType] = None
    confidence: KnowledgeConfidence = KnowledgeConfidence.MEDIUM
    usage_count: int = 0
    success_count: int = 0
    success_rate: float = 0.0
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""  # Agent ID
    related_task_types: List[str] = field(default_factory=list)
    source: str = ""  # 来源描述
    
    def use(self, success: bool) -> None:
        """使用知识资产"""
        self.usage_count += 1
        if success:
            self.success_count += 1
        self.success_rate = self.success_count / self.usage_count if self.usage_count > 0 else 0.0


@dataclass
class ExplicitKnowledge(KnowledgeAsset):
    """显性知识"""
    explicit_type: Optional[ExplicitKnowledgeType] = None
    domain: str = ""  # 领域
    tech_stack: List[str] = field(default_factory=list)  # 技术栈
    code_language: str = ""  # 编程语言
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.knowledge_type = KnowledgeType.EXPLICIT


@dataclass
class ImplicitKnowledge(KnowledgeAsset):
    """隐性知识"""
    implicit_type: Optional[ImplicitKnowledgeType] = None
    context: str = ""  # 上下文描述
    method: str = ""  # 采取的方法
    effect: str = ""  # 取得的效果
    success_factors: List[str] = field(default_factory=list)  # 成功因素
    failure_factors: List[str] = field(default_factory=list)  # 失败因素
    prevention_tips: List[str] = field(default_factory=list)  # 预防建议
    
    def __post_init__(self):
        self.knowledge_type = KnowledgeType.IMPLICIT


@dataclass
class SkillFromKnowledge:
    """从知识生成的技能"""
    id: str
    name: str
    description: str
    source_knowledge_id: str
    process_steps: List[str] = field(default_factory=list)  # 标准化流程
    checklist: List[str] = field(default_factory=list)  # 检查清单
    template: str = ""  # 报告模板
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class DiscoveredPattern:
    """发现的模式"""
    id: str
    name: str
    description: str
    pattern_type: str  # 成功特征/协作方式/技术方案/陷阱
    evidence_count: int = 0  # 支持证据数量
    confidence: float = 0.0  # 置信度
    discovered_at: datetime = field(default_factory=datetime.now)
    related_knowledge_ids: List[str] = field(default_factory=list)


class KnowledgeExtractor:
    """知识提取器"""
    
    def __init__(self):
        self.min_confidence_threshold = 0.6
    
    def extract_from_discussion(
        self,
        discussion_content: str,
        agent_id: str,
        task_type: str = ""
    ) -> List[ImplicitKnowledge]:
        """从讨论中提取知识"""
        knowledge_list = []
        
        consensus = self._extract_consensus(discussion_content)
        if consensus:
            knowledge_list.append(consensus)
        
        solutions = self._extract_solutions(discussion_content)
        knowledge_list.extend(solutions)
        
        patterns = self._extract_collaboration_patterns(discussion_content)
        knowledge_list.extend(patterns)
        
        for k in knowledge_list:
            k.created_by = agent_id
            k.related_task_types = [task_type] if task_type else []
        
        return knowledge_list
    
    def _extract_consensus(self, content: str) -> Optional[ImplicitKnowledge]:
        """提取讨论共识"""
        consensus_keywords = [
            "决定", "共识", "方案确定", "结论", "最终方案",
            "采用", "选择", "同意", "确认"
        ]
        
        for keyword in consensus_keywords:
            if keyword in content:
                sentences = content.split("。")
                for sentence in sentences:
                    if keyword in sentence and len(sentence) > 10:
                        return ImplicitKnowledge(
                            id=f"know_{uuid.uuid4().hex[:8]}",
                            title=f"讨论共识: {sentence[:30]}...",
                            content=sentence,
                            implicit_type=ImplicitKnowledgeType.DISCUSSION_CONSENSUS,
                            confidence=KnowledgeConfidence.MEDIUM,
                            source="讨论摘要提取",
                        )
        
        return None
    
    def _extract_solutions(self, content: str) -> List[ImplicitKnowledge]:
        """提取解决方案"""
        solutions = []
        solution_keywords = ["解决方案", "解决方法", "处理方式", "修复方法", "方案是"]
        
        sentences = content.split("。")
        for sentence in sentences:
            for keyword in solution_keywords:
                if keyword in sentence and len(sentence) > 5:
                    solutions.append(ImplicitKnowledge(
                        id=f"know_{uuid.uuid4().hex[:8]}",
                        title=f"解决方案: {sentence[:30]}...",
                        content=sentence,
                        implicit_type=ImplicitKnowledgeType.SOLUTION,
                        confidence=KnowledgeConfidence.HIGH if "成功" in sentence else KnowledgeConfidence.MEDIUM,
                        source="问题解决记录",
                    ))
                    break
        
        return solutions
    
    def _extract_collaboration_patterns(self, content: str) -> List[ImplicitKnowledge]:
        """提取协作模式"""
        patterns = []
        
        if any(word in content for word in ["协作", "配合", "分工", "合作"]):
            patterns.append(ImplicitKnowledge(
                id=f"know_{uuid.uuid4().hex[:8]}",
                title="发现的协作模式",
                content=content[:500],
                implicit_type=ImplicitKnowledgeType.COLLABORATION_PATTERN,
                confidence=KnowledgeConfidence.MEDIUM,
                source="协作模式发现",
            ))
        
        return patterns
    
    def extract_success_case(
        self,
        task_description: str,
        context: str,
        method: str,
        effect: str,
        success_factors: List[str],
        agent_id: str,
        task_type: str = ""
    ) -> ImplicitKnowledge:
        """提取成功案例"""
        return ImplicitKnowledge(
            id=f"know_{uuid.uuid4().hex[:8]}",
            title=f"成功案例: {task_description[:50]}",
            content=f"任务: {task_description}\n\n上下文: {context}\n\n方法: {method}\n\n效果: {effect}",
            implicit_type=ImplicitKnowledgeType.SUCCESS_CASE,
            confidence=KnowledgeConfidence.HIGH,
            context=context,
            method=method,
            effect=effect,
            success_factors=success_factors,
            created_by=agent_id,
            related_task_types=[task_type] if task_type else [],
            source="成功案例记录",
        )
    
    def extract_failure_lesson(
        self,
        task_description: str,
        problem: str,
        failed_attempts: List[str],
        final_solution: str,
        prevention_tips: List[str],
        agent_id: str,
        task_type: str = ""
    ) -> ImplicitKnowledge:
        """提取失败教训"""
        return ImplicitKnowledge(
            id=f"know_{uuid.uuid4().hex[:8]}",
            title=f"失败教训: {task_description[:50]}",
            content=f"问题: {problem}\n\n失败尝试: {'; '.join(failed_attempts)}\n\n最终方案: {final_solution}",
            implicit_type=ImplicitKnowledgeType.FAILURE_LESSON,
            confidence=KnowledgeConfidence.MEDIUM,
            context=problem,
            failure_factors=failed_attempts,
            prevention_tips=prevention_tips,
            created_by=agent_id,
            related_task_types=[task_type] if task_type else [],
            source="失败教训记录",
        )
    
    def extract_code_snippet(
        self,
        code: str,
        description: str,
        language: str,
        use_case: str,
        agent_id: str
    ) -> ExplicitKnowledge:
        """提取代码片段"""
        tags = self._extract_tags(code, description)
        
        return ExplicitKnowledge(
            id=f"know_{uuid.uuid4().hex[:8]}",
            title=f"代码片段: {description[:50]}",
            content=code,
            explicit_type=ExplicitKnowledgeType.CODE_SNIPPET,
            confidence=KnowledgeConfidence.HIGH,
            code_language=language,
            metadata={"use_case": use_case},
            tags=tags,
            created_by=agent_id,
            source="代码片段提取",
        )
    
    def _extract_tags(self, code: str, description: str) -> List[str]:
        """提取标签"""
        tags = []
        
        language_patterns = {
            "python": [r"def\s+\w+", r"import\s+\w+", r"class\s+\w+"],
            "javascript": [r"function\s+\w+", r"const\s+\w+", r"=>"],
            "typescript": [r"interface\s+\w+", r"type\s+\w+", r":\s*\w+\[\]"],
            "sql": [r"SELECT\s+", r"FROM\s+", r"WHERE\s+"],
        }
        
        for lang, patterns in language_patterns.items():
            for pattern in patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    if lang not in tags:
                        tags.append(lang)
                    break
        
        important_keywords = ["api", "database", "cache", "auth", "config", "error"]
        for keyword in important_keywords:
            if keyword in code.lower() or keyword in description.lower():
                if keyword not in tags:
                    tags.append(keyword)
        
        return tags


class PatternDiscoverer:
    """模式发现器"""
    
    def __init__(self):
        self.min_evidence_count = 3
    
    def discover_patterns(
        self,
        knowledge_assets: List[KnowledgeAsset],
        task_history: List[Dict[str, Any]]
    ) -> List[DiscoveredPattern]:
        """从知识资产和任务历史中发现模式"""
        patterns = []
        
        success_patterns = self._find_success_patterns(task_history)
        patterns.extend(success_patterns)
        
        collab_patterns = self._find_collaboration_patterns(task_history)
        patterns.extend(collab_patterns)
        
        tech_patterns = self._find_tech_patterns(knowledge_assets)
        patterns.extend(tech_patterns)
        
        trap_patterns = self._find_trap_patterns(task_history)
        patterns.extend(trap_patterns)
        
        return patterns
    
    def _find_success_patterns(self, task_history: List[Dict[str, Any]]) -> List[DiscoveredPattern]:
        """发现成功模式"""
        patterns = []
        
        successful_tasks = [t for t in task_history if t.get("success", False)]
        
        if len(successful_tasks) >= self.min_evidence_count:
            common_features = self._find_common_features(successful_tasks)
            
            patterns.append(DiscoveredPattern(
                id=f"pattern_{uuid.uuid4().hex[:8]}",
                name="成功任务共同特征",
                description=f"发现{len(successful_tasks)}个成功任务的共同特征: {', '.join(common_features[:3])}",
                pattern_type="success_feature",
                evidence_count=len(successful_tasks),
                confidence=min(0.9, len(successful_tasks) * 0.2),
                related_knowledge_ids=[t.get("id", "") for t in successful_tasks[:5]],
            ))
        
        return patterns
    
    def _find_common_features(self, tasks: List[Dict[str, Any]]) -> List[str]:
        """查找共同特征"""
        features = []
        
        task_types = [t.get("task_type") for t in tasks if t.get("task_type")]
        if len(set(task_types)) == 1:
            features.append(f"任务类型: {task_types[0]}")
        
        agents = [t.get("agent_id") for t in tasks if t.get("agent_id")]
        if len(set(agents)) <= 2:
            features.append("少量Agent协作")
        
        return features
    
    def _find_collaboration_patterns(self, task_history: List[Dict[str, Any]]) -> List[DiscoveredPattern]:
        """发现协作模式"""
        patterns = []
        
        if len(task_history) >= 5:
            patterns.append(DiscoveredPattern(
                id=f"pattern_{uuid.uuid4().hex[:8]}",
                name="高效协作模式",
                description="多Agent协作完成任务",
                pattern_type="collaboration_mode",
                evidence_count=len(task_history),
                confidence=0.7,
            ))
        
        return patterns
    
    def _find_tech_patterns(self, knowledge_assets: List[KnowledgeAsset]) -> List[DiscoveredPattern]:
        """发现技术模式"""
        patterns = []
        
        code_snippets = [k for k in knowledge_assets if isinstance(k, ExplicitKnowledge) and k.explicit_type == ExplicitKnowledgeType.CODE_SNIPPET]
        
        if len(code_snippets) >= 3:
            common_langs = self._most_common([s.code_language for s in code_snippets])
            
            patterns.append(DiscoveredPattern(
                id=f"pattern_{uuid.uuid4().hex[:8]}",
                name=f"常用技术栈: {', '.join(common_langs[:2])}",
                description=f"项目中频繁使用的技术栈",
                pattern_type="technical_solution",
                evidence_count=len(code_snippets),
                confidence=0.8,
                related_knowledge_ids=[s.id for s in code_snippets[:5]],
            ))
        
        return patterns
    
    def _find_trap_patterns(self, task_history: List[Dict[str, Any]]) -> List[DiscoveredPattern]:
        """发现陷阱模式"""
        patterns = []
        
        failed_tasks = [t for t in task_history if not t.get("success", True)]
        
        if len(failed_tasks) >= 2:
            patterns.append(DiscoveredPattern(
                id=f"pattern_{uuid.uuid4().hex[:8]}",
                name="需要避免的陷阱",
                description=f"发现{len(failed_tasks)}个失败案例，需要避免的模式",
                pattern_type="trap",
                evidence_count=len(failed_tasks),
                confidence=0.6,
                related_knowledge_ids=[t.get("id", "") for t in failed_tasks[:3]],
            ))
        
        return patterns
    
    def _most_common(self, items: List[str]) -> List[str]:
        """获取最常见的元素"""
        from collections import Counter
        counter = Counter(items)
        return [item for item, count in counter.most_common(3)]


class SkillGenerator:
    """技能生成器"""
    
    def __init__(self, knowledge_extractor: KnowledgeExtractor):
        self.knowledge_extractor = knowledge_extractor
    
    def generate_skill_from_cases(
        self,
        success_cases: List[ImplicitKnowledge],
        agent_id: str
    ) -> Optional[SkillFromKnowledge]:
        """从多个成功案例生成技能"""
        if len(success_cases) < 2:
            return None
        
        similar_cases = self._group_similar_cases(success_cases)
        
        if len(similar_cases) < 2:
            return None
        
        skill_name = self._generate_skill_name(similar_cases)
        process_steps = self._extract_process_steps(similar_cases)
        checklist = self._extract_checklist(similar_cases)
        
        return SkillFromKnowledge(
            id=f"skill_{uuid.uuid4().hex[:8]}",
            name=skill_name,
            description=f"从{len(similar_cases)}个成功案例提炼的技能",
            source_knowledge_id=similar_cases[0].id,
            process_steps=process_steps,
            checklist=checklist,
            template=self._generate_template(skill_name, process_steps),
        )
    
    def _group_similar_cases(self, cases: List[ImplicitKnowledge]) -> List[ImplicitKnowledge]:
        """分组相似案例"""
        if not cases:
            return []
        
        if len(cases) >= 2:
            return cases
        
        return cases
    
    def _generate_skill_name(self, cases: List[ImplicitKnowledge]) -> str:
        """生成技能名称"""
        task_types = [t for t in cases[0].related_task_types if t] if cases else []
        
        if task_types:
            return f"专业{task_types[0]}技能"
        
        if cases:
            first_title = cases[0].title
            if "代码审查" in first_title:
                return "标准化代码审查技能"
            if "测试" in first_title:
                return "自动化测试技能"
            if "优化" in first_title:
                return "性能优化技能"
        
        return "专业任务处理技能"
    
    def _extract_process_steps(self, cases: List[ImplicitKnowledge]) -> List[str]:
        """提取流程步骤"""
        steps = []
        
        for case in cases:
            if case.method:
                steps.extend(case.method.split(";")[:3])
        
        unique_steps = list(dict.fromkeys(steps))[:5]
        
        if not unique_steps:
            unique_steps = [
                "1. 分析任务需求",
                "2. 制定执行计划",
                "3. 逐步实施",
                "4. 验证结果",
                "5. 总结经验",
            ]
        
        return unique_steps
    
    def _extract_checklist(self, cases: List[ImplicitKnowledge]) -> List[str]:
        """提取检查清单"""
        checklist = []
        
        for case in cases:
            if case.success_factors:
                checklist.extend(case.success_factors[:2])
        
        unique_items = list(dict.fromkeys(checklist))[:5]
        
        if not unique_items:
            unique_items = [
                "✓ 确认任务目标清晰",
                "✓ 检查输入数据完整",
                "✓ 验证输出结果正确",
            ]
        
        return unique_items
    
    def _generate_template(self, skill_name: str, steps: List[str]) -> str:
        """生成报告模板"""
        template = f"""# {skill_name} 报告

## 任务描述
[在此填写]

## 执行步骤
"""
        for i, step in enumerate(steps, 1):
            template += f"{i}. {step}\n"
        
        template += """
## 检查清单
[在此勾选]

## 结果
[在此填写]

## 经验总结
[在此填写]
"""
        return template


class KnowledgeEvolutionService:
    """知识进化服务"""
    
    def __init__(self):
        self.knowledge_base: Dict[str, KnowledgeAsset] = {}
        self.patterns: List[DiscoveredPattern] = []
        self.generated_skills: Dict[str, SkillFromKnowledge] = {}
        
        self.extractor = KnowledgeExtractor()
        self.pattern_discoverer = PatternDiscoverer()
        self.skill_generator = SkillGenerator(self.extractor)
    
    def add_knowledge(self, knowledge: KnowledgeAsset) -> str:
        """添加知识资产"""
        self.knowledge_base[knowledge.id] = knowledge
        return knowledge.id
    
    def get_knowledge(self, knowledge_id: str) -> Optional[KnowledgeAsset]:
        """获取知识资产"""
        return self.knowledge_base.get(knowledge_id)
    
    def search_knowledge(
        self,
        query: str,
        knowledge_type: Optional[KnowledgeType] = None,
        min_confidence: Optional[KnowledgeConfidence] = None,
        limit: int = 10
    ) -> List[Tuple[KnowledgeAsset, float]]:
        """搜索知识资产（按相关性排序）"""
        results = []
        
        for knowledge in self.knowledge_base.values():
            if knowledge_type and knowledge.knowledge_type is not None and knowledge.knowledge_type != knowledge_type:
                continue
            
            if min_confidence:
                confidence_order = {
                    KnowledgeConfidence.HIGH: 3,
                    KnowledgeConfidence.MEDIUM: 2,
                    KnowledgeConfidence.LOW: 1,
                }
                if confidence_order.get(knowledge.confidence, 0) < confidence_order.get(min_confidence, 0):
                    continue
            
            relevance = self._calculate_relevance(query, knowledge)
            
            if relevance > 0.1:
                results.append((knowledge, relevance))
        
        results.sort(key=lambda x: (x[1], x[0].success_rate), reverse=True)
        
        return results[:limit]
    
    def _calculate_relevance(self, query: str, knowledge: KnowledgeAsset) -> float:
        """计算相关性"""
        query_lower = query.lower()
        content_lower = knowledge.content.lower()
        title_lower = knowledge.title.lower()
        
        relevance = 0.0
        
        query_words = set(query_lower.split())
        
        if not query_words:
            return 0.0
        
        content_words = set(content_lower.split())
        title_words = set(title_lower.split())
        
        title_match = len(query_words & title_words) / len(query_words)
        relevance += title_match * 0.5
        
        content_match = len(query_words & content_words) / len(query_words)
        relevance += content_match * 0.3
        
        for tag in knowledge.tags:
            if tag.lower() in query_lower:
                relevance += 0.2
                break
        
        if query_lower in content_lower or query_lower in title_lower:
            relevance += 0.2
        
        return min(1.0, relevance)
    
    def extract_and_save(
        self,
        content: str,
        agent_id: str,
        task_type: str = ""
    ) -> List[str]:
        """提取并保存知识"""
        knowledge_list = self.extractor.extract_from_discussion(
            content, agent_id, task_type
        )
        
        knowledge_ids = []
        for knowledge in knowledge_list:
            kid = self.add_knowledge(knowledge)
            knowledge_ids.append(kid)
        
        return knowledge_ids
    
    def discover_and_save_patterns(self, task_history: List[Dict[str, Any]]) -> int:
        """发现并保存模式"""
        patterns = self.pattern_discoverer.discover_patterns(
            list(self.knowledge_base.values()),
            task_history
        )
        
        for pattern in patterns:
            self.patterns.append(pattern)
        
        return len(patterns)
    
    def generate_skills(self, agent_id: str) -> List[SkillFromKnowledge]:
        """生成技能（从多个相似成功案例）"""
        success_cases = [
            k for k in self.knowledge_base.values()
            if isinstance(k, ImplicitKnowledge) and k.implicit_type == ImplicitKnowledgeType.SUCCESS_CASE
        ]
        
        generated = self.skill_generator.generate_skill_from_cases(success_cases, agent_id)
        
        if generated:
            self.generated_skills[generated.id] = generated
            return [generated]
        
        return []
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """获取知识库统计"""
        explicit_count = sum(
            1 for k in self.knowledge_base.values()
            if isinstance(k, ExplicitKnowledge)
        )
        implicit_count = sum(
            1 for k in self.knowledge_base.values()
            if isinstance(k, ImplicitKnowledge)
        )
        
        return {
            "total_knowledge": len(self.knowledge_base),
            "explicit_knowledge": explicit_count,
            "implicit_knowledge": implicit_count,
            "patterns_discovered": len(self.patterns),
            "skills_generated": len(self.generated_skills),
            "avg_success_rate": sum(k.success_rate for k in self.knowledge_base.values()) / len(self.knowledge_base) if self.knowledge_base else 0,
        }


knowledge_evolution_service = KnowledgeEvolutionService()
