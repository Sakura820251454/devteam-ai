#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import traceback
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

def test_import(module_path, import_statement, description):
    """测试单个导入"""
    try:
        exec(import_statement)
        print(f"✓ {description}")
        return True
    except Exception as e:
        print(f"✗ {description}")
        print(f"  错误: {e}")
        traceback.print_exc()
        return False

def main():
    results = []
    print("=" * 60)
    print("开始验证重组后的项目...")
    print(f"PYTHONPATH 根目录: {sys.path[0]}")
    print("=" * 60)

    print("\n【1】验证 Python 服务导入")
    print("-" * 40)

    results.append(test_import(
        "agent_service",
        "from app.services.agent.agent_service import AgentService",
        "AgentService"
    ))
    results.append(test_import(
        "agent_executor",
        "from app.services.agent.agent_executor import AgentExecutor",
        "AgentExecutor"
    ))
    results.append(test_import(
        "message_bus",
        "from app.services.collaboration.message_bus import MessageBus",
        "MessageBus"
    ))
    results.append(test_import(
        "task_board",
        "from app.services.collaboration.task_board import TaskBoard",
        "TaskBoard"
    ))
    results.append(test_import(
        "persistent_memory_manager",
        "from app.services.memory.persistent_memory_manager import PersistentMemoryManager",
        "PersistentMemoryManager"
    ))
    results.append(test_import(
        "llm_service",
        "from app.services.llm.llm_service import LLMService",
        "LLMService"
    ))

    print("\n【2】验证 __init__.py 导入")
    print("-" * 40)
    results.append(test_import(
        "services_init",
        "from app.services import AgentService, MessageBus, TaskBoard",
        "从 app.services 导入核心服务"
    ))

    print("\n【3】验证 API 导入")
    print("-" * 40)
    api_modules = [
        ("app.api.agents", "agents API"),
        ("app.api.messages", "messages API"),
        ("app.api.tasks", "tasks API"),
        ("app.api.projects", "projects API"),
        ("app.api.pipelines", "pipelines API"),
        ("app.api.speaking", "speaking API"),
        ("app.api.memories", "memories API"),
        ("app.api.llm", "llm API"),
        ("app.api.equipment", "equipment API"),
        ("app.api.knowledge", "knowledge API"),
        ("app.api.skills", "skills API"),
    ]

    for module, desc in api_modules:
        results.append(test_import(
            module,
            f"import {module}",
            desc
        ))

    print("\n【4】验证应用主模块导入")
    print("-" * 40)
    results.append(test_import(
        "app_app",
        "from app import app",
        "from app import app"
    ))
    results.append(test_import(
        "app_main",
        "import app.main",
        "import app.main"
    ))

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"验证结果: {passed}/{total} 通过")

    if passed == total:
        print("✓ 所有验证测试通过！")
        return 0
    else:
        print(f"✗ 有 {total - passed} 个测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
