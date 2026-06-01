# doc-check

全量检查文档与代码的一致性。

## 触发方式

- 用户输入 `/doc-check`

## 执行步骤

1. **扫描文档结构**
   - 列出 `docs/` 下所有 .md 文件
   - 检查是否有死链（链接到不存在的文件）

2. **检查代码 → 文档覆盖**
   扫描以下代码目录，检查是否有对应文档：

   | 代码目录 | 应有文档 |
   |---------|---------|
   | `backend/app/api/*.py` | `docs/05-api/*.md` |
   | `backend/app/models/*.py` | `docs/04-modules/backend/models/*.md` |
   | `backend/app/services/**/*.py` | `docs/04-modules/backend/*.md` |
   | `frontend/src/components/*.tsx` | `docs/04-modules/frontend/*.md` |
   | `backend/agents/*/soul.md` | `docs/02-design/agent-model.md` 中应有描述 |

3. **检查文档 → 代码准确性**
   对每个文档：
   - 提取文档中提到的函数名、类名、API 路径
   - 在代码中搜索是否真实存在
   - 检查参数签名是否一致

4. **检查版本号一致性**
   - 扫描所有文档头部的版本号
   - 检查是否有版本号冲突（同一文档头尾版本号不一致）
   - 检查 changelog 版本是否与其他文档一致

5. **检查实现状态标记**
   - 扫描文档中的 ⚠️/❌ 标记
   - 验证标记的功能是否确实未实现

6. **生成检查报告**
   ```
   [DOC CHECK] 全量检查完成：

   📊 统计：
   - 文档总数: 47 个
   - 代码覆盖: 85% (36/42 模块有对应文档)
   - 版本一致: ✅
   - 死链: 0 个

   ⚠️ 发现问题：
   1. docs/04-modules/backend/memory-service.md 描述的 get_context_window() 签名与代码不一致
   2. backend/app/services/learning/pattern_discovery.py 无对应文档
   3. docs/02-design/self-learning.md 中"模式发现"标记为❌但代码中有基础实现

   详细报告已写入 docs/08-tracker/check-report-YYYY-MM-DD.md
   ```

7. **询问用户是否修复**
   - 如果用户确认，逐个修复发现的问题
   - 修复完成后更新 docs/08-tracker/
