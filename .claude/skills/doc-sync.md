# doc-sync

检查代码变更对应的文档是否需要更新。

## 触发方式

- 用户输入 `/doc-sync`
- Hook 自动触发（代码修改后）

## 执行步骤

1. **识别变更范围**
   - 如果是手动触发，询问用户要检查哪些文件
   - 如果是 Hook 触发，使用 `$CLAUDE_FILE_PATHS` 环境变量

2. **映射代码 → 文档**
   根据以下映射表查找相关文档：

   | 代码路径 | 文档路径 |
   |---------|---------|
   | `backend/app/api/` | `docs/05-api/` |
   | `backend/app/models/` | `docs/04-modules/backend/models/` |
   | `backend/app/services/agent/` | `docs/04-modules/backend/agent-*.md` |
   | `backend/app/services/collaboration/` | `docs/04-modules/backend/pipeline-*.md`, `docs/02-design/collaboration.md` |
   | `backend/app/services/memory/` | `docs/04-modules/backend/memory-*.md`, `docs/02-design/memory-system.md` |
   | `backend/app/services/project/` | `docs/04-modules/backend/project-service.md` |
   | `backend/app/services/security/` | `docs/04-modules/backend/security-*.md` |
   | `backend/app/services/knowledge/` | `docs/04-modules/backend/knowledge-*.md` |
   | `backend/app/services/equipment/` | `docs/04-modules/backend/equipment-*.md` |
   | `backend/app/core/` | `docs/01-project/architecture.md`, `docs/03-development/setup.md` |
   | `backend/app/prompts/` | `docs/04-modules/backend/prompt-registry.md` |
   | `backend/agents/` | `docs/02-design/agent-model.md` |
   | `frontend/src/components/` | `docs/04-modules/frontend/` |
   | `frontend/src/lib/store.ts` | `docs/04-modules/frontend/` |

3. **检查文档是否需要更新**
   - 读取相关文档，检查是否描述了变更的代码
   - 如果文档描述了但内容过时，标记为"需要更新"
   - 如果文档未描述新增功能，标记为"需要新增"

4. **输出检查结果**
   ```
   [DOC SYNC] 检查完成：
   - 需要更新: docs/04-modules/backend/memory-service.md (L1 生命周期描述过时)
   - 需要更新: docs/02-design/memory-system.md (上下文压缩策略未记录)
   - 无需更新: docs/05-api/agents.md
   ```

5. **询问用户是否执行更新**
   - 如果用户确认，自动更新文档
   - 更新后检查版本号是否需要升级
