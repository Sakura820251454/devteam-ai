"""
Mock LLM 数据和响应模板
用于 Phase 2/3 测试

使用方法：
    from mock_llm_data import MockLLM, get_mock_response

    # 获取对话响应
    response = get_mock_response("你好", agent="pm")

    # 获取任务分析响应
    response = get_mock_response("分析需求", agent="architect", type="analysis")

    # 获取代码生成响应
    response = get_mock_response("生成代码", agent="backend", type="code")
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class MockAgent(Enum):
    PM = "product_manager"
    ARCHITECT = "architect"
    BACKEND = "backend_developer"
    FRONTEND = "frontend_developer"
    TESTER = "tester"


class ResponseType(Enum):
    DISCUSSION = "discussion"
    ANALYSIS = "analysis"
    CODE = "code"
    REVIEW = "review"
    SUMMARY = "summary"


@dataclass
class MockResponse:
    content: str
    agent: str
    tokens_used: int
    response_type: str


class MockLLMData:
    """Mock LLM 响应数据"""

    # Agent 角色定义
    AGENT_PROFILES = {
        "pm": {
            "name": "产品经理小李",
            "role": "产品经理",
            "personality": "严谨、专业、注重用户体验",
            "expertise": ["需求分析", "产品设计", "用户研究", "项目管理"]
        },
        "architect": {
            "name": "架构师老王",
            "role": "架构师",
            "personality": "技术深厚、注重系统设计、喜欢前瞻性思考",
            "expertise": ["系统架构", "技术选型", "性能优化", "安全性设计"]
        },
        "backend": {
            "name": "后端开发小张",
            "role": "后端开发",
            "personality": "务实、高效、注重代码质量",
            "expertise": ["Python", "FastAPI", "数据库设计", "API开发"]
        },
        "frontend": {
            "name": "前端开发小陈",
            "role": "前端开发",
            "personality": "追求细节、注重用户体验、关注最新技术",
            "expertise": ["React", "TypeScript", "TailwindCSS", "UI设计"]
        },
        "tester": {
            "name": "测试工程师小刘",
            "role": "测试工程师",
            "personality": "细心、严谨、善于发现问题",
            "expertise": ["测试用例设计", "自动化测试", "性能测试", "安全测试"]
        }
    }

    # 需求分析讨论数据
    REQUIREMENT_DISCUSSION = {
        "initial_analysis": {
            "pm": "大家好，今天我们来讨论一个新项目：开发一个用户管理系统。我来介绍一下需求背景和核心功能。",
            "architect": "好的，请先介绍一下系统的规模和预期用户量，这样我可以更好地设计系统架构。",
            "pm": "预计初期会有1000个并发用户，后期可能扩展到10000+。主要功能包括用户注册登录、权限管理、个人信息管理。",
            "architect": "明白了。按照这个规模，我建议采用微服务架构，但考虑到MVP阶段，我们可以先用单体架构，后期再拆分。",
            "backend": "同意。我建议使用 FastAPI + PostgreSQL，技术成熟且性能优秀。",
        },
        "detailed_discussion": {
            "architect": "关于技术选型，我建议后端用 FastAPI，前端用 React + TypeScript，数据库用 PostgreSQL。",
            "frontend": "好的，我这边没问题。React 生态成熟，组件库丰富，开发效率高。",
            "pm": "那数据库表结构怎么设计？我需要确认一下开发周期。",
            "backend": "我计划设计3张核心表：users、roles、permissions。预计开发周期2周左右。",
            "tester": "测试这边需要预留1周时间，包括单元测试和集成测试。",
        }
    }

    # 任务拆解数据
    TASK_BREAKDOWN = {
        "phases": [
            {
                "phase": "数据库设计",
                "tasks": [
                    {"title": "设计用户表结构", "description": "创建 users 表，包含用户名、邮箱、密码等字段", "priority": "high"},
                    {"title": "设计角色表结构", "description": "创建 roles 表，定义角色名称和描述", "priority": "high"},
                    {"title": "设计权限表结构", "description": "创建 permissions 表，定义权限名称和资源", "priority": "medium"},
                    {"title": "设计用户角色关联表", "description": "创建 user_roles 表，实现用户和角色的多对多关系", "priority": "high"},
                ]
            },
            {
                "phase": "API开发",
                "tasks": [
                    {"title": "实现用户注册API", "description": "POST /api/users/register", "priority": "high"},
                    {"title": "实现用户登录API", "description": "POST /api/users/login", "priority": "high"},
                    {"title": "实现用户信息查询API", "description": "GET /api/users/{id}", "priority": "medium"},
                    {"title": "实现权限验证API", "description": "POST /api/auth/verify", "priority": "high"},
                ]
            },
            {
                "phase": "前端开发",
                "tasks": [
                    {"title": "登录注册页面", "description": "实现用户登录和注册界面", "priority": "high"},
                    {"title": "用户列表页面", "description": "展示和管理用户列表", "priority": "medium"},
                    {"title": "权限配置页面", "description": "管理用户角色和权限", "priority": "medium"},
                ]
            },
            {
                "phase": "测试",
                "tasks": [
                    {"title": "编写单元测试", "description": "对核心业务逻辑编写单元测试", "priority": "high"},
                    {"title": "编写集成测试", "description": "测试 API 端到端功能", "priority": "high"},
                    {"title": "性能测试", "description": "测试系统在高并发下的表现", "priority": "low"},
                ]
            }
        ]
    }

    # 代码生成模板
    CODE_TEMPLATES = {
        "user_model": '''class User(BaseModel):
    """用户模型"""
    id: Optional[int] = None
    username: str
    email: EmailStr
    password_hash: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True''',
        "register_endpoint": '''@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """用户注册接口"""
    # 检查用户是否已存在
    existing = await db.query(User, email=user_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    # 创建用户
    user = await user_service.create_user(user_data)
    return user''',
        "login_endpoint": '''@router.post("/login")
async def login(credentials: LoginRequest):
    """用户登录接口"""
    user = await auth_service.authenticate(
        credentials.email,
        credentials.password
    )
    if not user:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    # 生成 JWT token
    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}'''
    }

    # 代码审查反馈
    CODE_REVIEWS = {
        "security_issue": {
            "severity": "high",
            "message": "发现安全问题：密码明文传输。建议使用 HTTPS 并在客户端进行密码加密。",
            "suggestion": "使用 bcrypt 进行密码哈希存储，确保即使数据库泄露也不会暴露用户密码。"
        },
        "performance_issue": {
            "severity": "medium",
            "message": "性能问题：数据库查询未使用索引，可能导致查询缓慢。",
            "suggestion": "在 email 和 username 字段上添加索引以提高查询性能。"
        },
        "best_practice": {
            "severity": "low",
            "message": "代码规范：建议使用 Pydantic 的 Field 来定义字段验证规则。",
            "suggestion": "如 Field(..., min_length=3, max_length=50) 来限制字段长度。"
        }
    }

    # 讨论摘要模板
    SUMMARY_TEMPLATE = '''# 讨论摘要

## 会议主题
{topic}

## 参与人员
{participants}

## 主要讨论内容
{content}

## 关键决策
{decisions}

## 待解决问题
{open_issues}

## 下一步行动
{next_steps}

## 会议时间
{meeting_time}
'''

    @classmethod
    def get_discussion_flow(cls, topic: str) -> List[Dict]:
        """获取讨论流程数据"""
        flows = {
            "requirement": [
                {"agent": "pm", "content": "大家好，今天我们讨论一个新项目。", "delay": 1.0},
                {"agent": "architect", "content": "请介绍一下需求背景。", "delay": 2.0},
                {"agent": "pm", "content": "这是一个企业内部用户管理系统...", "delay": 3.0},
                {"agent": "backend", "content": "技术选型方面我有一些建议...", "delay": 2.0},
                {"agent": "architect", "content": "同意，我们可以采用微服务架构...", "delay": 3.0},
            ],
            "task_breakdown": [
                {"agent": "pm", "content": "根据需求，我来拆解一下开发任务。", "delay": 1.0},
                {"agent": "backend", "content": "数据库设计和API开发我来负责。", "delay": 2.0},
                {"agent": "frontend", "content": "前端界面我这边可以并行开发。", "delay": 2.0},
                {"agent": "tester", "content": "测试用例我已经开始准备了。", "delay": 1.5},
            ]
        }
        return flows.get(topic, [])

    @classmethod
    def get_agent_response(cls, agent: str, context: str) -> str:
        """根据上下文获取 Agent 的回复"""
        profile = cls.AGENT_PROFILES.get(agent, {})
        responses = {
            "pm": f"我是{profile.get('name', '产品经理')}，{profile.get('personality', '')}。关于{context}，我会从用户需求的角度来考虑。",
            "architect": f"我是{profile.get('name', '架构师')}，{profile.get('personality', '')}。关于{context}，我会从系统设计的角度来分析。",
            "backend": f"我是{profile.get('name', '后端开发')}，{profile.get('personality', '')}。关于{context}，我会从技术实现的角度来处理。",
            "frontend": f"我是{profile.get('name', '前端开发')}，{profile.get('personality', '')}。关于{context}，我会从用户体验的角度来实现。",
            "tester": f"我是{profile.get('name', '测试工程师')}，{profile.get('personality', '')}。关于{context}，我会从质量保障的角度来验证。",
        }
        return responses.get(agent, f"这是 {agent} 的回复：关于 {context}")

    @classmethod
    def generate_token_estimate(cls, text: str) -> int:
        """估算 token 数量（简化版本）"""
        return len(text) // 4


def get_mock_response(
    prompt: str,
    agent: str = "pm",
    response_type: str = "discussion"
) -> MockResponse:
    """
    获取 Mock LLM 响应

    Args:
        prompt: 输入提示词
        agent: Agent 类型 (pm/architect/backend/frontend/tester)
        response_type: 响应类型 (discussion/analysis/code/review/summary)

    Returns:
        MockResponse: Mock 响应对象
    """
    data = MockLLMData()

    # 根据响应类型生成内容
    if response_type == "discussion":
        content = data.get_agent_response(agent, prompt)
    elif response_type == "analysis":
        content = f"## 分析报告\n\n基于'{prompt}'的分析：\n\n### 发现\n1. 核心需求明确\n2. 技术可行性较高\n3. 建议采用敏捷开发\n\n### 建议\n- 优先级：高\n- 预计工时：2周"
    elif response_type == "code":
        template_key = prompt.lower().replace(" ", "_")
        content = data.CODE_TEMPLATES.get(template_key, f"# 代码生成\n# prompt: {prompt}\npass")
    elif response_type == "review":
        content = "## 代码审查\n\n### 整体评价\n代码质量良好，建议关注安全性。"
    else:
        content = f"响应内容：{prompt}"

    return MockResponse(
        content=content,
        agent=agent,
        tokens_used=data.generate_token_estimate(content),
        response_type=response_type
    )


# 预定义的讨论场景数据
SCENARIOS = {
    "user_management": {
        "name": "用户管理系统开发",
        "requirements": """
需求描述：
1. 用户注册和登录
2. 角色权限管理
3. 用户信息管理
4. 密码安全

预期规模：
- 初期1000并发用户
- 后期扩展到10000+
""",
        "discussion_flow": "requirement",
        "expected_tasks": 12
    },

    "api_design": {
        "name": "RESTful API 设计",
        "requirements": """
API 需求：
1. 用户 CRUD 操作
2. 认证授权
3. 分页查询
4. 数据校验
""",
        "discussion_flow": "task_breakdown",
        "expected_tasks": 8
    },

    "code_review": {
        "name": "代码审查",
        "requirements": """
审查代码：
1. 用户认证模块
2. 权限校验逻辑
3. 数据加密实现
""",
        "discussion_flow": "requirement",
        "expected_issues": 3
    }
}


if __name__ == "__main__":
    # 测试代码
    print("=== Mock LLM 测试 ===\n")

    # 测试 Agent 回复
    for agent in ["pm", "architect", "backend"]:
        response = get_mock_response("这个功能怎么实现", agent=agent)
        print(f"[{agent}] {response.content[:50]}...")
        print(f"    tokens: {response.tokens_used}\n")

    # 测试讨论流程
    print("\n=== 讨论流程 ===")
    flow = MockLLMData.get_discussion_flow("requirement")
    for step in flow:
        print(f"[{step['agent']}] {step['content'][:30]}...")
