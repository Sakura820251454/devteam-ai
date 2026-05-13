# Mock LLM 测试数据说明

## 概述

本目录包含用于 Phase 2 和 Phase 3 功能测试的 Mock LLM 数据和测试用例。

## 文件结构

```
tests/
├── mock/
│   └── mock_llm_data.py      # Mock LLM 数据和响应模板
├── test_phase2_integration.py  # Phase 2 集成测试
├── test_phase3_integration.py  # Phase 3 集成测试
└── test_e2e_user_management.py # 端到端测试
```

## Mock 数据内容

### Agent 角色定义

| Agent | 名称 | 角色 | 特点 |
|-------|------|------|------|
| pm | 产品经理小李 | 产品经理 | 严谨、专业、注重用户体验 |
| architect | 架构师老王 | 架构师 | 技术深厚、注重系统设计 |
| backend | 后端开发小张 | 后端开发 | 务实、高效、注重代码质量 |
| frontend | 前端开发小陈 | 前端开发 | 追求细节、注重用户体验 |
| tester | 测试工程师小刘 | 测试工程师 | 细心、严谨、善于发现问题 |

### 预定义场景

1. **user_management**: 用户管理系统开发
2. **api_design**: RESTful API 设计
3. **code_review**: 代码审查

### 讨论流程

- `requirement`: 需求分析讨论流程
- `task_breakdown`: 任务拆解讨论流程

### 代码模板

- `user_model`: 用户模型代码
- `register_endpoint`: 用户注册 API
- `login_endpoint`: 用户登录 API

## 运行测试

### 运行所有测试

```bash
cd backend
pytest tests/test_phase2_integration.py -v
pytest tests/test_phase3_integration.py -v
pytest tests/test_e2e_user_management.py -v
```

### 运行特定测试

```bash
# Phase 2 测试
pytest tests/test_phase2_integration.py::TestMessageBus -v
pytest tests/test_phase2_integration.py::TestSpeakingController -v
pytest tests/test_phase2_integration.py::TestTaskBoard -v

# Phase 3 测试
pytest tests/test_phase3_integration.py::TestPipelineOrchestrator -v
pytest tests/test_phase3_integration.py::TestHumanIntervention -v

# 端到端测试
pytest tests/test_e2e_user_management.py::TestUserManagementE2E::test_complete_project_lifecycle -v -s
```

### 查看详细输出

```bash
pytest tests/test_e2e_user_management.py -v -s
```

## 测试场景

### 场景 1: 用户管理系统完整流程

1. 需求讨论（多 Agent 发言）
2. 任务拆解（生成 12 个任务）
3. 项目创建
4. Pipeline 启动
5. 人类干预（广播、私信、暂停、恢复）
6. 任务执行
7. 代码审查
8. 结果验证

### 场景 2: 任务状态流转

```
BACKLOG → TODO → IN_PROGRESS → REVIEW → DONE
```

### 场景 3: 多 Agent 协作

- 轮询发言模式
- 消息广播
- 频率限制

## 使用 Mock 数据

### 获取 Agent 响应

```python
from tests.mock.mock_llm_data import get_mock_response

response = get_mock_response(
    prompt="这个功能怎么实现",
    agent="backend",
    response_type="discussion"
)

print(response.content)
print(f"Tokens: {response.tokens_used}")
```

### 获取讨论流程

```python
from tests.mock.mock_llm_data import MockLLMData

flow = MockLLMData.get_discussion_flow("requirement")
for step in flow:
    print(f"[{step['agent']}] {step['content']}")
```

### 获取任务拆解

```python
from tests.mock.mock_llm_data import MockLLMData

breakdown = MockLLMData.TASK_BREAKDOWN
for phase in breakdown["phases"]:
    print(f"\n{phase['phase']}:")
    for task in phase["tasks"]:
        print(f"  - {task['title']} ({task['priority']})")
```

## 添加新的 Mock 数据

### 添加新的 Agent

在 `mock_llm_data.py` 的 `AGENT_PROFILES` 中添加：

```python
"new_agent": {
    "name": "新 Agent 名称",
    "role": "角色",
    "personality": "性格特点",
    "expertise": ["专业领域1", "专业领域2"]
}
```

### 添加新的讨论流程

```python
"new_flow": [
    {"agent": "pm", "content": "讨论内容1", "delay": 1.0},
    {"agent": "backend", "content": "讨论内容2", "delay": 2.0},
]
```

### 添加新的代码模板

```python
CODE_TEMPLATES = {
    "new_template": '''def new_function():
    # 你的代码
    pass'''
}
```

## 测试报告

运行测试后会生成以下信息：

- 测试通过/失败数量
- 各阶段执行时间
- 任务状态分布
- Pipeline 状态
- 干预记录数量

示例输出：

```
====================== test session starts ======================
collected 15 items

tests/test_phase2_integration.py::TestMessageBus::test_broadcast_message PASSED
tests/test_phase2_integration.py::TestTaskBoard::test_task_status_transition PASSED
tests/test_e2e_user_management.py::TestUserManagementE2E::test_complete_project_lifecycle PASSED

====================== 15 passed in 2.5s ======================
```
