import { create } from 'zustand'
import { createWorkspace, type TaskExecutionStatus, type StuckTaskInfo } from './api'

export interface LLMConfig {
  provider: string
  model: string
  temperature: number
  max_tokens?: number
}

export interface Agent {
  id: string
  name: string
  role: string
  status: 'idle' | 'thinking' | 'working' | 'waiting' | 'blocked'
  avatarColor: string
  currentTask?: string
  description?: string
  llm_config?: LLMConfig
}

export interface PipelineStage {
  key: string
  label: string
  status: 'pending' | 'active' | 'completed' | 'blocked'
  assignedAgents: string[]
  artifacts: string[]
  startedAt?: string
  completedAt?: string
}

export interface Pipeline {
  id: string
  name: string
  status: 'idle' | 'running' | 'paused' | 'completed' | 'failed'
  currentStage: string
  progress: number
  stages: PipelineStage[]
  createdAt: string
}

export interface Task {
  id: string
  title: string
  description: string
  status: string
  priority: string
  riskLevel?: string
  stage: string
  assignedAgents: string[]
  createdBy: string
  statusHistory: Array<{ from: string; to: string; timestamp: string; by: string }>
  tags: string[]
  createdAt: string
  updatedAt: string
  approvalRequired?: boolean
  approvedBy?: string | null
  approvedAt?: string | null
}

export interface TimelineEvent {
  id: string
  type: 'decision' | 'action' | 'message' | 'status_change' | 'artifact'
  agentId?: string
  agentName?: string
  agentColor?: string
  content: string
  detail?: string
  timestamp: string
  importance: 'normal' | 'important' | 'critical'
}

export interface ChatMessage {
  id: string
  agentId: string
  agentName: string
  agentColor: string
  content: string
  timestamp: string
}

export interface LogEntry {
  id: string
  level: 'info' | 'success' | 'warn' | 'error' | 'debug'
  source: string
  message: string
  timestamp: string
}

export interface CostData {
  totalCost: number
  totalTokens: number
  promptTokens: number
  completionTokens: number
  callCount: number
  byAgent: Record<string, { cost: number; tokens: number; calls: number }>
  byModel: Record<string, { cost: number; tokens: number; calls: number }>
}

export interface ProjectSummary {
  id: string
  name: string
  description: string
  status: string
  progress: number
  taskCount: number
  agentCount: number
  createdAt: string
}

interface WorkspaceState {
  // Multi-project
  projects: ProjectSummary[]
  activeProjectId: string | null

  // Per-project state
  pipelines: Record<string, Pipeline | null>
  tasksByProject: Record<string, Task[]>
  agentsByProject: Record<string, Agent[]>
  logsByProject: Record<string, LogEntry[]>
  eventsByProject: Record<string, TimelineEvent[]>
  chatMessagesByProject: Record<string, ChatMessage[]>
  costDataByProject: Record<string, CostData | null>
  taskExecutionsByProject: Record<string, Record<string, TaskExecutionStatus>>
  stuckTasksByProject: Record<string, StuckTaskInfo[]>
  workspacePaths: Record<string, string | null>
  interventionsByProject: Record<string, null | 'whisper' | 'broadcast' | 'pause'>
  tasksLoadingByProject: Record<string, boolean>
  stuckPollingByProject: Record<string, boolean>

  // Global state
  isConnected: boolean
  isLoading: boolean
  error: string | null
  globalLlmConfig: LLMConfig
  llmMode: 'mock' | 'real'
  sidePanelOpen: boolean
  sidePanelTab: 'agents' | 'timeline' | 'cost'
  setSidePanelOpen: (open: boolean) => void
  setSidePanelTab: (tab: 'agents' | 'timeline' | 'cost') => void
  terminalExpanded: boolean
  terminalFullscreen: boolean
  setTerminalExpanded: (expanded: boolean) => void
  setTerminalFullscreen: (fs: boolean) => void

  // Actions
  setGlobalLlmConfig: (config: LLMConfig) => void
  setLlmMode: (mode: 'mock' | 'real') => void
  fetchLlmMode: () => Promise<void>
  setConnected: (connected: boolean) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void

  // Project management
  createProject: (id: string, name: string, description: string) => void
  switchProject: (projectId: string) => void
  closeProject: (projectId: string) => void
  updateProjectProgress: (projectId: string, progress: number) => void

  // Per-project actions
  setPipeline: (projectId: string, pipeline: Pipeline) => void
  updatePipelineStage: (projectId: string, stageKey: string, updates: Partial<PipelineStage>) => void
  setTasks: (projectId: string, tasks: Task[]) => void
  updateTask: (projectId: string, taskId: string, updates: Partial<Task>) => void
  setTasksLoading: (projectId: string, loading: boolean) => void
  setAgents: (projectId: string, agents: Agent[]) => void
  updateAgentStatus: (projectId: string, agentId: string, status: Agent['status']) => void
  updateAgent: (projectId: string, agentId: string, updates: Partial<Agent>) => void
  replaceAgent: (projectId: string, oldAgentId: string, newAgent: Agent) => void
  addLog: (projectId: string, log: Omit<LogEntry, 'id' | 'timestamp'>) => void
  addLogs: (projectId: string, logs: Omit<LogEntry, 'id' | 'timestamp'>[]) => void
  clearLogs: (projectId: string) => void
  addEvent: (projectId: string, event: Omit<TimelineEvent, 'id' | 'timestamp'>) => void
  addEvents: (projectId: string, events: Omit<TimelineEvent, 'id' | 'timestamp'>[]) => void
  addChatMessage: (projectId: string, msg: Omit<ChatMessage, 'id' | 'timestamp'>) => void
  clearChatMessages: (projectId: string) => void
  setInterventionMode: (projectId: string, mode: null | 'whisper' | 'broadcast' | 'pause') => void
  setCostData: (projectId: string, data: CostData | null) => void
  setWorkspacePath: (projectId: string, path: string | null) => void
  setTaskExecution: (projectId: string, taskId: string, status: TaskExecutionStatus) => void
  setStuckTasks: (projectId: string, tasks: StuckTaskInfo[]) => void
  setStuckPolling: (projectId: string, polling: boolean) => void

  // Legacy compatibility
  startProject: (name: string, description: string, customAgents?: Agent[], teamConfig?: { strategy: string; coordinatorId?: string }, template?: { id: string; name: string; stages: Array<{ key: string; label: string; expected_artifact: string; parallel_group: string | null }> } | null) => void
  restoreProjectFromWorkspace: (workspace: import('./api').WorkspaceInfo) => void
  resetProject: () => void
  resumeProject: (projectId: string, pipelineId: string) => Promise<void>
  teamConfigs: Record<string, { strategy: string; coordinatorId?: string } | null>

  // Real backend integration
  startRealPipeline: (projectId: string, name: string, description: string, agentIds: string[], teamConfig?: { strategy: string; coordinatorId?: string }) => Promise<void>
  startPolling: (projectId: string, pipelineId: string) => void
  stopPolling: (projectId: string) => void

  // Team suggestion (Step 2+3 flow)
  fetchTeamSuggestion: (taskDescription: string) => Promise<import('./api').TeamSuggestionResponse | null>
}

// Per-project counters for ID generation
const counters: Record<string, { log: number; event: number; chat: number }> = {}

function getCounters(projectId: string) {
  if (!counters[projectId]) {
    counters[projectId] = { log: 0, event: 0, chat: 0 }
  }
  return counters[projectId]
}

const pollIntervals: Record<string, ReturnType<typeof setInterval>> = {}

export const useStore = create<WorkspaceState>((set) => ({
  projects: [],
  activeProjectId: null,
  pipelines: {},
  tasksByProject: {},
  agentsByProject: {},
  logsByProject: {},
  eventsByProject: {},
  chatMessagesByProject: {},
  costDataByProject: {},
  taskExecutionsByProject: {},
  stuckTasksByProject: {},
  workspacePaths: {},
  interventionsByProject: {},
  tasksLoadingByProject: {},
  stuckPollingByProject: {},
  teamConfigs: {},

  isConnected: false,
  isLoading: false,
  error: null,
  globalLlmConfig: {
    provider: 'deepseek',
    model: 'deepseek-v4-flash',
    temperature: 0.7,
    max_tokens: undefined,
  },
  llmMode: 'mock' as 'mock' | 'real',
  sidePanelOpen: true,
  sidePanelTab: 'agents',
  terminalExpanded: false,
  terminalFullscreen: false,

  strategyRecommendation: null as any, // kept for backward compat, use teamSuggestion instead

  // Team suggestion (async, not stored in state — components manage it locally)
  fetchTeamSuggestion: async (taskDescription) => {
    try {
      const { suggestTeam } = await import('./api')
      return await suggestTeam(taskDescription)
    } catch (err) {
      console.warn('团队建议失败:', err)
      return null
    }
  },

  setSidePanelOpen: (open) => set({ sidePanelOpen: open }),
  setSidePanelTab: (tab) => set({ sidePanelTab: tab }),
  setTerminalExpanded: (expanded) => set({ terminalExpanded: expanded }),
  setTerminalFullscreen: (fs) => set({ terminalFullscreen: fs }),

  setGlobalLlmConfig: (config) => set({ globalLlmConfig: config }),
  setLlmMode: (mode) => set({ llmMode: mode }),
  fetchLlmMode: async () => {
    try {
      const { getSettings } = await import('./api')
      const settings = await getSettings()
      if (settings.llm_mode) {
        set({ llmMode: settings.llm_mode as 'mock' | 'real' })
      }
    } catch {
      // Backend not available, stay in mock mode
    }
  },
  setConnected: (connected) => set({ isConnected: connected }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),

  // --- Project management ---

  createProject: (id, name, description) =>
    set((state) => ({
      projects: [
        ...state.projects,
        {
          id,
          name,
          description,
          status: 'planning',
          progress: 0,
          taskCount: 0,
          agentCount: 0,
          createdAt: new Date().toISOString(),
        },
      ],
      activeProjectId: id,
      tasksByProject: { ...state.tasksByProject, [id]: [] },
      agentsByProject: { ...state.agentsByProject, [id]: [] },
      logsByProject: { ...state.logsByProject, [id]: [] },
      eventsByProject: { ...state.eventsByProject, [id]: [] },
      chatMessagesByProject: { ...state.chatMessagesByProject, [id]: [] },
      costDataByProject: { ...state.costDataByProject, [id]: null },
      taskExecutionsByProject: { ...state.taskExecutionsByProject, [id]: {} },
      stuckTasksByProject: { ...state.stuckTasksByProject, [id]: [] },
      workspacePaths: { ...state.workspacePaths, [id]: null },
      interventionsByProject: { ...state.interventionsByProject, [id]: null },
      tasksLoadingByProject: { ...state.tasksLoadingByProject, [id]: false },
      stuckPollingByProject: { ...state.stuckPollingByProject, [id]: false },
      teamConfigs: { ...state.teamConfigs, [id]: null },
    })),

  switchProject: (projectId) => set({ activeProjectId: projectId }),

  closeProject: (projectId) => {
    const state = useStore.getState()
    // 停止轮询
    state.stopPolling(projectId)

    // 真实模式：通知后端关闭流水线
    if (state.llmMode === 'real') {
      const pipeline = state.pipelines[projectId]
      if (pipeline?.id && (pipeline.status === 'running' || pipeline.status === 'paused')) {
        import('./api').then(({ closePipeline }) => {
          closePipeline(pipeline.id).catch(err =>
            console.warn('关闭流水线失败:', err)
          )
        })
      }
    }

    // 清除客户端状态
    set((state) => {
      const newProjects = state.projects.filter((p) => p.id !== projectId)
      const newActiveId = state.activeProjectId === projectId
        ? (newProjects.length > 0 ? newProjects[0].id : null)
        : state.activeProjectId

      const { [projectId]: _, ...newPipelines } = state.pipelines
      const { [projectId]: __, ...newTasks } = state.tasksByProject
      const { [projectId]: ___, ...newAgents } = state.agentsByProject
      const { [projectId]: ____, ...newLogs } = state.logsByProject
      const { [projectId]: _____, ...newEvents } = state.eventsByProject
      const { [projectId]: ______, ...newChat } = state.chatMessagesByProject
      const { [projectId]: _______, ...newCost } = state.costDataByProject
      const { [projectId]: ________, ...newExec } = state.taskExecutionsByProject
      const { [projectId]: _________, ...newStuck } = state.stuckTasksByProject
      const { [projectId]: __________, ...newPaths } = state.workspacePaths
      const { [projectId]: ___________, ...newInterventions } = state.interventionsByProject
      const { [projectId]: ____________, ...newTasksLoading } = state.tasksLoadingByProject
      const { [projectId]: _____________, ...newStuckPolling } = state.stuckPollingByProject
      const { [projectId]: ______________, ...newTeamConfigs } = state.teamConfigs

      delete counters[projectId]

      return {
        projects: newProjects,
        activeProjectId: newActiveId,
        pipelines: newPipelines,
        tasksByProject: newTasks,
        agentsByProject: newAgents,
        logsByProject: newLogs,
        eventsByProject: newEvents,
        chatMessagesByProject: newChat,
        costDataByProject: newCost,
        taskExecutionsByProject: newExec,
        stuckTasksByProject: newStuck,
        workspacePaths: newPaths,
        interventionsByProject: newInterventions,
        tasksLoadingByProject: newTasksLoading,
        stuckPollingByProject: newStuckPolling,
        teamConfigs: newTeamConfigs,
      }
    })
  },

  updateProjectProgress: (projectId, progress) =>
    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === projectId ? { ...p, progress, status: progress >= 1 ? 'completed' : p.status } : p,
      ),
    })),

  // --- Per-project actions ---

  setPipeline: (projectId, pipeline) =>
    set((state) => ({ pipelines: { ...state.pipelines, [projectId]: pipeline } })),

  updatePipelineStage: (projectId, stageKey, updates) =>
    set((state) => {
      const pipeline = state.pipelines[projectId]
      if (!pipeline) return state
      return {
        pipelines: {
          ...state.pipelines,
          [projectId]: {
            ...pipeline,
            stages: pipeline.stages.map((s) =>
              s.key === stageKey ? { ...s, ...updates } : s,
            ),
          },
        },
      }
    }),

  setTasks: (projectId, tasks) =>
    set((state) => ({
      tasksByProject: { ...state.tasksByProject, [projectId]: tasks },
      projects: state.projects.map((p) =>
        p.id === projectId ? { ...p, taskCount: tasks.length } : p,
      ),
    })),

  updateTask: (projectId, taskId, updates) =>
    set((state) => {
      const tasks = state.tasksByProject[projectId] || []
      return {
        tasksByProject: {
          ...state.tasksByProject,
          [projectId]: tasks.map((t) =>
            t.id === taskId ? { ...t, ...updates, updatedAt: new Date().toISOString() } : t,
          ),
        },
      }
    }),

  setTasksLoading: (projectId, loading) =>
    set((state) => ({
      tasksLoadingByProject: { ...state.tasksLoadingByProject, [projectId]: loading },
    })),

  setAgents: (projectId, agents) =>
    set((state) => ({
      agentsByProject: { ...state.agentsByProject, [projectId]: agents },
      projects: state.projects.map((p) =>
        p.id === projectId ? { ...p, agentCount: agents.length } : p,
      ),
    })),

  updateAgentStatus: (projectId, agentId, status) =>
    set((state) => {
      const agents = state.agentsByProject[projectId] || []
      return {
        agentsByProject: {
          ...state.agentsByProject,
          [projectId]: agents.map((a) => (a.id === agentId ? { ...a, status } : a)),
        },
      }
    }),

  updateAgent: (projectId, agentId, updates) =>
    set((state) => {
      const agents = state.agentsByProject[projectId] || []
      return {
        agentsByProject: {
          ...state.agentsByProject,
          [projectId]: agents.map((a) => (a.id === agentId ? { ...a, ...updates } : a)),
        },
      }
    }),

  replaceAgent: (projectId, oldAgentId, newAgent) =>
    set((state) => {
      const agents = state.agentsByProject[projectId] || []
      const idx = agents.findIndex((a) => a.id === oldAgentId)
      if (idx === -1) return state
      const updated = [...agents]
      updated[idx] = { ...newAgent, status: 'idle' as const }
      return {
        agentsByProject: { ...state.agentsByProject, [projectId]: updated },
      }
    }),

  addLog: (projectId, log) =>
    set((state) => {
      const c = getCounters(projectId)
      const logs = state.logsByProject[projectId] || []
      return {
        logsByProject: {
          ...state.logsByProject,
          [projectId]: [
            ...logs.slice(-500),
            { ...log, id: `log-${++c.log}`, timestamp: new Date().toISOString() },
          ],
        },
      }
    }),

  addLogs: (projectId, logs) =>
    set((state) => {
      const c = getCounters(projectId)
      const existing = state.logsByProject[projectId] || []
      const newLogs = logs.map((l) => ({
        ...l,
        id: `log-${++c.log}`,
        timestamp: new Date().toISOString(),
      }))
      return {
        logsByProject: {
          ...state.logsByProject,
          [projectId]: [...existing, ...newLogs].slice(-500),
        },
      }
    }),

  clearLogs: (projectId) =>
    set((state) => ({ logsByProject: { ...state.logsByProject, [projectId]: [] } })),

  addEvent: (projectId, event) =>
    set((state) => {
      const c = getCounters(projectId)
      const events = state.eventsByProject[projectId] || []
      return {
        eventsByProject: {
          ...state.eventsByProject,
          [projectId]: [
            ...events,
            { ...event, id: `evt-${++c.event}`, timestamp: new Date().toISOString() },
          ].slice(-200),
        },
      }
    }),

  addEvents: (projectId, events) =>
    set((state) => {
      const c = getCounters(projectId)
      const existing = state.eventsByProject[projectId] || []
      const newEvents = events.map((e) => ({
        ...e,
        id: `evt-${++c.event}`,
        timestamp: new Date().toISOString(),
      }))
      return {
        eventsByProject: {
          ...state.eventsByProject,
          [projectId]: [...existing, ...newEvents].slice(-200),
        },
      }
    }),

  addChatMessage: (projectId, msg) =>
    set((state) => {
      const c = getCounters(projectId)
      const chat = state.chatMessagesByProject[projectId] || []
      return {
        chatMessagesByProject: {
          ...state.chatMessagesByProject,
          [projectId]: [
            ...chat,
            { ...msg, id: `chat-${++c.chat}`, timestamp: new Date().toISOString() },
          ].slice(-500),
        },
      }
    }),

  clearChatMessages: (projectId) =>
    set((state) => ({
      chatMessagesByProject: { ...state.chatMessagesByProject, [projectId]: [] },
    })),

  setInterventionMode: (projectId, mode) =>
    set((state) => ({
      interventionsByProject: { ...state.interventionsByProject, [projectId]: mode },
    })),

  setCostData: (projectId, data) =>
    set((state) => ({
      costDataByProject: { ...state.costDataByProject, [projectId]: data },
    })),

  setWorkspacePath: (projectId, path) =>
    set((state) => ({
      workspacePaths: { ...state.workspacePaths, [projectId]: path },
    })),

  setTaskExecution: (projectId, taskId, status) =>
    set((state) => {
      const exec = state.taskExecutionsByProject[projectId] || {}
      return {
        taskExecutionsByProject: {
          ...state.taskExecutionsByProject,
          [projectId]: { ...exec, [taskId]: status },
        },
      }
    }),

  setStuckTasks: (projectId, tasks) =>
    set((state) => ({
      stuckTasksByProject: { ...state.stuckTasksByProject, [projectId]: tasks },
    })),

  setStuckPolling: (projectId, polling) =>
    set((state) => ({
      stuckPollingByProject: { ...state.stuckPollingByProject, [projectId]: polling },
    })),

  // --- Legacy compatibility (wraps multi-project API) ---

  startProject: (name, _description, customAgents, teamConfig, template) => {
    const now = new Date().toISOString()
    const projectId = `project-${Date.now()}`

    const projectAgents = customAgents && customAgents.length > 0 ? customAgents : [];
    const allGeneric = projectAgents.length > 0 && projectAgents.every(a => a.role === '团队成员');


    const stageAgentMap: Record<string, string[]> = {
      requirement_analysis: [],
      task_breakdown: [],
      coding: [],
      review: [],
      testing: [],
      delivery: [],
    }
    if (allGeneric) {
      // All agents are generic — assign everyone to all stages, roles determined at runtime
      for (const agent of projectAgents) {
        for (const key of Object.keys(stageAgentMap)) {
          stageAgentMap[key].push(agent.id);
        }
      }
    } else {
      // Legacy keyword-based role→stage matching
      for (const agent of projectAgents) {
        const role = agent.role
      if (role.includes('需求') || role.includes('产品')) {
        stageAgentMap.requirement_analysis.push(agent.id)
        stageAgentMap.task_breakdown.push(agent.id)
      }
      if (role.includes('架构') || role.includes('设计')) {
        stageAgentMap.requirement_analysis.push(agent.id)
        stageAgentMap.task_breakdown.push(agent.id)
        stageAgentMap.review.push(agent.id)
      }
      if (role.includes('后端')) {
        stageAgentMap.coding.push(agent.id)
      }
      if (role.includes('前端')) {
        stageAgentMap.coding.push(agent.id)
      }
      if (role.includes('测试')) {
        stageAgentMap.review.push(agent.id)
        stageAgentMap.testing.push(agent.id)
      }
      if (role.includes('运维') || role.includes('部署') || role.includes('DevOps')) {
        stageAgentMap.delivery.push(agent.id)
      }
      if (role.includes('评审')) {
        stageAgentMap.review.push(agent.id)
      }
      if (role.includes('文档')) {
        stageAgentMap.task_breakdown.push(agent.id)
      }
    }
    }

    for (const key of Object.keys(stageAgentMap)) {
      stageAgentMap[key] = [...new Set(stageAgentMap[key])]
      if (stageAgentMap[key].length === 0) {
        stageAgentMap[key] = [projectAgents[0]?.id || 'pm']
      }
    }

    // Build pipeline stages from template or use default 6-stage pipeline
    let pipelineStages: PipelineStage[]
    if (template && template.stages && template.stages.length > 0) {
      // Use template stages — assign all agents to all stages for generic teams
      pipelineStages = template.stages.map((s, i) => ({
        key: s.key,
        label: s.label,
        status: (i === 0 ? 'active' : 'pending') as PipelineStage['status'],
        assignedAgents: allGeneric
          ? projectAgents.map(a => a.id)
          : (stageAgentMap[s.key] || [projectAgents[0]?.id || 'pm']),
        artifacts: s.expected_artifact ? [s.expected_artifact] : [],
      }))
    } else {
      // Fallback: legacy 6-stage pipeline
      pipelineStages = [
        { key: 'requirement_analysis', label: '需求分析', status: 'pending', assignedAgents: stageAgentMap.requirement_analysis, artifacts: [] },
        { key: 'task_breakdown', label: '任务拆解', status: 'pending', assignedAgents: stageAgentMap.task_breakdown, artifacts: [] },
        { key: 'coding', label: '编码实现', status: 'pending', assignedAgents: stageAgentMap.coding, artifacts: [] },
        { key: 'review', label: '代码审查', status: 'pending', assignedAgents: stageAgentMap.review, artifacts: [] },
        { key: 'testing', label: '测试验证', status: 'pending', assignedAgents: stageAgentMap.testing, artifacts: [] },
        { key: 'delivery', label: '交付部署', status: 'pending', assignedAgents: stageAgentMap.delivery, artifacts: [] },
      ]
    }

    const currentStage = pipelineStages[0]?.key || 'requirement_analysis'

    const pipeline: Pipeline = {
      id: `pipeline-${Date.now()}`,
      name,
      status: 'running',
      currentStage,
      progress: 0,
      stages: pipelineStages,
      createdAt: now,
    }

    const project: ProjectSummary = {
      id: projectId,
      name,
      description: _description,
      status: 'running',
      progress: 0,
      taskCount: 0,
      agentCount: projectAgents.length,
      createdAt: now,
    }

    set((state) => ({
      projects: [...state.projects, project],
      activeProjectId: projectId,
      pipelines: { ...state.pipelines, [projectId]: pipeline },
      agentsByProject: { ...state.agentsByProject, [projectId]: projectAgents },
      tasksByProject: { ...state.tasksByProject, [projectId]: [] },
      logsByProject: { ...state.logsByProject, [projectId]: [] },
      eventsByProject: { ...state.eventsByProject, [projectId]: [] },
      chatMessagesByProject: { ...state.chatMessagesByProject, [projectId]: [] },
      costDataByProject: { ...state.costDataByProject, [projectId]: null },
      taskExecutionsByProject: { ...state.taskExecutionsByProject, [projectId]: {} },
      stuckTasksByProject: { ...state.stuckTasksByProject, [projectId]: [] },
      workspacePaths: { ...state.workspacePaths, [projectId]: null },
      interventionsByProject: { ...state.interventionsByProject, [projectId]: null },
      tasksLoadingByProject: { ...state.tasksLoadingByProject, [projectId]: false },
      stuckPollingByProject: { ...state.stuckPollingByProject, [projectId]: false },
      teamConfigs: { ...state.teamConfigs, [projectId]: teamConfig || null },
      isConnected: true,
      error: null,
    }))

    // Fire-and-forget: create physical workspace on backend
    // 仅在 mock 模式下创建 workspace（real 模式由 startRealPipeline 用正确 ID 创建）
    if (useStore.getState().llmMode !== 'real') {
      const pid = projectId
      createWorkspace(
        pid,
        name,
        _description,
        projectAgents.map((a) => ({ id: a.id, name: a.name, role: a.role, llm_config: a.llm_config })),
        pipeline.stages.map((s) => ({ key: s.key, label: s.label, assignedAgents: s.assignedAgents })),
        teamConfig,
        template || undefined,
      )
        .then((result) => set((state) => ({
          workspacePaths: { ...state.workspacePaths, [pid]: result.workspace_path },
        })))
        .catch((err) => console.warn('创建物理工作区失败 (后端未启动?):', err.message))
    }
  },

  restoreProjectFromWorkspace: (workspace) => {
    const now = new Date().toISOString()
    const projectId = workspace.id

    // Convert workspace agents to store Agent[]
    const agents: Agent[] = (workspace.agents || []).map((a: any) => ({
      id: a.id,
      name: a.name || a.id,
      role: a.role || a.type || '团队成员',
      status: 'idle' as const,
      avatarColor: a.avatar_color || '#58a6ff',
      description: a.description || '',
      llm_config: a.llm_config,
    }))

    // Determine pipeline status from workspace status
    const wsStatus = workspace.status || 'running'
    const pipelineStatus: Pipeline['status'] =
      wsStatus === 'completed' ? 'completed' :
      wsStatus === 'paused' ? 'paused' :
      wsStatus === 'failed' ? 'failed' : 'idle'

    const wsCurrentStage = (workspace as any).current_stage

    // Build PipelineStage[] from workspace stages
    const pipelineStages: PipelineStage[] = (workspace.stages || []).map((s: any, i: number) => ({
      key: s.key,
      label: s.label || s.key,
      status: pipelineStatus === 'completed'
        ? 'completed' as const
        : (s.key === wsCurrentStage
          ? 'active' as const
          : (i === 0 && !wsCurrentStage ? 'active' as const : 'pending' as const)),
      assignedAgents: s.assignedAgents || agents.map(a => a.id),
      artifacts: [],
    }))

    const currentStage = wsCurrentStage || pipelineStages[0]?.key || 'requirement_analysis'

    const pipeline: Pipeline = {
      id: `pipeline-${projectId}`,
      name: workspace.name,
      status: pipelineStatus,
      currentStage,
      progress: pipelineStatus === 'completed' ? 1.0 : 0,
      stages: pipelineStages,
      createdAt: workspace.created_at || now,
    }

    const project: ProjectSummary = {
      id: projectId,
      name: workspace.name,
      description: workspace.description || '',
      status: pipelineStatus,
      progress: pipelineStatus === 'completed' ? 1.0 : 0,
      taskCount: 0,
      agentCount: agents.length,
      createdAt: workspace.created_at || now,
    }

    const teamConfig = (workspace as any).team_config || null

    set((state) => ({
      projects: [...state.projects, project],
      activeProjectId: projectId,
      pipelines: { ...state.pipelines, [projectId]: pipeline },
      agentsByProject: { ...state.agentsByProject, [projectId]: agents },
      tasksByProject: { ...state.tasksByProject, [projectId]: [] },
      logsByProject: { ...state.logsByProject, [projectId]: [] },
      eventsByProject: { ...state.eventsByProject, [projectId]: [] },
      chatMessagesByProject: { ...state.chatMessagesByProject, [projectId]: [] },
      costDataByProject: { ...state.costDataByProject, [projectId]: null },
      taskExecutionsByProject: { ...state.taskExecutionsByProject, [projectId]: {} },
      stuckTasksByProject: { ...state.stuckTasksByProject, [projectId]: [] },
      workspacePaths: { ...state.workspacePaths, [projectId]: workspace.workspace_path || null },
      interventionsByProject: { ...state.interventionsByProject, [projectId]: null },
      tasksLoadingByProject: { ...state.tasksLoadingByProject, [projectId]: false },
      stuckPollingByProject: { ...state.stuckPollingByProject, [projectId]: false },
      teamConfigs: { ...state.teamConfigs, [projectId]: teamConfig },
      isConnected: true,
      error: null,
    }))
  },

  startRealPipeline: async (projectId, name, description, agentIds, teamConfig) => {
    const { createProject, createPipeline, startPipeline, createWorkspace } = await import('./api')

    // 1. Create project on backend (description IS the user's requirement text)
    const project = await createProject(name, description, description)

    // 2. Create workspace with the REAL backend project ID (not the frontend-generated one)
    const s = useStore.getState()
    const oldAgents = s.agentsByProject[projectId] || []
    const oldPipeline = s.pipelines[projectId]
    createWorkspace(
      project.id,
      name,
      description,
      oldAgents.map((a) => ({ id: a.id, name: a.name, role: a.role, llm_config: a.llm_config })),
      (oldPipeline?.stages || []).map((s) => ({ key: s.key, label: s.label, assignedAgents: s.assignedAgents })),
      teamConfig,
    ).then((result) => set((state) => ({
      workspacePaths: { ...state.workspacePaths, [project.id]: result.workspace_path },
    }))).catch((err) => console.warn('创建物理工作区失败:', err.message))

    // 3. Create pipeline on backend (with team_config for strategy-aware assignment)
    const pipeline = await createPipeline(project.id, name, agentIds, teamConfig)

    // 4. Start pipeline execution
    await startPipeline(pipeline.id)

    // 5. Update in-memory project/pipeline IDs to match backend
    const oldProjectId = projectId
    const realProjectId = project.id
    const realPipelineId = pipeline.id

    // Migrate all per-project state from frontend-generated ID to backend ID
    set((s) => {
      const migrate = <T extends Record<string, unknown>>(obj: T, oldId: string, newId: string): T => {
        if (oldId === newId) return obj
        const next = { ...obj } as Record<string, unknown>
        next[newId] = next[oldId]
        delete next[oldId]
        return next as T
      }

      return {
        projects: s.projects.map((p) => p.id === oldProjectId ? { ...p, id: realProjectId } : p),
        activeProjectId: realProjectId,
        pipelines: migrate(s.pipelines, oldProjectId, realProjectId),
        agentsByProject: migrate(s.agentsByProject, oldProjectId, realProjectId),
        tasksByProject: migrate(s.tasksByProject, oldProjectId, realProjectId),
        logsByProject: migrate(s.logsByProject, oldProjectId, realProjectId),
        eventsByProject: migrate(s.eventsByProject, oldProjectId, realProjectId),
        chatMessagesByProject: migrate(s.chatMessagesByProject, oldProjectId, realProjectId),
        costDataByProject: migrate(s.costDataByProject, oldProjectId, realProjectId),
        taskExecutionsByProject: migrate(s.taskExecutionsByProject, oldProjectId, realProjectId),
        stuckTasksByProject: migrate(s.stuckTasksByProject, oldProjectId, realProjectId),
        workspacePaths: migrate(s.workspacePaths, oldProjectId, realProjectId),
        interventionsByProject: migrate(s.interventionsByProject, oldProjectId, realProjectId),
        tasksLoadingByProject: migrate(s.tasksLoadingByProject, oldProjectId, realProjectId),
        stuckPollingByProject: migrate(s.stuckPollingByProject, oldProjectId, realProjectId),
        teamConfigs: migrate(s.teamConfigs, oldProjectId, realProjectId),
      }
    })

    // 6. Start polling for real data
    useStore.getState().startPolling(realProjectId, realPipelineId)
  },

  // Deprecated: strategy recommendation is now part of team suggestion (Step 3)

  startPolling: (projectId, pipelineId) => {
    // Clear any existing poll for this project
    if (pollIntervals[projectId]) {
      clearInterval(pollIntervals[projectId])
    }

    let lastLogCount = 0

    const poll = async () => {
      try {
        const { getPipeline, listTasks } = await import('./api')

        // Fetch pipeline data (includes logs)
        const pipelineData = await getPipeline(pipelineId)
        if (!pipelineData) return

        // Update pipeline status
        const backendStatus = pipelineData.status as string
        const frontendStatus: Pipeline['status'] =
          backendStatus === 'running' ? 'running' :
          backendStatus === 'completed' ? 'completed' :
          backendStatus === 'failed' ? 'failed' :
          backendStatus === 'paused' ? 'paused' : 'idle'

        const backendStage = pipelineData.current_stage as string || 'requirement_analysis'

        set((s) => ({
          pipelines: {
            ...s.pipelines,
            [projectId]: {
              ...(s.pipelines[projectId] || {}),
              id: pipelineId,
              status: frontendStatus,
              currentStage: backendStage,
              progress: (pipelineData.progress as number) || s.pipelines[projectId]?.progress || 0,
              stages: (s.pipelines[projectId]?.stages || []).map((stage) => ({
                ...stage,
                status: (backendStage === stage.key ? 'active' :
                  backendStatus === 'completed' ? 'completed' : stage.status) as PipelineStage['status'],
              })),
              name: (pipelineData.name as string) || s.pipelines[projectId]?.name || '',
              createdAt: (pipelineData.created_at as string) || s.pipelines[projectId]?.createdAt || '',
            } as Pipeline,
          },
        }))

        // Convert pipeline logs to terminal logs and timeline events
        const logs = (pipelineData.logs as Array<{ stage: string; message: string; level: string; timestamp: string }>) || []
        if (logs.length > lastLogCount) {
          const newLogs = logs.slice(lastLogCount)
          const s = useStore.getState()

          for (const log of newLogs) {
            const level = log.level || 'info'
            const mappedLevel = level === 'error' ? 'error' : level === 'warning' ? 'warn' :
              level === 'info' ? 'info' : level === 'success' ? 'success' : 'debug'

            s.addLog(projectId, {
              level: mappedLevel as LogEntry['level'],
              source: log.stage || 'pipeline',
              message: log.message,
            })

            // Create timeline events for stage transitions
            if (log.message.includes('Starting') || log.message.includes('complete') || log.message.includes('completed')) {
              s.addEvent(projectId, {
                type: log.message.includes('Starting') ? 'decision' : 'artifact',
                agentId: 'pipeline',
                agentName: 'Pipeline',
                content: log.message,
                importance: 'normal',
              })
            }

            // Create chat messages for agent actions
            if (log.stage && log.message && log.stage !== 'init') {
              s.addChatMessage(projectId, {
                agentId: 'pipeline',
                agentName: 'Pipeline',
                agentColor: '#58a6ff',
                content: `[${log.stage}] ${log.message}`,
              })
            }
          }

          lastLogCount = logs.length
        }

        // Update project status
        if (backendStatus === 'completed' || backendStatus === 'failed') {
          set((s) => ({
            projects: s.projects.map((p) =>
              p.id === projectId ? { ...p, status: backendStatus, progress: backendStatus === 'completed' ? 1.0 : p.progress } : p
            ),
          }))
        }

        // Fetch task data
        try {
          const tasks = await listTasks(projectId)
          if (Array.isArray(tasks) && tasks.length > 0) {
            const storeTasks: Task[] = tasks.map((t: any) => ({
              id: t.id || '',
              title: t.title || '',
              description: t.description || '',
              status: t.status || 'backlog',
              priority: t.priority || 'medium',
              riskLevel: t.risk_level || 'low',
              stage: t.phase || 'execution',
              assignedAgents: Array.isArray(t.assigned_agents) ? t.assigned_agents : [],
              createdBy: t.created_by || 'system',
              tags: Array.isArray(t.tags) ? t.tags : [],
              statusHistory: Array.isArray(t.history) ? t.history.map((h: any) => ({
                from: h.from || '',
                to: h.to || '',
                timestamp: h.timestamp || h.changed_at || '',
                by: h.by || h.changed_by || 'system',
              })) : [],
              createdAt: t.created_at || new Date().toISOString(),
              updatedAt: t.updated_at || new Date().toISOString(),
              approvalRequired: t.approval_required || false,
              approvedBy: t.approved_by || null,
              approvedAt: t.approved_at || null,
            }))
            // Always update tasks to reflect status changes
            const currentTasks = useStore.getState().tasksByProject[projectId] || []
            const currentStatuses = currentTasks.map((t: Task) => `${t.id}:${t.status}`).sort().join(',')
            const newStatuses = storeTasks.map((t) => `${t.id}:${t.status}`).sort().join(',')
            if (newStatuses !== currentStatuses || storeTasks.length !== currentTasks.length) {
              set((s) => ({
                tasksByProject: { ...s.tasksByProject, [projectId]: storeTasks },
                projects: s.projects.map((p) =>
                  p.id === projectId ? { ...p, taskCount: storeTasks.length } : p
                ),
              }))
            }
          }
        } catch {
          // Task fetch can fail silently
        }

        // Derive agent statuses from task assignments
        try {
          const currentTasks = useStore.getState().tasksByProject[projectId] || []
          const currentAgents = useStore.getState().agentsByProject[projectId] || []
          if (currentTasks.length > 0 && currentAgents.length > 0) {
            const agentStatuses: Record<string, Agent['status']> = {}
            for (const agent of currentAgents) {
              const agentTasks = currentTasks.filter(t => t.assignedAgents.includes(agent.id))
              if (agentTasks.some(t => t.status === 'in_progress')) {
                agentStatuses[agent.id] = 'working'
              } else if (agentTasks.some(t => t.status === 'blocked')) {
                agentStatuses[agent.id] = 'blocked'
              } else if (agentTasks.some(t => t.status === 'review')) {
                agentStatuses[agent.id] = 'thinking'
              } else if (agentTasks.some(t => t.status === 'todo')) {
                agentStatuses[agent.id] = 'waiting'
              } else {
                agentStatuses[agent.id] = 'idle'
              }
            }
            // Only update if anything changed
            const changed = Object.entries(agentStatuses).some(
              ([id, status]) => currentAgents.find(a => a.id === id)?.status !== status
            )
            if (changed) {
              set((s) => ({
                agentsByProject: {
                  ...s.agentsByProject,
                  [projectId]: currentAgents.map(a => ({
                    ...a,
                    status: agentStatuses[a.id] || a.status,
                  })),
                },
              }))
            }
          }
        } catch {
          // Agent status derivation failure is non-critical
        }

        // If pipeline completed or failed, stop polling
        if (backendStatus === 'completed' || backendStatus === 'failed') {
          const interval = pollIntervals[projectId]
          if (interval) {
            clearInterval(interval)
            delete pollIntervals[projectId]
          }
        }
      } catch {
        // Silently handle polling errors (backend might be busy)
      }
    }

    // Initial poll immediately
    poll()

    // Then poll every 3 seconds
    pollIntervals[projectId] = setInterval(poll, 3000)
  },

  stopPolling: (projectId) => {
    const interval = pollIntervals[projectId]
    if (interval) {
      clearInterval(interval)
      delete pollIntervals[projectId]
    }
  },

  resetProject: () => {
    const state = useStore.getState()
    if (state.activeProjectId) {
      state.closeProject(state.activeProjectId)
    }
  },

  resumeProject: async (projectId: string, pipelineId: string) => {
    const state = useStore.getState()
    if (state.llmMode === 'real') {
      try {
        const { resumeFromClose } = await import('./api')
        await resumeFromClose(pipelineId)
        state.startPolling(projectId, pipelineId)
      } catch (err) {
        console.error('恢复流水线失败:', err)
      }
    }
  },
}))
