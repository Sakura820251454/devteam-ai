"""
知识进化模块测试 - Phase 5.4

测试知识进化服务的核心功能
"""

import pytest

from app.services.knowledge.knowledge_evolution import (
    knowledge_evolution_service,
    KnowledgeExtractor,
    PatternDiscoverer,
    SkillGenerator,
    KnowledgeEvolutionService,
    ImplicitKnowledge,
    ExplicitKnowledge,
    KnowledgeType,
    KnowledgeConfidence,
    ImplicitKnowledgeType,
    ExplicitKnowledgeType,
)


class TestKnowledgeExtractor:
    """知识提取器测试"""
    
    def test_extract_consensus(self):
        """测试提取讨论共识"""
        extractor = KnowledgeExtractor()
        content = "经过讨论，我们决定采用微服务架构。这个方案更加灵活。"
        
        knowledge = extractor._extract_consensus(content)
        
        assert knowledge is not None
        assert "决定" in knowledge.title
        assert knowledge.implicit_type == ImplicitKnowledgeType.DISCUSSION_CONSENSUS
    
    def test_extract_solutions(self):
        """测试提取解决方案"""
        extractor = KnowledgeExtractor()
        content = "这个问题的解决方案是使用缓存。解决方案已验证成功。"
        
        solutions = extractor._extract_solutions(content)
        
        assert len(solutions) >= 1
        assert any("解决方案" in s.title for s in solutions)
    
    def test_extract_success_case(self):
        """测试提取成功案例"""
        extractor = KnowledgeExtractor()
        
        knowledge = extractor.extract_success_case(
            task_description="优化数据库查询",
            context="订单查询慢",
            method="添加索引；优化SQL",
            effect="查询速度提升10倍",
            success_factors=["索引", "SQL优化"],
            agent_id="agent_001",
            task_type="性能优化",
        )
        
        assert knowledge is not None
        assert knowledge.implicit_type == ImplicitKnowledgeType.SUCCESS_CASE
        assert knowledge.success_factors == ["索引", "SQL优化"]
    
    def test_extract_failure_lesson(self):
        """测试提取失败教训"""
        extractor = KnowledgeExtractor()
        
        knowledge = extractor.extract_failure_lesson(
            task_description="API响应慢",
            problem="数据库连接池耗尽",
            failed_attempts=["增加线程数", "增加超时时间"],
            final_solution="增加连接池大小",
            prevention_tips=["监控连接池", "设置告警"],
            agent_id="agent_001",
        )
        
        assert knowledge is not None
        assert knowledge.implicit_type == ImplicitKnowledgeType.FAILURE_LESSON
        assert knowledge.prevention_tips == ["监控连接池", "设置告警"]
    
    def test_extract_code_snippet(self):
        """测试提取代码片段"""
        extractor = KnowledgeExtractor()
        
        knowledge = extractor.extract_code_snippet(
            code="def hello():\n    print('Hello')",
            description="简单的Hello函数",
            language="python",
            use_case="演示",
            agent_id="agent_001",
        )
        
        assert knowledge is not None
        assert knowledge.explicit_type == ExplicitKnowledgeType.CODE_SNIPPET
        assert knowledge.code_language == "python"
        assert "python" in knowledge.tags


class TestPatternDiscoverer:
    """模式发现器测试"""
    
    def test_find_success_patterns(self):
        """测试发现成功模式"""
        discoverer = PatternDiscoverer()
        
        task_history = [
            {"success": True, "task_type": "代码审查"},
            {"success": True, "task_type": "代码审查"},
            {"success": True, "task_type": "代码审查"},
        ]
        
        patterns = discoverer._find_success_patterns(task_history)
        
        assert len(patterns) >= 1
        assert patterns[0].pattern_type == "success_feature"
    
    def test_find_trap_patterns(self):
        """测试发现陷阱模式"""
        discoverer = PatternDiscoverer()
        
        task_history = [
            {"success": False, "id": "t1"},
            {"success": False, "id": "t2"},
        ]
        
        patterns = discoverer._find_trap_patterns(task_history)
        
        assert len(patterns) >= 1
        assert patterns[0].pattern_type == "trap"


class TestSkillGenerator:
    """技能生成器测试"""
    
    def test_generate_skill_from_cases(self):
        """测试从案例生成技能"""
        extractor = KnowledgeExtractor()
        generator = SkillGenerator(extractor)
        
        case1 = extractor.extract_success_case(
            task_description="代码审查任务1",
            context="审查Python代码",
            method="检查代码规范；运行测试",
            effect="发现3个问题",
            success_factors=["规范检查", "测试"],
            agent_id="agent_001",
            task_type="代码审查",
        )
        
        case2 = extractor.extract_success_case(
            task_description="代码审查任务2",
            context="审查Python代码",
            method="检查代码规范；审查逻辑",
            effect="发现2个问题",
            success_factors=["规范检查", "逻辑审查"],
            agent_id="agent_001",
            task_type="代码审查",
        )
        
        skill = generator.generate_skill_from_cases([case1, case2], "agent_001")
        
        assert skill is not None
        assert "代码审查" in skill.name
        assert len(skill.process_steps) > 0
        assert len(skill.checklist) > 0


class TestKnowledgeEvolutionService:
    """知识进化服务测试"""
    
    def test_add_and_get_knowledge(self):
        """测试添加和获取知识"""
        service = KnowledgeEvolutionService()
        
        knowledge = ImplicitKnowledge(
            id="test_knowledge",
            title="测试知识",
            content="测试内容",
            implicit_type=ImplicitKnowledgeType.SOLUTION,
            confidence=KnowledgeConfidence.HIGH,
        )
        
        service.add_knowledge(knowledge)
        
        retrieved = service.get_knowledge("test_knowledge")
        
        assert retrieved is not None
        assert retrieved.title == "测试知识"
    
    def test_search_knowledge(self):
        """测试搜索知识"""
        service = KnowledgeEvolutionService()
        
        knowledge1 = ImplicitKnowledge(
            id="k1",
            title="数据库优化技巧",
            content="使用索引优化查询",
            implicit_type=ImplicitKnowledgeType.SOLUTION,
            confidence=KnowledgeConfidence.HIGH,
            tags=["database", "optimization"],
        )
        
        knowledge2 = ImplicitKnowledge(
            id="k2",
            title="API设计指南",
            content="RESTful API设计原则",
            implicit_type=ImplicitKnowledgeType.SOLUTION,
            confidence=KnowledgeConfidence.HIGH,
            tags=["api", "design"],
        )
        
        service.add_knowledge(knowledge1)
        service.add_knowledge(knowledge2)
        
        results = service.search_knowledge("数据库")
        
        assert len(results) >= 1
        assert any(r[0].id == "k1" for r in results)
    
    def test_extract_and_save(self):
        """测试提取并保存知识"""
        service = KnowledgeEvolutionService()
        
        content = "经过讨论，我们决定采用缓存方案。解决方案是使用Redis缓存。"
        
        knowledge_ids = service.extract_and_save(content, "agent_001")
        
        assert len(knowledge_ids) > 0
        
        stats = service.get_knowledge_stats()
        assert stats["total_knowledge"] == len(knowledge_ids)
    
    def test_discover_patterns(self):
        """测试发现模式"""
        service = KnowledgeEvolutionService()
        
        task_history = [
            {"success": True, "task_type": "代码审查", "id": "t1"},
            {"success": True, "task_type": "代码审查", "id": "t2"},
            {"success": True, "task_type": "代码审查", "id": "t3"},
        ]
        
        count = service.discover_and_save_patterns(task_history)
        
        assert count >= 1
        assert len(service.patterns) >= 1
    
    def test_generate_skills(self):
        """测试生成技能"""
        service = KnowledgeEvolutionService()
        extractor = KnowledgeExtractor()
        
        case1 = extractor.extract_success_case(
            task_description="测试审查1",
            context="审查",
            method="检查代码",
            effect="发现问题",
            success_factors=["检查"],
            agent_id="agent_001",
            task_type="代码审查",
        )
        
        case2 = extractor.extract_success_case(
            task_description="测试审查2",
            context="审查",
            method="检查代码",
            effect="发现问题",
            success_factors=["检查"],
            agent_id="agent_001",
            task_type="代码审查",
        )
        
        service.add_knowledge(case1)
        service.add_knowledge(case2)
        
        skills = service.generate_skills("agent_001")
        
        assert len(skills) >= 1
        assert "代码审查" in skills[0].name
    
    def test_use_knowledge(self):
        """测试使用知识"""
        service = KnowledgeEvolutionService()
        
        knowledge = ImplicitKnowledge(
            id="use_test",
            title="测试使用",
            content="测试内容",
            implicit_type=ImplicitKnowledgeType.SOLUTION,
            confidence=KnowledgeConfidence.HIGH,
        )
        
        service.add_knowledge(knowledge)
        
        retrieved = service.get_knowledge("use_test")
        retrieved.use(True)
        retrieved.use(False)
        retrieved.use(True)
        
        assert retrieved.usage_count == 3
        assert retrieved.success_count == 2
        assert retrieved.success_rate == 2/3


class TestIntegration:
    """集成测试"""
    
    def test_full_knowledge_flow(self):
        """测试完整知识进化流程"""
        service = KnowledgeEvolutionService()
        
        content = "经过讨论，我们决定使用Redis缓存来优化API响应速度。解决方案已验证成功。"
        
        knowledge_ids = service.extract_and_save(content, "agent_001", "性能优化")
        
        assert len(knowledge_ids) > 0
        
        results = service.search_knowledge("缓存")
        assert len(results) >= 1
        
        task_history = [
            {"success": True, "task_type": "性能优化", "id": "t1"},
            {"success": True, "task_type": "性能优化", "id": "t2"},
            {"success": True, "task_type": "性能优化", "id": "t3"},
        ]
        
        pattern_count = service.discover_and_save_patterns(task_history)
        assert pattern_count >= 1
        
        stats = service.get_knowledge_stats()
        assert stats["total_knowledge"] == len(knowledge_ids)
        assert stats["patterns_discovered"] == pattern_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
