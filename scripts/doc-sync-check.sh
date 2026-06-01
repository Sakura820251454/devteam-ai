#!/bin/bash
# doc-sync-check.sh
# 轻量级文档同步检查，供 Hook 调用
# 输入：变更的文件路径（通过参数或 stdin）
# 输出：需要检查的文档路径列表（如果有）

CHANGED_FILES="$@"
NEEDS_CHECK=""

# 代码路径 → 文档路径映射
check_mapping() {
    local file="$1"
    case "$file" in
        backend/app/api/*)
            NEEDS_CHECK="$NEEDS_CHECK\n- docs/05-api/ (API 文档)" ;;
        backend/app/models/*)
            NEEDS_CHECK="$NEEDS_CHECK\n- docs/04-modules/backend/models/ (数据模型)" ;;
        backend/app/services/agent/*)
            NEEDS_CHECK="$NEEDS_CHECK\n- docs/04-modules/backend/agent-*.md (Agent 服务)" ;;
        backend/app/services/collaboration/*)
            NEEDS_CHECK="$NEEDS_CHECK\n- docs/04-modules/backend/pipeline-*.md\n- docs/02-design/collaboration.md (协作设计)" ;;
        backend/app/services/memory/*)
            NEEDS_CHECK="$NEEDS_CHECK\n- docs/04-modules/backend/memory-*.md\n- docs/02-design/memory-system.md (记忆系统)" ;;
        backend/app/services/project/*)
            NEEDS_CHECK="$NEEDS_CHECK\n- docs/04-modules/backend/project-service.md (项目服务)" ;;
        backend/app/services/security/*)
            NEEDS_CHECK="$NEEDS_CHECK\n- docs/04-modules/backend/security-*.md (安全服务)" ;;
        backend/app/services/knowledge/*)
            NEEDS_CHECK="$NEEDS_CHECK\n- docs/04-modules/backend/knowledge-*.md (知识服务)" ;;
        backend/app/services/equipment/*)
            NEEDS_CHECK="$NEEDS_CHECK\n- docs/04-modules/backend/equipment-*.md (装备服务)" ;;
        backend/app/core/*)
            NEEDS_CHECK="$NEEDS_CHECK\n- docs/01-project/architecture.md\n- docs/03-development/setup.md (核心配置)" ;;
        backend/app/prompts/*)
            NEEDS_CHECK="$NEEDS_CHECK\n- docs/04-modules/backend/prompt-registry.md (Prompt 模板)" ;;
        backend/agents/*)
            NEEDS_CHECK="$NEEDS_CHECK\n- docs/02-design/agent-model.md (Agent 人才库)" ;;
        frontend/src/components/*)
            NEEDS_CHECK="$NEEDS_CHECK\n- docs/04-modules/frontend/ (前端组件)" ;;
        frontend/src/lib/*)
            NEEDS_CHECK="$NEEDS_CHECK\n- docs/04-modules/frontend/ (前端工具)" ;;
    esac
}

# 检查每个变更的文件
for f in $CHANGED_FILES; do
    check_mapping "$f"
done

# 如果有需要检查的文档，输出提醒
if [ -n "$NEEDS_CHECK" ]; then
    echo ""
    echo "=========================================="
    echo "[DOC SYNC] 代码已修改，以下文档可能需要同步更新："
    echo -e "$NEEDS_CHECK"
    echo ""
    echo "运行 /doc-sync 检查具体差异"
    echo "=========================================="
    echo ""
fi
