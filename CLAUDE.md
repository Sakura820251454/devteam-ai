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

## Documentation

- 架构变更 → ADR (`docs/02-design/decisions/`)
- 新模块/公开接口变更 → 模块文档 (`docs/04-modules/`)
- 代码中非显而易见的"为什么" → 中文注释

## Per-directory rules

- `backend/CLAUDE.md` — 后端编码规则（prompt 管理、AI 安全网、状态机）
- `backend/tests/CLAUDE.md` — 测试策略和规范
- `frontend/CLAUDE.md` — 前端约定
