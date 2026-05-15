#!/usr/bin/env python3
"""
文档同步工具
功能：
1. 检测代码变更
2. 识别受影响的模块
3. 提醒或自动更新相关文档
4. 支持 git hook 集成

用法：
    python doc_sync.py --check          # 检查变更
    python doc_sync.py --auto          # 自动同步
    python doc_sync.py --list          # 列出所有映射
    python doc_sync.py --init-hook     # 安装 git hooks
"""

import os
import sys
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set


class DocSyncTool:
    def __init__(self, config_path: str = None):
        self.project_root = Path(__file__).parent.parent
        self.config_path = config_path or str(self.project_root / "scripts" / "doc_sync_config.json")
        self.config = self._load_config()
        self.mappings = self.config.get("mappings", {})

    def _load_config(self) -> dict:
        if not os.path.exists(self.config_path):
            print(f"⚠️ 配置文件不存在: {self.config_path}")
            return {"mappings": {}, "sync_rules": {}}

        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_git_diff(self, staged_only: bool = False) -> List[str]:
        """获取 git 变更的文件列表"""
        try:
            cmd = ["git", "diff", "--name-only", "--cached"] if staged_only else ["git", "diff", "--name-only", "HEAD"]
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        except Exception as e:
            print(f"⚠️ 获取 git 差异失败: {e}")
            return []

    def _get_modified_files(self) -> List[str]:
        """获取所有变更的文件"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            files = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    # 去掉状态前缀 (如 "M " 或 "A ")
                    file_path = line[3:].strip() if len(line) > 3 else line[2:].strip()
                    files.append(file_path)
            return files
        except Exception as e:
            print(f"⚠️ 获取变更文件失败: {e}")
            return []

    def _normalize_path(self, path: str) -> str:
        """标准化路径格式"""
        return path.replace("\\", "/")

    def find_affected_modules(self, changed_files: List[str]) -> List[Dict]:
        """找出受影响的模块"""
        affected = []
        changed_set = {self._normalize_path(f) for f in changed_files}

        for code_file, mapping in self.mappings.items():
            normalized_code = self._normalize_path(code_file)

            # 检查是否有直接匹配
            if normalized_code in changed_set:
                affected.append({
                    "code_file": code_file,
                    "docs": mapping.get("docs", []),
                    "description": mapping.get("description", ""),
                    "reason": "直接修改"
                })
                continue

            # 检查文件名是否包含在变更路径中
            code_filename = Path(code_file).name
            for changed_file in changed_set:
                if code_filename in changed_file:
                    affected.append({
                        "code_file": code_file,
                        "docs": mapping.get("docs", []),
                        "description": mapping.get("description", ""),
                        "reason": f"文件名匹配 ({Path(changed_file).name})"
                    })
                    break

        return affected

    def check_docs_need_update(self, affected_modules: List[Dict]) -> List[Dict]:
        """检查文档是否需要更新"""
        needs_update = []

        for module in affected_modules:
            code_file = module["code_file"]
            docs = module["docs"]

            # 检查代码文件是否存在且有变更
            code_path = self.project_root / code_file
            if not code_path.exists():
                continue

            # 获取代码的最后修改时间
            code_mtime = os.path.getmtime(code_path)

            # 检查关联的文档
            for doc_path in docs:
                full_doc_path = self.project_root / doc_path
                if not full_doc_path.exists():
                    needs_update.append({
                        **module,
                        "doc_file": doc_path,
                        "doc_exists": False,
                        "reason": "文档不存在，需要创建"
                    })
                    continue

                # 比较修改时间
                doc_mtime = os.path.getmtime(full_doc_path)
                if code_mtime > doc_mtime:
                    needs_update.append({
                        **module,
                        "doc_file": doc_path,
                        "doc_exists": True,
                        "code_mtime": datetime.fromtimestamp(code_mtime),
                        "doc_mtime": datetime.fromtimestamp(doc_mtime),
                        "reason": f"代码较新 (代码: {datetime.fromtimestamp(code_mtime):%Y-%m-%d %H:%M}, 文档: {datetime.fromtimestamp(doc_mtime):%Y-%m-%d %H:%M})"
                    })

        return needs_update

    def generate_sync_report(self, needs_update: List[Dict]) -> str:
        """生成同步报告"""
        if not needs_update:
            return "✅ 所有文档已是最新状态"

        report = ["=" * 60]
        report.append("📋 文档同步报告")
        report.append("=" * 60)
        report.append(f"\n发现 {len(needs_update)} 个文档需要同步:\n")

        for i, item in enumerate(needs_update, 1):
            report.append(f"\n{i}. {item['description']}")
            report.append(f"   代码文件: {item['code_file']}")
            report.append(f"   文档文件: {item['doc_file']}")
            report.append(f"   原因: {item['reason']}")

            if not item.get('doc_exists', True):
                report.append("   ⚠️ 文档不存在，需要创建新文档")

        report.append("\n" + "=" * 60)
        report.append("下一步操作:")
        report.append("  1. 运行 'python doc_sync.py --auto' 自动同步")
        report.append("  2. 手动更新相关文档")
        report.append("  3. 使用 'python doc_sync.py --review' 查看详细变更")
        report.append("=" * 60)

        return "\n".join(report)

    def list_mappings(self):
        """列出所有映射关系"""
        print("\n📚 代码文件 ↔ 文档映射表")
        print("=" * 60)

        for code_file, mapping in self.mappings.items():
            docs = mapping.get("docs", [])
            description = mapping.get("description", "")
            print(f"\n📁 {description}")
            print(f"   代码: {code_file}")
            for doc in docs:
                print(f"   文档: {doc}")

        print("\n" + "=" * 60)

    def run_sync(self, interactive: bool = True) -> bool:
        """执行同步检查"""
        print("\n🔍 正在检查代码与文档同步状态...\n")

        # 获取变更的文件
        changed_files = self._get_modified_files()
        if not changed_files:
            print("📝 未检测到代码变更")
            changed_files = self._get_git_diff()

        if not changed_files:
            print("✅ 未检测到代码变更，文档状态正常")
            return True

        print(f"📂 检测到 {len(changed_files)} 个文件变更:")
        for f in changed_files[:10]:
            print(f"   - {f}")
        if len(changed_files) > 10:
            print(f"   ... 还有 {len(changed_files) - 10} 个文件")

        # 找出受影响的模块
        affected = self.find_affected_modules(changed_files)
        if not affected:
            print("\n✅ 没有受影响的文档")
            return True

        print(f"\n⚠️  发现 {len(affected)} 个模块可能需要更新文档")

        # 检查哪些文档需要更新
        needs_update = self.check_docs_need_update(affected)

        # 生成报告
        report = self.generate_sync_report(needs_update)
        print(f"\n{report}")

        if interactive and needs_update:
            response = input("\n❓ 是否需要我帮你更新这些文档? (y/n): ")
            if response.lower() == 'y':
                return self.auto_update_docs(needs_update)

        return False

    def auto_update_docs(self, needs_update: List[Dict] = None) -> bool:
        """自动更新文档 - 这里调用 AI 来帮助更新"""
        if needs_update is None:
            changed_files = self._get_modified_files()
            affected = self.find_affected_modules(changed_files)
            needs_update = self.check_docs_need_update(affected)

        if not needs_update:
            print("✅ 所有文档已是最新状态")
            return True

        print(f"\n🔄 准备更新 {len(needs_update)} 个文档...")

        # 这里生成更新任务列表，供 AI 后续处理
        update_tasks = []
        for item in needs_update:
            update_tasks.append({
                "action": "update" if item.get("doc_exists") else "create",
                "code_file": item["code_file"],
                "doc_file": item["doc_file"],
                "description": item["description"]
            })

        # 保存更新任务
        tasks_file = self.project_root / "scripts" / "pending_updates.json"
        with open(tasks_file, "w", encoding="utf-8") as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "tasks": update_tasks
            }, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 更新任务已保存到: {tasks_file}")
        print("\n📋 待处理的任务列表:")
        for i, task in enumerate(update_tasks, 1):
            action = "创建" if task["action"] == "create" else "更新"
            print(f"   {i}. [{action}] {task['doc_file']}")
            print(f"      <- {task['code_file']}")

        print("\n💡 提示: 请告诉 AI 助手 '帮我同步文档' 来执行实际更新")
        return True

    def init_git_hooks(self):
        """初始化 git hooks"""
        hooks_dir = self.project_root / ".git" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)

        # 创建 pre-commit hook
        hook_content = '''#!/bin/bash
# 文档同步检查 - pre-commit hook
# 此 hook 会在提交前检查是否有文档需要同步

echo "🔍 检查文档同步状态..."

cd "$(dirname "$0")/../scripts"
python doc_sync.py --check

if [ $? -ne 0 ]; then
    echo "⚠️  发现文档可能需要更新"
    read -p "是否继续提交? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 提交已取消"
        exit 1
    fi
fi

echo "✅ 文档检查完成"
exit 0
'''

        hook_path = hooks_dir / "pre-commit"
        with open(hook_path, "w", encoding="utf-8") as f:
            f.write(hook_content)

        # 设置执行权限
        os.chmod(hook_path, 0o755)

        print(f"✅ Git hook 已安装: {hook_path}")
        print("   每次提交前会自动检查文档同步状态")

    def generate_module_doc_from_code(self, code_file: str) -> Optional[str]:
        """根据代码文件生成模块文档（基础版本）"""
        code_path = self.project_root / code_file
        if not code_path.exists():
            return None

        with open(code_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 提取类定义
        classes = re.findall(r'class (\w+)(?:\([^)]*\))?:', content)

        # 提取函数定义
        functions = re.findall(r'(?:async )?def (\w+)\(', content)

        # 提取 docstring
        docstrings = {}
        for match in re.finditer(r'"""(.*?)"""', content, re.DOTALL):
            docstrings[len(docstrings)] = match.group(1).strip()[:200]

        return f"""# {Path(code_file).stem} 模块文档

**自动生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 概述

本模块对应代码文件: `{code_file}`

## 检测到的组件

### 类定义
{chr(10).join(f'- `{c}`' for c in classes) if classes else '- 无'}

### 函数定义
{chr(10).join(f'- `{f}()`' for f in functions) if functions else '- 无'}

---
*此文档为自动生成，请根据实际功能补充详细内容*
"""


def main():
    import argparse

    parser = argparse.ArgumentParser(description="文档同步工具")
    parser.add_argument("--check", action="store_true", help="检查文档同步状态")
    parser.add_argument("--auto", action="store_true", help="自动同步文档")
    parser.add_argument("--list", action="store_true", help="列出所有映射")
    parser.add_argument("--init-hook", action="store_true", help="安装 git hooks")
    parser.add_argument("--config", type=str, help="指定配置文件路径")

    args = parser.parse_args()

    tool = DocSyncTool(config_path=args.config)

    if args.list:
        tool.list_mappings()
    elif args.init_hook:
        tool.init_git_hooks()
    elif args.auto:
        success = tool.run_sync(interactive=False)
        sys.exit(0 if success else 1)
    elif args.check:
        success = tool.run_sync(interactive=False)
        sys.exit(0 if success else 1)
    else:
        # 默认显示帮助
        tool.list_mappings()
        print("\n用法示例:")
        print("  python doc_sync.py --check      # 检查同步状态")
        print("  python doc_sync.py --auto      # 生成同步任务")
        print("  python doc_sync.py --list      # 列出所有映射")
        print("  python doc_sync.py --init-hook # 安装 git hooks")


if __name__ == "__main__":
    main()
