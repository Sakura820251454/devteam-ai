# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

DevTeam-AI is a multi-agent collaborative development platform. A FastAPI backend orchestrates AI agents (powered by LLMs) that collaborate through a pipeline system to perform software development tasks. A React frontend provides visualization and human intervention capabilities.

## Development commands

### Backend (Python 3.11+ / FastAPI)

```bash
cd backend
# Create venv and install
python -m venv venv
source venv/Scripts/activate  # Windows; use bin/activate on Unix
pip install -e ".[dev]"

# Run dev server
uvicorn app.main:app --reload --port 8000

# Run all tests (requires LLM_MODE=mock)
pytest tests/ -v

# Run specific test categories
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/e2e/ -v

# Run a single test file/class/test
pytest tests/unit/agent/test_llm_config.py -v
pytest tests/unit/agent/test_agent_service.py::TestAgentLifecycle -v

# Lint
ruff check .
```

### Frontend (React 18 / TypeScript / Vite)

```bash
cd frontend
npm install

# Dev server (port 3000, proxies /api to localhost:8000)
npm run dev

# Type-check
npx tsc --noEmit

# Lint
npm run lint

# Run unit tests (vitest)
npm test
npm run test:run          # single run, no watch

# Run E2E tests (Playwright)
npm run test:e2e
npm run test:e2e:ui       # Playwright UI mode
```

### Docs (VitePress)

```bash
cd docs
npm install
npm run docs:dev          # dev server
npm run docs:build        # production build
```

### CI

CI (`.github/workflows/ci.yml`) runs: Python Ruff lint + pytest with `LLM_MODE=mock`, TypeScript `tsc --noEmit` + Vite build, and VitePress build. CodeQL security analysis runs weekly.

## Architecture

### Backend layer structure

```
api/        → Thin route handlers (APIRouters), define request/response Pydantic models
services/   → Business logic. Organized by domain: agent/, collaboration/, memory/, equipment/, execution/, knowledge/, learning/, llm/, security/, shared/
models/     → SQLAlchemy ORM models (tables)
core/       → Settings (pydantic-settings from .env), LLM abstraction layer
database/   → Async SQLAlchemy engine + session factory (SQLite for dev, PostgreSQL for prod)
```

**Pattern**: API routers call service-layer singletons (e.g., `task_board`, `stuck_detector`, `task_persistence_service`). Services are Python class instances initialized at app startup via `lifespan`.

### LLM subsystem (`app/core/`)

- **LLM mode switching**: `LLM_MODE=mock` forces all providers to mock (no API key needed); `LLM_MODE=real` uses live APIs
- **Multi-provider**: DeepSeek (default), OpenAI, Anthropic, Azure — configured via `.env`
- **Per-agent LLM config**: Each agent can override provider/model/temperature; falls back to `default_llm_provider`/`default_llm_model` from settings
- Models and pricing are defined in `llm_models.py`

### Agent system

- **Soul files** (`backend/agents/*/soul.md`): Markdown files defining personality, skills, knowledge domains, collaboration style for each agent
- **Agent pool**: Agents are loaded from soul files; the frontend's `AgentPoolModal` allows selecting which agents participate in a project
- **Agent executor** (`services/agent/agent_executor.py`): Handles task execution with step planning, checkpoint/resume, and pause support

### Collaboration system

- **Pipeline** (`services/collaboration/pipeline_orchestrator.py`): 6-stage pipeline (需求分析 → 任务拆解 → 编码实现 → 代码审查 → 测试验证 → 交付部署). Each stage assigns agents based on their roles.
- **Message bus**: Event-driven communication between agents
- **Speaking controller**: Turn-based speaking with hand-raising and rate limiting
- **Task board**: Kanban-style task management with status flow BACKLOG → TODO → IN_PROGRESS → REVIEW → DONE
- **Arbitrator**: Conflict resolution between agents

### Execution recovery (`services/execution/`)

- **Checkpoints**: Task state snapshots for resume after interruption
- **Stuck detection**: Background monitor (`stuck_detector`) that polls for stalled tasks
- **Task persistence**: Durable task state via `task_persistence_service`

### Frontend architecture

```
components/  → 14 React components (AgentConfigModal is the most complex at 22KB)
lib/api.ts   → Single API client module, all REST calls to /api/*
lib/store.ts → Single Zustand store with all app state
lib/simulation.ts → Frontend-only simulation logic (41KB) for demo/offline use
pages/       → Page-level components (Home.tsx is the main page, 10KB)
types/       → Shared TypeScript type definitions
```

**State management**: One Zustand store (`useStore`) holds pipeline state, agent list, tasks, chat messages, timeline events, terminal logs, cost data, execution tracking, and intervention mode. Actions are defined inline in the store.

**API communication**: The Vite dev server proxies `/api` to `localhost:8000`. The API client (`lib/api.ts`) defines typed request/response interfaces matching the backend Pydantic models.

### Data flow

1. User creates a project → `startProject()` in store sets up default pipeline + agents, calls `POST /api/workspaces` to create physical workspace
2. Pipeline orchestrator advances through stages, assigning agents to tasks
3. Agents "speak" via the speaking controller; messages appear in chat panel
4. Humans can intervene (whisper/broadcast/pause) via `InterventionPanel`
5. Execution is tracked with step-level granularity; stuck tasks are detected and surfaced

### Multi-project support

The system supports multiple projects running concurrently. Key design:

- **Agent-Project binding**: An agent can only belong to one project at a time. `AgentService.assign_agent_to_project()` enforces this exclusivity. Pipeline creation validates all agents are available; pipeline completion/stop releases them.
- **Project-scoped state**: All service dicts are nested by `project_id` (e.g., `TaskBoard._tasks[project_id][task_id]`). Global flags (pause, stop) moved to per-project fields on the `Pipeline` object.
- **Frontend store**: `agentsByProject`, `pipelines`, `tasksByProject`, etc. are `Record<string, ...>` keyed by `project_id`. `activeProjectId` tracks the currently viewed project. `ProjectSwitcher` component provides tab-based navigation.
- **Cleanup cascade**: `ProjectService.delete_project()` cascades through all services (stop pipeline, release agents, clear tasks/messages/issues, delete workspace).

### Testing strategy

- **Backend unit tests** (`tests/unit/`): Organized by domain (agent, collaboration, equipment, knowledge, learning, llm, memory). Use mock LLM.
- **Backend integration tests** (`tests/integration/`): Cross-service flows (collaboration, cost tracking, execution recovery, etc.)
- **Backend E2E tests** (`tests/e2e/`): Full project lifecycle simulations
- **Frontend unit tests**: Vitest with jsdom, configured but no tests written yet
- **Frontend E2E**: Playwright, configured but minimal

Always set `LLM_MODE=mock` when running backend tests to avoid real API calls.

### Key configuration

- `.env` at `backend/.env` — LLM provider keys, mode, database URL
- `backend/app/core/config.py` — Settings class with all env vars
- `frontend/vite.config.ts` — Dev server port (3000) and API proxy
- `backend/agents/*/soul.md` — Agent persona definitions
