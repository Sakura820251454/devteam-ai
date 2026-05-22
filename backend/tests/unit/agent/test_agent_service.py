"""
Agent 服务单元测试
"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.services.agent.agent_service import AgentService, AgentType, AgentTemplate
from app.services.shared.soul_parser import SoulFile


class TestAgentService:
    """Agent 服务测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.service = AgentService()
    
    def test_service_initialization(self):
        """测试服务初始化"""
        assert self.service is not None
        # 应该加载了模板
        templates = self.service.get_all_templates()
        assert len(templates) > 0
    
    def test_get_all_templates(self):
        """测试获取所有模板"""
        templates = self.service.get_all_templates()
        
        assert isinstance(templates, list)
        assert len(templates) > 0
        
        # 检查模板结构
        for template in templates:
            assert "id" in template
            assert "name" in template
            assert "type" in template
            assert "system_prompt" in template
    
    def test_get_template_by_id(self):
        """测试通过 ID 获取模板"""
        # 先获取一个存在的模板 ID
        all_templates = self.service.get_all_templates()
        if all_templates:
            template_id = all_templates[0]["id"]
            template = self.service.get_template(template_id)
            
            assert template is not None
            assert template["id"] == template_id
    
    def test_get_template_not_found(self):
        """测试获取不存在的模板"""
        template = self.service.get_template("nonexistent_id")
        assert template is None
    
    def test_get_templates_by_type(self):
        """测试按类型获取模板"""
        templates = self.service.get_templates_by_type(AgentType.BACKEND)
        
        assert isinstance(templates, list)
        # 应该包含后端相关的模板
        for template in templates:
            assert template["type"] == "backend_developer"
    
    def test_get_templates_by_tag(self):
        """测试按标签获取模板"""
        templates = self.service.get_templates_by_tag("后端")
        
        assert isinstance(templates, list)
    
    def test_create_custom_template(self):
        """测试创建自定义模板"""
        template_data = {
            "name": "测试模板",
            "type": "custom",
            "description": "用于测试的模板",
            "system_prompt": "你是一个测试 Agent",
            "capabilities": ["测试"],
            "collaboration_style": "协作型",
            "speaking_tendency": "简洁型",
            "tags": ["测试", "自定义"]
        }
        
        template = self.service.create_custom_template(template_data)
        
        assert template["name"] == "测试模板"
        assert template["type"] == "custom"
        assert "测试" in template["tags"]
        assert template["is_preset"] is False
    
    def test_create_agent_from_template(self):
        """测试从模板创建 Agent"""
        # 先获取一个模板
        templates = self.service.get_all_templates()
        if templates:
            template_id = templates[0]["id"]
            agent = self.service.create_agent(template_id, "测试 Agent")
            
            assert agent is not None
            assert agent["name"] == "测试 Agent"
            assert agent["template_id"] == template_id
            assert agent["status"] == "idle"
            assert agent["is_active"] is True
            assert "id" in agent
    
    def test_create_agent_template_not_found(self):
        """测试从不存在的模板创建 Agent"""
        with pytest.raises(ValueError) as exc_info:
            self.service.create_agent("nonexistent_template")
        
        assert "Template not found" in str(exc_info.value)
    
    def test_get_agent(self):
        """测试获取 Agent"""
        # 先创建一个 Agent
        templates = self.service.get_all_templates()
        if templates:
            agent = self.service.create_agent(templates[0]["id"])
            agent_id = agent["id"]
            
            # 再获取
            retrieved = self.service.get_agent(agent_id)
            
            assert retrieved is not None
            assert retrieved["id"] == agent_id
    
    def test_get_agent_not_found(self):
        """测试获取不存在的 Agent"""
        agent = self.service.get_agent("nonexistent_id")
        assert agent is None
    
    def test_list_agents(self):
        """测试列出所有 Agent"""
        # 先创建几个 Agent
        templates = self.service.get_all_templates()
        if len(templates) >= 2:
            self.service.create_agent(templates[0]["id"], "Agent 1")
            self.service.create_agent(templates[1]["id"], "Agent 2")
        
        agents = self.service.list_agents()
        
        assert isinstance(agents, list)
        assert len(agents) >= 2
    
    def test_update_agent(self):
        """测试更新 Agent"""
        # 先创建一个 Agent
        templates = self.service.get_all_templates()
        if templates:
            agent = self.service.create_agent(templates[0]["id"])
            agent_id = agent["id"]
            
            # 更新
            updated = self.service.update_agent(agent_id, {"name": "Updated Name"})
            
            assert updated is not None
            assert updated["name"] == "Updated Name"
    
    def test_update_agent_not_found(self):
        """测试更新不存在的 Agent"""
        result = self.service.update_agent("nonexistent_id", {"name": "New Name"})
        assert result is None
    
    def test_delete_agent(self):
        """测试删除 Agent"""
        # 先创建一个 Agent
        templates = self.service.get_all_templates()
        if templates:
            agent = self.service.create_agent(templates[0]["id"])
            agent_id = agent["id"]
            
            # 删除
            result = self.service.delete_agent(agent_id)
            
            assert result is True
            assert self.service.get_agent(agent_id) is None
    
    def test_delete_agent_not_found(self):
        """测试删除不存在的 Agent"""
        result = self.service.delete_agent("nonexistent_id")
        assert result is False
    
    def test_create_team(self):
        """测试创建团队"""
        # 先创建几个 Agent
        templates = self.service.get_all_templates()
        if len(templates) >= 2:
            agent1 = self.service.create_agent(templates[0]["id"])
            agent2 = self.service.create_agent(templates[1]["id"])
            
            team = self.service.create_team("测试团队", [agent1["id"], agent2["id"]])
            
            assert team is not None
            assert team["name"] == "测试团队"
            assert len(team["agent_ids"]) == 2
    
    def test_get_team(self):
        """测试获取团队"""
        # 先创建团队
        templates = self.service.get_all_templates()
        if len(templates) >= 2:
            agent1 = self.service.create_agent(templates[0]["id"])
            agent2 = self.service.create_agent(templates[1]["id"])
            team = self.service.create_team("测试团队", [agent1["id"], agent2["id"]])
            team_id = team["id"]
            
            # 获取
            retrieved = self.service.get_team(team_id)
            
            assert retrieved is not None
            assert retrieved["id"] == team_id
    
    def test_get_team_not_found(self):
        """测试获取不存在的团队"""
        team = self.service.get_team("nonexistent_id")
        assert team is None
    
    def test_list_teams(self):
        """测试列出所有团队"""
        teams = self.service.list_teams()
        
        assert isinstance(teams, list)


class TestAgentServiceWithSoul:
    """Agent 服务与 soul.md 集成测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.service = AgentService()
    
    def test_soul_to_template_conversion(self):
        """测试 soul 到模板的转换"""
        soul = SoulFile(
            name="xiaowang",
            role="backend",
            title="后端开发工程师",
            core_principles=["解决实际问题", "保持简洁"],
            execution_rules=["单步任务立即执行"],
            avatar_color="#3B82F6"
        )
        
        template = self.service._soul_to_template(soul)
        
        assert template is not None
        assert template.name == "xiaowang"
        # 类型统一为 CUSTOM——配置阶段不预设职位
        assert template.type == AgentType.CUSTOM, f"Expected CUSTOM but got {template.type}"
        assert template.avatar_color == "#3B82F6"
        assert template.is_preset is False
        assert "soul-based" in template.tags
    
    def test_infer_agent_type(self):
        """测试 Agent 类型推断——统一返回 CUSTOM（不预设职位）"""
        assert self.service._infer_agent_type("产品经理") == AgentType.CUSTOM
        assert self.service._infer_agent_type("backend_dev") == AgentType.CUSTOM
        assert self.service._infer_agent_type("前端小王") == AgentType.CUSTOM
        assert self.service._infer_agent_type("测试工程师") == AgentType.CUSTOM
        assert self.service._infer_agent_type("运维") == AgentType.CUSTOM
        assert self.service._infer_agent_type("架构师") == AgentType.CUSTOM
        assert self.service._infer_agent_type("未知角色") == AgentType.CUSTOM
    
    def test_create_agent_from_soul(self):
        """测试从 soul 文件创建 Agent"""
        # 这个测试需要实际的 soul 文件存在
        # 如果 soul 文件不存在，应该抛出 ValueError
        try:
            agent = self.service.create_agent_from_soul("xiaowang", "小王")
            
            assert agent is not None
            assert agent["name"] == "小王"
            assert agent["source"] == "soul"
            assert agent["soul_data"] is not None
            assert "core_principles" in agent["soul_data"]
        except ValueError as e:
            # 如果 soul 文件不存在，这是预期的行为
            assert "Soul file not found" in str(e)
    
    def test_create_agent_from_soul_not_found(self):
        """测试从不存在的 soul 文件创建 Agent"""
        with pytest.raises(ValueError) as exc_info:
            self.service.create_agent_from_soul("nonexistent_agent")
        
        assert "Soul file not found" in str(exc_info.value)
    
    def test_get_soul_based_agents(self):
        """测试获取基于 soul 的 Agent"""
        # 初始应该为空或包含之前创建的
        agents = self.service.get_soul_based_agents()
        
        assert isinstance(agents, list)
        
        # 所有返回的 Agent 都应该有 source == "soul"
        for agent in agents:
            assert agent.get("source") == "soul"
    
    def test_create_agent_context(self):
        """测试为 Agent 创建上下文"""
        from app.models.agent_context import AgentContext
        
        # 先创建一个普通 Agent（使用非 soul-based 模板）
        templates = self.service.get_all_templates()
        # 找一个非 soul-based 的预设模板
        preset_templates = [t for t in templates if t.get("is_preset")]
        if preset_templates:
            agent = self.service.create_agent(preset_templates[0]["id"])
            agent_id = agent["id"]
            
            # 创建上下文
            context = self.service.create_agent_context(agent_id, "test_session")
            
            assert context is not None
            assert isinstance(context, AgentContext)
            assert context.agent_id == agent_id, f"Expected agent_id {agent_id} but got {context.agent_id}"
            assert context.session_id == "test_session"
    
    def test_create_agent_context_with_soul(self):
        """测试为有 soul 数据的 Agent 创建上下文"""
        from app.models.agent_context import AgentContext
        
        # 创建一个模拟的 soul-based Agent
        agent_id = "test_soul_agent"
        self.service._agents[agent_id] = {
            "id": agent_id,
            "name": "Test Soul Agent",
            "type": "backend",
            "system_prompt": "Test prompt",
            "source": "soul",
            "soul_data": {
                "name": "test_agent",
                "core_principles": ["Be helpful"],
                "execution_rules": ["Think first"],
                "role_definitions": {}
            }
        }
        
        # 创建上下文
        context = self.service.create_agent_context(agent_id, "test_session")
        
        assert context is not None
        assert isinstance(context, AgentContext)
        assert context.soul_data is not None
        assert "Be helpful" in context.personality.get("core_principles", [])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
