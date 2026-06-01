# CLAUDE.md

## Project overview

DevTeam-AI is a multi-agent collaborative development platform. FastAPI backend + React frontend + VitePress docs.

## Development commands

```bash
# Backend (Python 3.12 at C:/Users/AA/python-sdk/python3.12.9)
cd backend
C:/Users/AA/python-sdk/python3.12.9/python.exe -m uvicorn app.main:app --reload --port 8000
pytest tests/ -v                    # LLM_MODE=mock required
ruff check .

# Frontend (React 18 / TypeScript / Vite)
cd frontend
npm run dev                         # port 3000, proxies /api → localhost:8000
npx tsc --noEmit
npm run lint
npm test

# Docs (VitePress)
npm run docs:dev
npm run docs:build
```

## Key config files

- `backend/.env` — LLM keys, mode, database URL
- `backend/app/core/config.py` — Settings class
- `frontend/vite.config.ts` — port, API proxy
- `backend/agents/*/soul.md` — agent personas

## Testing & CI

- Backend: `pytest tests/ -v`（`LLM_MODE=mock`）
- Frontend: Vitest (unit) + Playwright (e2e)
- CI: Ruff lint + pytest, `tsc --noEmit` + Vite build, VitePress build

## Documentation — AI 项目记忆规范（硬性规则）

**文档定位**：`docs/` 不是给人看的产品文档，是 Claude Code 的**项目记忆**。当 AI 遗忘开发细节时，必须能从文档中快速恢复上下文。

### 文档分类

| 类型 | 作用 | 生命周期 |
|------|------|---------|
| **结果文档** | 反映当前状态（架构、模块、API） | 随代码同步更新 |
| **过程文档** | 反映演进过程（设计、调研、决策变更） | 只增不改，保留历史 |

### 结果文档（随代码更新）

描述系统**现在是什么样**。修改代码后，检查 `docs/` 下是否有文档描述了你改的这部分内容。如果有，同步更新；如果没有，视重要性决定是否新建。

### 过程文档（只增不改）

记录**为什么变成这样**。以下情况需要写过程文档：

| 场景 | 记录内容 |
|------|---------|
| 设计决策 | 为什么选 A 不选 B，权衡了什么 |
| 技术调研 | 调研了哪些方案，结论是什么，参考链接 |
| 计划变更 | 原计划是什么，为什么改，新计划是什么 |
| 功能推翻重做 | 原方案哪里不行，新方案怎么解决 |
| 与用户沟通 | 达成了什么共识，确认了什么约束 |

**存放位置**：`docs/process/` 目录，按日期命名：
```
docs/process/
├── 2026-05-29-memory-system-research.md    # 调研
├── 2026-05-30-pipeline-redesign.md         # 重新设计
├── 2026-05-31-agent-role-discussion.md     # 沟通记录
└── ...
```

**写作格式**：
```markdown
# 标题
日期: YYYY-MM-DD | 状态: 进行中/已完成/已废弃

## 背景
为什么要做这件事

## 过程/方案
具体做了什么，考虑了哪些选项

## 结论
最终决定是什么，对后续开发的影响
```

### 核心原则

1. **结果文档反映当前状态** — 随代码同步更新，过时就修正
2. **过程文档保留历史** — 只增不改，记录"为什么"
3. **单一来源** — 同一信息只在一个文档中描述，其他地方引用
4. **不堆砌** — 每个文档只解决一个问题

### 自检清单（每次提交前）

- [ ] 本次代码变更涉及的结果文档是否已更新？
- [ ] 本次有设计决策/计划变更/调研吗？是否写了过程文档？
- [ ] 文档中描述的目录结构、函数名是否与代码一致？

### 自动化工具

**Skills**（在 Claude Code 中输入触发）：

| Skill | 用途 |
|-------|------|
| `/doc-sync` | 检查代码变更对应的文档是否需要更新 |
| `/doc-version` | 更新版本号和 changelog（发版前使用） |
| `/doc-check` | 全量检查文档与代码一致性（定期使用） |

**Hook**（自动触发）：
- 修改 `backend/app/` 或 `frontend/src/` 后，自动提醒检查相关文档
- 提示信息精确到具体文档路径（如 `[DOC SYNC] 记忆服务变更 → 检查 docs/02-design/memory-system.md`）

### 写作规范

- 用中文写，英文术语保留原文
- 结果文档开头写 `最后更新: YYYY-MM-DD | 对应代码版本: vX.Y`
- 过程文档开头写 `日期: YYYY-MM-DD | 状态: 进行中/已完成/已废弃`
- 不写产品宣传语（"强大的"、"完善的"），只写事实

## Per-directory rules

- `backend/CLAUDE.md` — 后端编码规则（prompt 管理、AI 安全网、状态机）
- `backend/tests/CLAUDE.md` — 测试策略和规范
- `frontend/CLAUDE.md` — 前端约定
