import { useStore } from './store'
import type { Task } from './store'
import { addArtifact, addWorkspaceLog, updateWorkspaceStatus } from './api'

const AGENTS = {
  pm:        { id: 'pm',        name: '产品经理',   color: '#58a6ff' },
  architect: { id: 'architect', name: '架构师',     color: '#a371f7' },
  backend:   { id: 'backend',   name: '后端开发',   color: '#3fb950' },
  frontend:  { id: 'frontend',  name: '前端开发',   color: '#f0883e' },
  tester:    { id: 'tester',    name: '测试工程师', color: '#f85149' },
  devops:    { id: 'devops',    name: 'DevOps',     color: '#39d2c0' },
}

function s() { return useStore.getState() }

type StepFn = () => void

export function startSimulation(projectName: string, projectDesc: string): () => void {
  const timers: ReturnType<typeof setTimeout>[] = []
  let stopped = false

  function schedule(delayMs: number, fn: StepFn) {
    if (stopped) return
    const t = setTimeout(() => {
      if (stopped) return
      fn()
    }, delayMs)
    timers.push(t)
  }

  // Write artifact file to backend workspace
  function writeArtifact(stageKey: string, name: string, content: string) {
    const pid = s().pipeline?.id
    if (!pid) return
    addArtifact(pid, stageKey, name, content).catch(() => {})
  }

  // Write log to backend workspace
  function writeLog(level: string, source: string, message: string) {
    const pid = s().pipeline?.id
    if (!pid) return
    addWorkspaceLog(pid, level, source, message).catch(() => {})
  }

  function chat(agent: typeof AGENTS.pm, content: string, delayMs: number) {
    schedule(delayMs, () => {
      s().addChatMessage({ agentId: agent.id, agentName: agent.name, agentColor: agent.color, content })
    })
  }

  function event(
    type: 'decision' | 'action' | 'message' | 'status_change' | 'artifact',
    agent: typeof AGENTS.pm,
    content: string,
    detail: string | undefined,
    importance: 'normal' | 'important' | 'critical',
    delayMs: number,
  ) {
    schedule(delayMs, () => {
      s().addEvent({ type, agentId: agent.id, agentName: agent.name, agentColor: agent.color, content, detail, importance })
    })
  }

  function log(level: 'info' | 'success' | 'warn' | 'error' | 'debug', source: string, message: string, delayMs: number) {
    schedule(delayMs, () => { s().addLog({ level, source, message }) })
  }

  function updateStage(stageKey: string, updates: Record<string, unknown>, delayMs: number) {
    schedule(delayMs, () => { s().updatePipelineStage(stageKey, updates as any) })
  }

  function setStageStatus(stageKey: string, status: 'pending' | 'active' | 'completed' | 'blocked', delayMs: number) {
    schedule(delayMs, () => {
      const now = new Date().toISOString()
      const updates: any = { status }
      if (status === 'active') updates.startedAt = now
      if (status === 'completed') updates.completedAt = now
      s().updatePipelineStage(stageKey, updates)
    })
  }

  function setProgress(progress: number, currentStage: string, delayMs: number) {
    schedule(delayMs, () => {
      const p = s().pipeline
      if (p) s().setPipeline({ ...p, progress, currentStage })
    })
  }

  function setCostData(delayMs: number) {
    schedule(delayMs, () => {
      const state = s()
      const agents = state.agents
      const globalCfg = state.globalLlmConfig

      const agentCosts: Record<string, { cost: number; tokens: number; calls: number }> = {
        '产品经理':   { cost: 0.028, tokens: 15000, calls: 5 },
        '架构师':     { cost: 0.052, tokens: 32000, calls: 7 },
        '后端开发':   { cost: 0.045, tokens: 26000, calls: 5 },
        '前端开发':   { cost: 0.035, tokens: 18000, calls: 4 },
        '测试工程师': { cost: 0.018, tokens: 9000,  calls: 2 },
        '运维工程师': { cost: 0.008, tokens: 4000,  calls: 1 },
        'DevOps':     { cost: 0.008, tokens: 4000,  calls: 1 },
      }

      const byAgent: Record<string, { cost: number; tokens: number; calls: number }> = {}
      const byModel: Record<string, { cost: number; tokens: number; calls: number }> = {}

      if (agents.length > 0) {
        for (const agent of agents) {
          const baseCost = agentCosts[agent.role] || { cost: 0.015, tokens: 8000, calls: 3 }
          byAgent[agent.name] = { ...baseCost }

          const model = agent.llm_config?.model || globalCfg.model
          if (!byModel[model]) {
            byModel[model] = { cost: 0, tokens: 0, calls: 0 }
          }
          byModel[model].cost += baseCost.cost
          byModel[model].tokens += baseCost.tokens
          byModel[model].calls += baseCost.calls
        }
      } else {
        // Fallback: no agents in store — use global defaults
        byAgent['产品经理']   = agentCosts['产品经理']
        byAgent['架构师']     = agentCosts['架构师']
        byAgent['后端开发']   = agentCosts['后端开发']
        byAgent['前端开发']   = agentCosts['前端开发']
        byAgent['测试工程师'] = agentCosts['测试工程师']
        byAgent['运维工程师'] = agentCosts['运维工程师']

        const model = globalCfg.model
        const totalCost = Object.values(byAgent).reduce((s, a) => s + a.cost, 0)
        const totalTokens = Object.values(byAgent).reduce((s, a) => s + a.tokens, 0)
        const totalCalls = Object.values(byAgent).reduce((s, a) => s + a.calls, 0)
        byModel[model] = { cost: totalCost, tokens: totalTokens, calls: totalCalls }
      }

      // Round costs to 3 decimal places
      for (const key of Object.keys(byModel)) {
        byModel[key].cost = Math.round(byModel[key].cost * 1000) / 1000
      }
      for (const key of Object.keys(byAgent)) {
        byAgent[key].cost = Math.round(byAgent[key].cost * 1000) / 1000
      }

      const totalCost = Object.values(byAgent).reduce((s, a) => s + a.cost, 0)
      const totalTokens = Object.values(byAgent).reduce((s, a) => s + a.tokens, 0)
      const promptTokens = Math.round(totalTokens * 0.72)
      const completionTokens = totalTokens - promptTokens
      const callCount = Object.values(byAgent).reduce((s, a) => s + a.calls, 0)

      s().setCostData({
        totalCost: Math.round(totalCost * 1000) / 1000,
        totalTokens,
        promptTokens,
        completionTokens,
        callCount,
        byAgent,
        byModel,
      })
    })
  }

  // ================================================================
  // PHASE 1: Requirement Analysis (0s - 4s)
  // ================================================================
  schedule(200, () => {
    s().updatePipelineStage('requirement_analysis', { status: 'active', startedAt: new Date().toISOString() })
    s().updateAgentStatus('pm', 'thinking')
    s().addLog({ level: 'info', source: 'pipeline', message: '阶段开始: 需求分析' })
    s().addLog({ level: 'info', source: 'pm', message: '正在分析项目需求...' })
  })

  chat(AGENTS.pm, `收到新项目需求：「${projectName}」。让我先梳理一下核心诉求。`, 800)
  chat(AGENTS.pm, `根据需求描述"${projectDesc.slice(0, 80)}${projectDesc.length > 80 ? '...' : ''}"，我识别出以下几个核心功能模块需要进一步细化。`, 1800)

  schedule(2200, () => s().updateAgentStatus('architect', 'thinking'))
  chat(AGENTS.architect, '产品经理的分析很有条理，我现在开始考虑技术方案的可行性。', 2500)

  chat(AGENTS.pm, '我整理出了需求规格说明，包括用户故事、功能边界和非功能需求。架构师可以开始技术预研了。', 3000)

  event('decision', AGENTS.pm, '需求分析完成，识别出核心功能模块', '产出 8 条用户故事和需求规格说明 v1.0', 'important', 3500)
  event('artifact', AGENTS.pm, '产出需求规格说明 v1.0', '包含功能边界、非功能需求和验收标准', 'normal', 3600)

  log('success', 'pm', '需求分析完成，产出 8 条用户故事', 3700)

  setStageStatus('requirement_analysis', 'completed', 3800)
  updateStage('requirement_analysis', { artifacts: ['需求规格说明 v1.0', '用户故事 8条'] }, 3900)

  schedule(3950, () => writeArtifact('requirement_analysis', '需求规格说明_v1.0.md',
    `# 需求规格说明 v1.0\n\n## 项目\n${projectName}\n\n## 需求描述\n${projectDesc}\n\n## 核心功能模块\n1. 用户管理\n2. 权限控制\n3. 数据展示\n4. 系统配置\n\n## 非功能需求\n- 响应时间 < 200ms\n- 支持 1000 并发\n- 数据安全加密\n\n## 验收标准\n- 所有用户故事通过测试\n- 代码审查评分 A- 以上`))

  schedule(3960, () => writeArtifact('requirement_analysis', '用户故事.md',
    `# 用户故事\n\n1. 作为用户，我希望能注册账号\n2. 作为管理员，我希望能管理用户权限\n3. 作为用户，我希望能查看个人数据\n4. 作为用户，我希望能导出数据报告\n5. 作为开发者，我希望能查看 API 文档\n6. 作为运维，我希望能监控系统状态\n7. 作为用户，我希望能修改个人信息\n8. 作为管理员，我希望能查看操作审计日志`))

  schedule(3970, () => { writeLog('info', 'pipeline', '阶段完成: 需求分析'); writeLog('success', 'pm', '产出需求规格说明 v1.0 + 8 条用户故事') })

  setProgress(0.17, 'task_breakdown', 4000)

  // ================================================================
  // PHASE 2: Task Breakdown (4s - 10s)
  // ================================================================
  schedule(4200, () => {
    s().addLog({ level: 'info', source: 'pipeline', message: '阶段开始: 任务拆解' })
    s().updateAgentStatus('pm', 'working')
    s().updateAgentStatus('architect', 'working')
  })
  setStageStatus('task_breakdown', 'active', 4200)

  chat(AGENTS.pm, '现在开始将需求拆解为具体的技术任务。我会按照前端、后端、测试三个维度来划分。', 4500)

  chat(AGENTS.architect, '我建议采用 FastAPI + React + PostgreSQL 的技术栈。前端用 Tailwind CSS，后端 RESTful API 设计。', 5000)

  event('decision', AGENTS.architect, '技术方案选定：FastAPI + React + PostgreSQL', '前后端分离，RESTful API，JWT 认证', 'important', 5500)

  chat(AGENTS.pm, '好的，基于这个技术方案，我来拆解任务：\n1. 数据库表结构设计\n2. 用户认证 API\n3. 前端登录页面\n4. API 单元测试\n5. CI/CD 部署配置', 6000)

  chat(AGENTS.architect, '数据库设计我建议从用户表、角色表、权限表开始，保持第三范式。认证用 JWT + refresh token 方案。', 7000)

  // Create mock tasks
  schedule(8000, () => {
    const now = new Date().toISOString()
    const tasks: Task[] = [
      {
        id: 'task-1', title: '数据库表结构设计', description: '设计用户、角色、权限等核心表', status: 'done', priority: 'high',
        stage: 'task_breakdown', assignedAgents: ['architect', 'backend'], createdBy: 'pm',
        statusHistory: [
          { from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 3000).toISOString(), by: 'pm' },
          { from: 'todo', to: 'in_progress', timestamp: new Date(Date.now() - 2000).toISOString(), by: 'architect' },
          { from: 'in_progress', to: 'done', timestamp: now, by: 'architect' },
        ],
        tags: ['database', 'schema'], createdAt: new Date(Date.now() - 4000).toISOString(), updatedAt: now,
      },
      {
        id: 'task-2', title: '实现用户认证 API', description: 'JWT 登录、注册、token 刷新', status: 'in_progress', priority: 'high',
        stage: 'task_breakdown', assignedAgents: ['backend'], createdBy: 'pm',
        statusHistory: [
          { from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 3000).toISOString(), by: 'pm' },
          { from: 'todo', to: 'in_progress', timestamp: now, by: 'backend' },
        ],
        tags: ['api', 'auth', 'jwt'], createdAt: new Date(Date.now() - 4000).toISOString(), updatedAt: now,
      },
      {
        id: 'task-3', title: '前端登录页面开发', description: '登录/注册表单、表单验证、token 存储', status: 'todo', priority: 'medium',
        stage: 'task_breakdown', assignedAgents: ['frontend'], createdBy: 'pm',
        statusHistory: [
          { from: 'backlog', to: 'todo', timestamp: now, by: 'pm' },
        ],
        tags: ['frontend', 'ui', 'auth'], createdAt: new Date(Date.now() - 2000).toISOString(), updatedAt: now,
      },
      {
        id: 'task-4', title: '编写 API 单元测试', description: '对认证 API 编写全面的单元测试和集成测试', status: 'todo', priority: 'medium',
        stage: 'task_breakdown', assignedAgents: ['tester'], createdBy: 'backend',
        statusHistory: [
          { from: 'backlog', to: 'todo', timestamp: now, by: 'backend' },
        ],
        tags: ['testing', 'api'], createdAt: new Date(Date.now() - 1000).toISOString(), updatedAt: now,
      },
      {
        id: 'task-5', title: 'CI/CD Pipeline 配置', description: '配置 GitHub Actions 自动化构建、测试、部署', status: 'backlog', priority: 'low',
        stage: 'task_breakdown', assignedAgents: ['devops'], createdBy: 'pm',
        statusHistory: [
          { from: 'backlog', to: 'backlog', timestamp: now, by: 'pm' },
        ],
        tags: ['devops', 'ci/cd'], createdAt: now, updatedAt: now,
      },
    ]
    s().setTasks(tasks)
  })

  event('action', AGENTS.pm, '任务拆解完成，共创建 5 个技术任务', '已按优先级排序并分配给对应 Agent', 'important', 8500)
  log('success', 'taskboard', '任务看板已生成: 5 个任务', 8600)

  setStageStatus('task_breakdown', 'completed', 9000)
  updateStage('task_breakdown', { artifacts: ['任务列表 5项', '技术方案文档'] }, 9200)

  schedule(9250, () => writeArtifact('task_breakdown', '任务列表.md',
    `# 任务列表\n\n## 1. 数据库表结构设计 [高优先级]\n- 设计用户、角色、权限等核心表\n- 负责人: 架构师, 后端开发\n\n## 2. 实现用户认证 API [高优先级]\n- JWT 登录、注册、token 刷新\n- 负责人: 后端开发\n\n## 3. 前端登录页面开发 [中优先级]\n- 登录/注册表单、表单验证、token 存储\n- 负责人: 前端开发\n\n## 4. 编写 API 单元测试 [中优先级]\n- 对认证 API 编写全面的单元测试和集成测试\n- 负责人: 测试工程师\n\n## 5. CI/CD Pipeline 配置 [低优先级]\n- 配置 GitHub Actions 自动化构建、测试、部署\n- 负责人: DevOps`))

  schedule(9260, () => writeArtifact('task_breakdown', '技术方案文档.md',
    `# 技术方案文档\n\n## 技术栈\n- 后端: FastAPI + SQLAlchemy + PostgreSQL\n- 前端: React + TypeScript + Tailwind CSS\n- 认证: JWT (access_token 30min / refresh_token 7d)\n- 部署: Docker + GitHub Actions\n\n## 架构设计\n- 前后端分离，RESTful API\n- 分层架构: Router → Service → Repository\n- 异步数据库操作 (aiosqlite)\n\n## API 设计\n- POST /api/auth/login\n- POST /api/auth/register\n- POST /api/auth/refresh\n- GET /api/users/me\n- PATCH /api/users/me`))

  schedule(9270, () => writeLog('info', 'pipeline', '阶段完成: 任务拆解'))

  setProgress(0.33, 'coding', 9500)

  // ================================================================
  // PHASE 3: Coding (10s - 35s)
  // ================================================================
  schedule(10000, () => {
    s().addLog({ level: 'info', source: 'pipeline', message: '阶段开始: 编码实现' })
    s().updateAgentStatus('backend', 'working')
    s().updateAgentStatus('frontend', 'working')
  })
  setStageStatus('coding', 'active', 10000)

  chat(AGENTS.backend, '开始编写数据库模型和迁移脚本。使用 SQLAlchemy ORM，先建 users 表。', 10500)
  chat(AGENTS.frontend, '我先搭建 React 项目结构，配好路由和状态管理。', 11000)

  schedule(12000, () => {
    s().updateAgentStatus('backend', 'working')
    s().addLog({ level: 'info', source: 'backend', message: '正在创建数据库迁移脚本...' })
  })
  chat(AGENTS.backend, '数据库模型已创建完成：User, Role, Permission 三张表，外键关联正确。现在开始写认证 API。', 13000)

  schedule(13500, () => {
    s().updateAgentStatus('frontend', 'working')
    s().addLog({ level: 'info', source: 'frontend', message: '正在开发登录页面组件...' })
  })
  chat(AGENTS.frontend, '登录表单组件写好了，包含邮箱/密码验证、错误提示、loading 状态。现在对接后端 API。', 15000)

  chat(AGENTS.backend, 'JWT 认证中间件已实现。POST /api/auth/login 返回 access_token + refresh_token，过期时间 30min/7d。', 16500)

  event('action', AGENTS.backend, '后端认证 API 开发完成', '实现了登录、注册、token 刷新三个端点', 'normal', 17000)

  // Update task statuses
  schedule(18000, () => {
    const now = new Date().toISOString()
    s().setTasks([
      {
        id: 'task-1', title: '数据库表结构设计', description: '设计用户、角色、权限等核心表', status: 'done', priority: 'high',
        stage: 'coding', assignedAgents: ['architect', 'backend'], createdBy: 'pm',
        statusHistory: [
          { from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 15000).toISOString(), by: 'pm' },
          { from: 'todo', to: 'in_progress', timestamp: new Date(Date.now() - 12000).toISOString(), by: 'architect' },
          { from: 'in_progress', to: 'done', timestamp: now, by: 'architect' },
        ],
        tags: ['database', 'schema'], createdAt: new Date(Date.now() - 15000).toISOString(), updatedAt: now,
      },
      {
        id: 'task-2', title: '实现用户认证 API', description: 'JWT 登录、注册、token 刷新', status: 'review', priority: 'high',
        stage: 'coding', assignedAgents: ['backend'], createdBy: 'pm',
        statusHistory: [
          { from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 15000).toISOString(), by: 'pm' },
          { from: 'todo', to: 'in_progress', timestamp: new Date(Date.now() - 10000).toISOString(), by: 'backend' },
          { from: 'in_progress', to: 'review', timestamp: now, by: 'backend' },
        ],
        tags: ['api', 'auth', 'jwt'], createdAt: new Date(Date.now() - 15000).toISOString(), updatedAt: now,
      },
      {
        id: 'task-3', title: '前端登录页面开发', description: '登录/注册表单、表单验证、token 存储', status: 'in_progress', priority: 'medium',
        stage: 'coding', assignedAgents: ['frontend'], createdBy: 'pm',
        statusHistory: [
          { from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 15000).toISOString(), by: 'pm' },
          { from: 'todo', to: 'in_progress', timestamp: new Date(Date.now() - 5000).toISOString(), by: 'frontend' },
        ],
        tags: ['frontend', 'ui', 'auth'], createdAt: new Date(Date.now() - 15000).toISOString(), updatedAt: now,
      },
      {
        id: 'task-4', title: '编写 API 单元测试', description: '对认证 API 编写全面的单元测试和集成测试', status: 'todo', priority: 'medium',
        stage: 'coding', assignedAgents: ['tester'], createdBy: 'backend',
        statusHistory: [
          { from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 10000).toISOString(), by: 'backend' },
        ],
        tags: ['testing', 'api'], createdAt: new Date(Date.now() - 15000).toISOString(), updatedAt: now,
      },
      {
        id: 'task-5', title: 'CI/CD Pipeline 配置', description: '配置 GitHub Actions 自动化构建、测试、部署', status: 'backlog', priority: 'low',
        stage: 'coding', assignedAgents: ['devops'], createdBy: 'pm',
        statusHistory: [
          { from: 'backlog', to: 'backlog', timestamp: new Date(Date.now() - 15000).toISOString(), by: 'pm' },
        ],
        tags: ['devops', 'ci/cd'], createdAt: new Date(Date.now() - 15000).toISOString(), updatedAt: now,
      },
    ])
  })

  chat(AGENTS.frontend, '前后端联调成功！登录流程跑通了。token 自动存储到 localStorage，axios 拦截器自动附加 Authorization header。', 20000)

  event('status_change', AGENTS.frontend, '任务「前端登录页面开发」进展更新', undefined, 'normal', 21000)

  chat(AGENTS.architect, '看了后端的代码，认证逻辑没问题。建议把 token 黑名单机制加上，方便后续做登出功能。', 23000)

  chat(AGENTS.backend, '好的，我加一个 redis 缓存层做 token 黑名单。同时在响应头里加 X-Request-Id 方便追踪。', 25000)

  event('action', AGENTS.frontend, '前端登录页面开发完成', '包含表单验证、错误处理、loading 状态', 'normal', 27000)

  // Update tasks again
  schedule(28000, () => {
    const now = new Date().toISOString()
    s().setTasks([
      {
        id: 'task-1', title: '数据库表结构设计', description: '', status: 'done', priority: 'high',
        stage: 'coding', assignedAgents: ['architect', 'backend'], createdBy: 'pm',
        statusHistory: [
          { from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 25000).toISOString(), by: 'pm' },
          { from: 'todo', to: 'in_progress', timestamp: new Date(Date.now() - 22000).toISOString(), by: 'architect' },
          { from: 'in_progress', to: 'done', timestamp: now, by: 'architect' },
        ],
        tags: ['database', 'schema'], createdAt: new Date(Date.now() - 25000).toISOString(), updatedAt: now,
      },
      {
        id: 'task-2', title: '实现用户认证 API', description: '', status: 'done', priority: 'high',
        stage: 'coding', assignedAgents: ['backend'], createdBy: 'pm',
        statusHistory: [
          { from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 25000).toISOString(), by: 'pm' },
          { from: 'todo', to: 'in_progress', timestamp: new Date(Date.now() - 20000).toISOString(), by: 'backend' },
          { from: 'in_progress', to: 'review', timestamp: new Date(Date.now() - 10000).toISOString(), by: 'backend' },
          { from: 'review', to: 'done', timestamp: now, by: 'architect' },
        ],
        tags: ['api', 'auth', 'jwt'], createdAt: new Date(Date.now() - 25000).toISOString(), updatedAt: now,
      },
      {
        id: 'task-3', title: '前端登录页面开发', description: '', status: 'done', priority: 'medium',
        stage: 'coding', assignedAgents: ['frontend'], createdBy: 'pm',
        statusHistory: [
          { from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 25000).toISOString(), by: 'pm' },
          { from: 'todo', to: 'in_progress', timestamp: new Date(Date.now() - 15000).toISOString(), by: 'frontend' },
          { from: 'in_progress', to: 'done', timestamp: now, by: 'frontend' },
        ],
        tags: ['frontend', 'ui', 'auth'], createdAt: new Date(Date.now() - 25000).toISOString(), updatedAt: now,
      },
      {
        id: 'task-4', title: '编写 API 单元测试', description: '', status: 'in_progress', priority: 'medium',
        stage: 'coding', assignedAgents: ['tester'], createdBy: 'backend',
        statusHistory: [
          { from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 20000).toISOString(), by: 'backend' },
          { from: 'todo', to: 'in_progress', timestamp: now, by: 'tester' },
        ],
        tags: ['testing', 'api'], createdAt: new Date(Date.now() - 25000).toISOString(), updatedAt: now,
      },
      {
        id: 'task-5', title: 'CI/CD Pipeline 配置', description: '', status: 'todo', priority: 'low',
        stage: 'coding', assignedAgents: ['devops'], createdBy: 'pm',
        statusHistory: [
          { from: 'backlog', to: 'todo', timestamp: now, by: 'pm' },
        ],
        tags: ['devops', 'ci/cd'], createdAt: new Date(Date.now() - 25000).toISOString(), updatedAt: now,
      },
    ])
  })

  log('success', 'backend', '编码阶段完成: 2个API模块，6个端点', 30000)
  log('success', 'frontend', '前端组件完成: 登录页、路由配置、API 对接', 30500)

  updateStage('coding', { artifacts: ['后端 API 代码', '前端组件', '数据库迁移脚本'] }, 31000)
  setStageStatus('coding', 'completed', 32000)

  schedule(32100, () => writeArtifact('coding', '后端API代码.md',
    `# 后端 API 代码实现\n\n## 文件结构\n\`\`\`\nbackend/app/\n├── api/\n│   └── auth.py          # 认证路由\n├── models/\n│   └── user.py          # 用户模型\n├── services/\n│   └── auth_service.py  # 认证服务\n└── middleware/\n    └── jwt.py           # JWT 中间件\n\`\`\`\n\n## 核心端点\n- POST /api/auth/login → 返回 access_token + refresh_token\n- POST /api/auth/register → 创建用户\n- POST /api/auth/refresh → 刷新 token\n\n## 安全措施\n- 密码 bcrypt 哈希\n- JWT 黑名单 (Redis)\n- X-Request-Id 追踪`))

  schedule(32110, () => writeArtifact('coding', '前端组件.md',
    `# 前端组件实现\n\n## 页面\n- /login — 登录页面\n- /register — 注册页面\n\n## 组件\n- LoginForm.tsx — 登录表单 (邮箱 + 密码 + 验证)\n- RegisterForm.tsx — 注册表单\n- AuthGuard.tsx — 路由守卫\n- TokenManager.ts — localStorage token 管理\n\n## 技术细节\n- React Hook Form 处理表单\n- Axios 拦截器自动附加 Authorization header\n- 错误处理和 loading 状态`))

  schedule(32120, () => writeArtifact('coding', '数据库迁移脚本.md',
    `# 数据库迁移脚本\n\n## 表结构\n\`\`\`sql\nCREATE TABLE users (\n  id UUID PRIMARY KEY,\n  email VARCHAR(255) UNIQUE NOT NULL,\n  password_hash VARCHAR(255) NOT NULL,\n  created_at TIMESTAMP DEFAULT NOW()\n);\n\nCREATE TABLE roles (\n  id UUID PRIMARY KEY,\n  name VARCHAR(100) UNIQUE NOT NULL\n);\n\nCREATE TABLE permissions (\n  id UUID PRIMARY KEY,\n  name VARCHAR(100) UNIQUE NOT NULL\n);\n\`\`\`\n\n## 迁移命令\n\`\`\`bash\nalembic upgrade head\n\`\`\``))

  schedule(32130, () => writeLog('info', 'pipeline', '阶段完成: 编码实现'))

  setProgress(0.55, 'review', 32500)

  // ================================================================
  // PHASE 4: Code Review (35s - 45s)
  // ================================================================
  schedule(33000, () => {
    s().addLog({ level: 'info', source: 'pipeline', message: '阶段开始: 代码审查' })
    s().updateAgentStatus('architect', 'working')
    s().updateAgentStatus('tester', 'thinking')
    s().updateAgentStatus('backend', 'idle')
    s().updateAgentStatus('frontend', 'idle')
  })
  setStageStatus('review', 'active', 33000)

  chat(AGENTS.architect, '开始审查后端代码。整体架构清晰，分层合理。有几个小建议：\n1. Service 层可以再加一层 Repository 抽象\n2. 异常处理可以更统一', 34000)

  chat(AGENTS.tester, '我从测试角度审查：代码的可测试性不错，依赖注入做得好。建议给关键路径加边界测试。', 36000)

  event('decision', AGENTS.architect, '代码审查通过，建议增加 Repository 抽象层', '代码质量评分: A-，无阻塞性问题', 'important', 38000)

  chat(AGENTS.architect, '前端代码也看了，组件拆分合理，错误边界处理得当。有一个 CSS 样式重复的问题，可以提取成公共类。', 39000)

  event('action', AGENTS.architect, '审查完成：后端 A- / 前端 B+', '后端建议增加 Repository 层，前端建议提取公共样式', 'normal', 41000)

  log('success', 'architect', '代码审查完成: 整体评分 A-', 42000)

  setStageStatus('review', 'completed', 43000)
  updateStage('review', { artifacts: ['审查报告', '改进建议 3条'] }, 43500)

  schedule(43600, () => writeArtifact('review', '审查报告.md',
    `# 代码审查报告\n\n## 总体评分: A-\n\n## 后端代码审查\n- 架构清晰，分层合理: ✅\n- 建议增加 Repository 抽象层: ⚠️\n- 异常处理可以更统一: ⚠️\n- JWT 中间件实现正确: ✅\n\n## 前端代码审查\n- 组件拆分合理: ✅\n- 错误边界处理得当: ✅\n- CSS 样式有重复，建议提取公共类: ⚠️\n\n## 改进建议\n1. Service 层增加 Repository 抽象\n2. 统一异常处理机制\n3. 前端提取公共 CSS 样式类`))

  schedule(43610, () => writeArtifact('review', '改进建议.md',
    `# 改进建议\n\n1. **Repository 抽象层**: 在 Service 和 ORM 之间增加 Repository 层，提高可测试性\n2. **异常处理统一**: 使用统一的 AppException 类和全局异常处理器\n3. **公共样式提取**: 将重复的 CSS 样式提取为 Tailwind 组件类\n\n## 实施优先级\n- 建议 1: 中 (不影响功能，提升维护性)\n- 建议 2: 高 (影响错误定位效率)\n- 建议 3: 低 (不影响功能)`))

  schedule(43620, () => writeLog('info', 'pipeline', '阶段完成: 代码审查'))

  setProgress(0.7, 'testing', 44000)

  // ================================================================
  // PHASE 5: Testing (45s - 55s)
  // ================================================================
  schedule(44500, () => {
    s().addLog({ level: 'info', source: 'pipeline', message: '阶段开始: 测试验证' })
    s().updateAgentStatus('tester', 'working')
    s().updateAgentStatus('architect', 'idle')
  })
  setStageStatus('testing', 'active', 44500)

  chat(AGENTS.tester, '开始执行测试计划。先跑单元测试，再跑集成测试。', 45500)

  schedule(46000, () => {
    s().addLog({ level: 'info', source: 'tester', message: '运行单元测试: 24/24 通过' })
    s().addLog({ level: 'info', source: 'tester', message: '运行集成测试: 8/8 通过' })
  })
  log('success', 'tester', '单元测试: 24/24 通过 ✓', 47000)
  log('success', 'tester', '集成测试: 8/8 通过 ✓', 47500)

  chat(AGENTS.tester, '所有测试通过！覆盖率：后端 89%，前端 76%。没有发现回归问题。建议前端补几个交互测试。', 48000)

  event('action', AGENTS.tester, '测试全部通过：32 个用例 0 失败', '覆盖率：后端 89%，前端 76%', 'important', 49000)

  // Update task 4 to done
  schedule(50000, () => {
    const now = new Date().toISOString()
    s().setTasks([
      {
        id: 'task-1', title: '数据库表结构设计', description: '', status: 'done', priority: 'high',
        stage: 'testing', assignedAgents: ['architect', 'backend'], createdBy: 'pm',
        statusHistory: [{ from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 45000).toISOString(), by: 'pm' }, { from: 'todo', to: 'in_progress', timestamp: new Date(Date.now() - 42000).toISOString(), by: 'architect' }, { from: 'in_progress', to: 'done', timestamp: now, by: 'architect' }],
        tags: ['database', 'schema'], createdAt: new Date(Date.now() - 45000).toISOString(), updatedAt: now,
      },
      {
        id: 'task-2', title: '实现用户认证 API', description: '', status: 'done', priority: 'high',
        stage: 'testing', assignedAgents: ['backend'], createdBy: 'pm',
        statusHistory: [{ from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 45000).toISOString(), by: 'pm' }, { from: 'todo', to: 'in_progress', timestamp: new Date(Date.now() - 40000).toISOString(), by: 'backend' }, { from: 'in_progress', to: 'review', timestamp: new Date(Date.now() - 30000).toISOString(), by: 'backend' }, { from: 'review', to: 'done', timestamp: now, by: 'architect' }],
        tags: ['api', 'auth', 'jwt'], createdAt: new Date(Date.now() - 45000).toISOString(), updatedAt: now,
      },
      {
        id: 'task-3', title: '前端登录页面开发', description: '', status: 'done', priority: 'medium',
        stage: 'testing', assignedAgents: ['frontend'], createdBy: 'pm',
        statusHistory: [{ from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 45000).toISOString(), by: 'pm' }, { from: 'todo', to: 'in_progress', timestamp: new Date(Date.now() - 35000).toISOString(), by: 'frontend' }, { from: 'in_progress', to: 'done', timestamp: now, by: 'frontend' }],
        tags: ['frontend', 'ui', 'auth'], createdAt: new Date(Date.now() - 45000).toISOString(), updatedAt: now,
      },
      {
        id: 'task-4', title: '编写 API 单元测试', description: '', status: 'done', priority: 'medium',
        stage: 'testing', assignedAgents: ['tester'], createdBy: 'backend',
        statusHistory: [{ from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 40000).toISOString(), by: 'backend' }, { from: 'todo', to: 'in_progress', timestamp: new Date(Date.now() - 20000).toISOString(), by: 'tester' }, { from: 'in_progress', to: 'done', timestamp: now, by: 'tester' }],
        tags: ['testing', 'api'], createdAt: new Date(Date.now() - 45000).toISOString(), updatedAt: now,
      },
      {
        id: 'task-5', title: 'CI/CD Pipeline 配置', description: '', status: 'review', priority: 'low',
        stage: 'testing', assignedAgents: ['devops'], createdBy: 'pm',
        statusHistory: [{ from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 30000).toISOString(), by: 'pm' }, { from: 'todo', to: 'in_progress', timestamp: new Date(Date.now() - 10000).toISOString(), by: 'devops' }, { from: 'in_progress', to: 'review', timestamp: now, by: 'devops' }],
        tags: ['devops', 'ci/cd'], createdAt: new Date(Date.now() - 45000).toISOString(), updatedAt: now,
      },
    ])
  })

  setStageStatus('testing', 'completed', 52000)
  updateStage('testing', { artifacts: ['测试报告', '覆盖率数据'] }, 52500)

  schedule(52600, () => writeArtifact('testing', '测试报告.md',
    `# 测试报告\n\n## 测试结果: 全部通过 ✅\n\n## 单元测试\n- 认证模块: 16/16 通过\n- 用户模块: 8/8 通过\n- 合计: 24/24 通过\n\n## 集成测试\n- 登录流程: 3/3 通过\n- 注册流程: 2/2 通过\n- Token 刷新: 2/2 通过\n- 权限验证: 1/1 通过\n- 合计: 8/8 通过\n\n## 覆盖率\n- 后端: 89%\n- 前端: 76%\n- 整体: 82.5%\n\n## 性能测试\n- API 平均响应: 45ms\n- 并发 1000 用户: 无错误`))

  schedule(52610, () => writeArtifact('testing', '覆盖率数据.md',
    `# 测试覆盖率数据\n\n\`\`\`\nName                        Stmts   Miss  Cover\n----------------------------------------------\napp/api/auth.py                45      2    96%\napp/services/auth_service.py   89      8    91%\napp/models/user.py             23      1    96%\napp/middleware/jwt.py          34      5    85%\n----------------------------------------------\nTOTAL                         191     16    89%\n\`\`\`\n\n## 未覆盖区域\n- auth_service.py: refresh_token 过期处理\n- jwt.py: 边缘情况 token 解析错误`))

  schedule(52620, () => writeLog('info', 'pipeline', '阶段完成: 测试验证'))

  setProgress(0.85, 'delivery', 53000)

  // ================================================================
  // PHASE 6: Delivery (55s - 65s)
  // ================================================================
  schedule(53500, () => {
    s().addLog({ level: 'info', source: 'pipeline', message: '阶段开始: 交付部署' })
    s().updateAgentStatus('devops', 'working')
    s().updateAgentStatus('tester', 'idle')
  })
  setStageStatus('delivery', 'active', 53500)

  chat(AGENTS.devops, '开始配置部署流程。Dockerfile 已编写，GitHub Actions workflow 已配置。', 54500)

  schedule(55000, () => {
    s().addLog({ level: 'info', source: 'devops', message: '构建 Docker 镜像...' })
    s().addLog({ level: 'success', source: 'devops', message: '镜像构建成功: devteam-app:latest' })
  })

  chat(AGENTS.devops, '部署完成！应用已上线。健康检查通过，监控面板已接入。', 56500)

  event('artifact', AGENTS.devops, '部署成功：应用已上线', 'Docker 镜像 + GitHub Actions 自动化部署', 'important', 57000)

  // All tasks done
  schedule(58000, () => {
    const now = new Date().toISOString()
    s().setTasks([
      {
        id: 'task-1', title: '数据库表结构设计', description: '', status: 'done', priority: 'high',
        stage: 'delivery', assignedAgents: ['architect', 'backend'], createdBy: 'pm',
        statusHistory: [{ from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 55000).toISOString(), by: 'pm' }, { from: 'todo', to: 'in_progress', timestamp: new Date(Date.now() - 52000).toISOString(), by: 'architect' }, { from: 'in_progress', to: 'done', timestamp: now, by: 'architect' }],
        tags: ['database'], createdAt: new Date(Date.now() - 55000).toISOString(), updatedAt: now,
      },
      {
        id: 'task-2', title: '实现用户认证 API', description: '', status: 'done', priority: 'high',
        stage: 'delivery', assignedAgents: ['backend'], createdBy: 'pm',
        statusHistory: [{ from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 55000).toISOString(), by: 'pm' }, { from: 'todo', to: 'in_progress', timestamp: new Date(Date.now() - 50000).toISOString(), by: 'backend' }, { from: 'in_progress', to: 'review', timestamp: new Date(Date.now() - 40000).toISOString(), by: 'backend' }, { from: 'review', to: 'done', timestamp: now, by: 'architect' }],
        tags: ['api', 'auth'], createdAt: new Date(Date.now() - 55000).toISOString(), updatedAt: now,
      },
      {
        id: 'task-3', title: '前端登录页面开发', description: '', status: 'done', priority: 'medium',
        stage: 'delivery', assignedAgents: ['frontend'], createdBy: 'pm',
        statusHistory: [{ from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 55000).toISOString(), by: 'pm' }, { from: 'todo', to: 'in_progress', timestamp: new Date(Date.now() - 45000).toISOString(), by: 'frontend' }, { from: 'in_progress', to: 'done', timestamp: now, by: 'frontend' }],
        tags: ['frontend', 'ui'], createdAt: new Date(Date.now() - 55000).toISOString(), updatedAt: now,
      },
      {
        id: 'task-4', title: '编写 API 单元测试', description: '', status: 'done', priority: 'medium',
        stage: 'delivery', assignedAgents: ['tester'], createdBy: 'backend',
        statusHistory: [{ from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 50000).toISOString(), by: 'backend' }, { from: 'todo', to: 'in_progress', timestamp: new Date(Date.now() - 30000).toISOString(), by: 'tester' }, { from: 'in_progress', to: 'done', timestamp: now, by: 'tester' }],
        tags: ['testing'], createdAt: new Date(Date.now() - 55000).toISOString(), updatedAt: now,
      },
      {
        id: 'task-5', title: 'CI/CD Pipeline 配置', description: '', status: 'done', priority: 'low',
        stage: 'delivery', assignedAgents: ['devops'], createdBy: 'pm',
        statusHistory: [{ from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 40000).toISOString(), by: 'pm' }, { from: 'todo', to: 'in_progress', timestamp: new Date(Date.now() - 20000).toISOString(), by: 'devops' }, { from: 'in_progress', to: 'review', timestamp: new Date(Date.now() - 8000).toISOString(), by: 'devops' }, { from: 'review', to: 'done', timestamp: now, by: 'architect' }],
        tags: ['devops', 'ci/cd'], createdAt: new Date(Date.now() - 55000).toISOString(), updatedAt: now,
      },
    ])
  })

  log('success', 'pipeline', '所有任务已完成 ✓', 59000)
  log('success', 'pipeline', '项目交付完成！', 59500)

  updateStage('delivery', { artifacts: ['Docker 镜像', 'CI/CD 配置', '上线应用'] }, 59500)
  setStageStatus('delivery', 'completed', 60000)
  setProgress(1.0, 'delivery', 60500)

  schedule(60600, () => writeArtifact('delivery', 'Docker镜像.md',
    `# Docker 镜像\n\n## Dockerfile\n\`\`\`dockerfile\nFROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY . .\nEXPOSE 8000\nCMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]\n\`\`\`\n\n## 构建\n\`\`\`bash\ndocker build -t devteam-app:latest .\n\`\`\``))

  schedule(60610, () => writeArtifact('delivery', 'CI_CD配置.md',
    `# CI/CD Pipeline 配置\n\n## GitHub Actions\n\`\`\`yaml\nname: Deploy\non:\n  push:\n    branches: [main]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - run: pip install -r requirements.txt\n      - run: pytest\n  deploy:\n    needs: test\n    runs-on: ubuntu-latest\n    steps:\n      - run: docker build -t app .\n      - run: docker push app\n\`\`\`\n\n## 环境\n- 开发: devteam-dev.example.com\n- 生产: devteam.example.com`))

  schedule(60620, () => writeArtifact('delivery', '上线说明.md',
    `# 上线说明\n\n## 应用信息\n- 名称: ${projectName}\n- 版本: 1.0.0\n- 上线时间: ${new Date().toISOString()}\n\n## 健康检查\n- GET /health → {\"status\": \"healthy\"}\n\n## 监控\n- 日志: 已接入\n- 监控面板: 已配置\n- 告警: 已配置`))

  schedule(60630, () => { writeLog('success', 'pipeline', '项目交付完成'); updateWorkspaceStatus(s().pipeline?.id || '', 'completed', 'delivery').catch(() => {}) })

  schedule(61000, () => {
    const p = s().pipeline
    if (p) s().setPipeline({ ...p, status: 'completed' })
    s().setLoading(false)
    s().agents.forEach((a) => s().updateAgentStatus(a.id, 'idle'))

    s().addEvent({
      type: 'status_change',
      agentId: 'system',
      agentName: '系统',
      agentColor: '#8b949e',
      content: `项目「${projectName}」已完成`,
      detail: '全部 6 个阶段、5 个任务均已完成。Agent 团队已就绪，等待下一个项目。',
      importance: 'critical',
    })
  })

  setCostData(62000)

  // ================================================================
  // Cleanup
  // ================================================================
  return () => {
    stopped = true
    timers.forEach(clearTimeout)
  }
}
