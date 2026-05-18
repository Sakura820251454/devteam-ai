#!/usr/bin/env python3
"""
测试 soul.md 解析器
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

from app.services.shared.soul_parser import (
    SoulParser,
    load_agent_from_soul,
    load_all_agents,
    soul_to_system_prompt
)


def test_parse_xiaowang():
    """测试解析小王的 soul.md"""
    print("=" * 60)
    print("测试解析小王的 soul.md")
    print("=" * 60)
    
    soul_file = project_root / "backend" / "agents" / "agent_xiaowang" / "soul.md"
    soul = load_agent_from_soul(str(soul_file))
    
    print(f"\n✅ 成功解析: {soul.name}")
    print(f"\n📌 Core Principles ({len(soul.core_principles)} 条):")
    for p in soul.core_principles:
        print(f"   - {p}")
    
    print(f"\n📋 Execution Rules ({len(soul.execution_rules)} 条):")
    for r in soul.execution_rules:
        print(f"   - {r}")
    
    print("\n📝 生成的系统提示词:")
    print("-" * 60)
    prompt = soul_to_system_prompt(soul)
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    print("-" * 60)
    
    return True


def test_load_all():
    """测试加载所有 agents"""
    print("\n" + "=" * 60)
    print("测试加载所有 Agents")
    print("=" * 60)
    
    agents_dir = project_root / "backend" / "agents"
    agents = load_all_agents(str(agents_dir))
    
    print(f"\n✅ 加载了 {len(agents)} 个 Agent:")
    for name, soul in agents.items():
        principles_count = len(soul.core_principles)
        rules_count = len(soul.execution_rules)
        print(f"  - {name}: {principles_count} 原则 + {rules_count} 规则")
    
    return len(agents) > 0


def main():
    results = []
    results.append(("小王解析测试", test_parse_xiaowang()))
    results.append(("批量加载测试", test_load_all()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
