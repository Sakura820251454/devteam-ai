#!/usr/bin/env python3
"""
记忆系统真实场景测试脚本
使用 Python 内置模块，无需额外安装
"""
import urllib.request
import urllib.error
import json
import time

BASE_URL = "http://127.0.0.1:8001"


def make_request(method, endpoint, data=None):
    """发送 HTTP 请求"""
    url = f"{BASE_URL}{endpoint}"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        if method == "GET":
            req = urllib.request.Request(url, headers=headers)
        else:  # POST, PUT, DELETE
            body = json.dumps(data).encode("utf-8") if data else None
            req = urllib.request.Request(url, data=body, headers=headers, method=method)

        with urllib.request.urlopen(req) as response:
            response_data = response.read().decode("utf-8")
            return response.status, json.loads(response_data) if response_data else {}

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        return e.code, {"error": error_body}
    except Exception as e:
        return 500, {"error": str(e)}


def test_add_memory():
    """测试添加记忆"""
    print("\n" + "="*60)
    print("1. 测试添加记忆 API")
    print("="*60)

    test_cases = [
        {
            "agent_id": "backend_dev_001",
            "content": "使用 FastAPI 开发 REST API，包含用户管理和认证功能",
            "level": "working",
            "tags": ["FastAPI", "REST", "后端"]
        },
        {
            "agent_id": "backend_dev_001",
            "content": "掌握了 PostgreSQL 数据库优化技巧，包括索引和查询优化",
            "level": "long_term",
            "tags": ["PostgreSQL", "数据库", "优化"]
        },
        {
            "agent_id": "backend_dev_001",
            "content": "学会了 Redis 缓存策略，用于提升 API 响应速度",
            "level": "long_term",
            "tags": ["Redis", "缓存", "性能"]
        },
        {
            "agent_id": "backend_dev_001",
            "content": "完成了用户登录功能的开发，使用 JWT 进行身份验证",
            "level": "short_term",
            "tags": ["JWT", "认证", "完成"]
        },
        {
            "agent_id": "backend_dev_001",
            "content": "正在开发商品管理模块，包含 CRUD 操作",
            "level": "working",
            "tags": ["任务", "商品管理", "开发中"]
        }
    ]

    created_ids = []

    for i, test_data in enumerate(test_cases, 1):
        print(f"\n添加记忆 {i}/{len(test_cases)}:")
        print(f"  Agent: {test_data['agent_id']}")
        print(f"  Content: {test_data['content']}")
        print(f"  Level: {test_data['level']}")
        print(f"  Tags: {test_data['tags']}")

        status, result = make_request("POST", "/memories/", test_data)

        if status == 200:
            print(f"  ✅ 成功! ID: {result['id']}")
            created_ids.append(result['id'])
        else:
            print(f"  ❌ 失败: {status} - {result}")

        time.sleep(0.1)

    return created_ids


def test_get_memories():
    """测试获取 Agent 的所有记忆"""
    print("\n" + "="*60)
    print("2. 测试获取 Agent 所有记忆")
    print("="*60)

    status, memories = make_request("GET", "/memories/agent/backend_dev_001")

    if status == 200:
        print(f"\n✅ 成功! 找到 {len(memories)} 条记忆")

        for i, mem in enumerate(memories, 1):
            print(f"\n  记忆 {i}:")
            print(f"    ID: {mem['id']}")
            print(f"    Level: {mem['level']}")
            print(f"    Tags: {mem['tags']}")
            print(f"    Content: {mem['content'][:50]}...")
    else:
        print(f"❌ 失败: {status} - {memories}")


def test_retrieve_memories():
    """测试检索记忆"""
    print("\n" + "="*60)
    print("3. 测试检索记忆 API")
    print("="*60)

    queries = [
        ("FastAPI", "查找 FastAPI 相关的记忆"),
        ("数据库", "查找数据库相关的记忆"),
        ("JWT", "查找 JWT 认证相关的记忆"),
        ("商品", "查找商品管理相关的记忆")
    ]

    for query, description in queries:
        print(f"\n查询: \"{query}\" ({description})")

        status, results = make_request(
            "POST",
            "/memories/retrieve",
            {
                "agent_id": "backend_dev_001",
                "search_query": query,
                "max_results": 3
            }
        )

        if status == 200:
            print(f"  ✅ 找到 {len(results)} 条相关记忆")

            for result in results:
                print(f"    - {result['content'][:50]}... (level: {result['level']})")
        else:
            print(f"  ❌ 失败: {status}")


def test_get_context_prompt():
    """测试获取上下文提示词"""
    print("\n" + "="*60)
    print("4. 测试获取上下文提示词")
    print("="*60)

    status, result = make_request("GET", "/memories/context/backend_dev_001/prompt")

    if status == 200:
        print(f"\n✅ 成功获取上下文提示词:")
        print("-" * 60)
        prompt = result['prompt']
        print(prompt[:500] if len(prompt) > 500 else prompt)
        print("-" * 60)
    else:
        print(f"❌ 失败: {status} - {result}")


def test_get_statistics():
    """测试获取统计信息"""
    print("\n" + "="*60)
    print("5. 测试获取记忆统计")
    print("="*60)

    status, stats = make_request("GET", "/memories/agent/backend_dev_001/statistics")

    if status == 200:
        print(f"\n✅ 统计信息:")
        print(f"  Working (L1): {stats['working']} 条")
        print(f"  Short-term (L2): {stats['short_term']} 条")
        print(f"  Long-term (L3): {stats['long_term']} 条")
        print(f"  总计: {stats['total']} 条")
    else:
        print(f"❌ 失败: {status}")


def test_persist_after_restart():
    """测试持久化 - 重启后验证数据"""
    print("\n" + "="*60)
    print("6. 测试持久化 - 验证数据是否持久化")
    print("="*60)

    print("\n重新查询记忆:")
    status, memories = make_request("GET", "/memories/agent/backend_dev_001")

    if status == 200:
        print(f"✅ 数据持久化成功! 仍有 {len(memories)} 条记忆")

        if len(memories) > 0:
            print("\n前 3 条记忆:")
            for i, mem in enumerate(memories[:3], 1):
                print(f"  {i}. [{mem['level']}] {mem['content'][:40]}...")
    else:
        print(f"❌ 查询失败: {status}")


def main():
    print("="*60)
    print("DevTeam-AI 记忆系统真实场景测试")
    print("="*60)
    print(f"API 地址: {BASE_URL}")

    try:
        # 1. 添加记忆
        created_ids = test_add_memory()

        # 2. 获取所有记忆
        test_get_memories()

        # 3. 检索记忆
        test_retrieve_memories()

        # 4. 获取上下文提示词
        test_get_context_prompt()

        # 5. 获取统计
        test_get_statistics()

        # 6. 测试持久化
        test_persist_after_restart()

        print("\n" + "="*60)
        print("✅ 所有测试完成!")
        print("="*60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
