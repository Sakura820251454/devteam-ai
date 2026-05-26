# CLAUDE.md

## Project overview

DevTeam-AI is a multi-agent collaborative development platform. FastAPI backend orchestrates AI agents through a pipeline system; React frontend provides visualization and human intervention.

## Development commands

### Backend (Python 3.12 / FastAPI)

```bash
# Python 3.12 at: C:\Users\AA\python-sdk\python3.12.9
C:/Users/AA/python-sdk/python3.12.9/python.exe -m uvicorn app.main:app --reload --port 8000
pytest tests/ -v              # LLM_MODE=mock required
ruff check .
```

### Frontend (React 18 / TypeScript / Vite)

```bash
npm run dev                   # port 3000, proxies /api → localhost:8000
npx tsc --noEmit
npm run lint
npm test
```

### Docs (VitePress)

```bash
npm run docs:dev
npm run docs:build
```

## Testing & CI

- Backend: `pytest tests/ -v` with `LLM_MODE=mock`
- Frontend: Vitest (unit) + Playwright (e2e)
- CI: Python Ruff lint + pytest, TypeScript `tsc --noEmit` + Vite build, VitePress build

## Key config files

- `backend/.env` — LLM keys, mode, database URL
- `backend/app/core/config.py` — Settings class
- `frontend/vite.config.ts` — port, API proxy
- `backend/agents/*/soul.md` — agent personas

## Task persistence rule

When working through a multi-phase plan with TaskCreate tasks, **do not abandon incomplete tasks** after finishing the first few. Before ending a session or reporting "done", always check TaskList and explicitly report which tasks were completed and which remain. If the user interrupts with a new direction mid-plan, note which tasks are paused and will need resumption. This prevents half-finished implementations where earlier phases are done but later phases are forgotten.

## Prompt management

All LLM prompts live in `backend/app/prompts/registry.yaml` as the single source of truth — never write f-string prompts in code.
Use `registry.render(id, vars)` instead. After changing prompts, run `python scripts/prompt_doc_gen.py` to update docs.

## Documentation maintenance

Use `documentation-and-adrs` skill. Before writing docs, search existing ones to avoid conflicts.
If overriding a prior decision, write an ADR explaining why and mark the old one superseded.

- Direction/architecture change → ADR (`docs/02-design/decisions/`)
- New feature/module → module doc (`04-modules/`) + API doc if public-facing
- Modified behavior → update corresponding doc in `04-modules/` or `05-api/`
- New data model → update `04-modules/backend/models/`
