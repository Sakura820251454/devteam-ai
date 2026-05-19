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
  stage: string
  assignedAgents: string[]
  createdBy: string
  statusHistory: Array<{ from: string; to: string; timestamp: string; by: string }>
  tags: string[]
  createdAt: string
  updatedAt: string
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
  setTasksLoading: (projectId: string, loading: boolean) => void
  setAgents: (projectId: string, agents: Agent[]) => void
  updateAgentStatus: (projectId: string, agentId: string, status: Agent['status']) => void
  updateAgent: (projectId: string, agentId: string, updates: Partial<Agent>) => void
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
  resetProject: () => void
  teamConfigs: Record<string, { strategy: string; coordinatorId?: string } | null>
}

// Per-project counters for ID generation
const counters: Record<string, { log: number; event: number; chat: number }> = {}

function getCounters(projectId: string) {
  if (!counters[projectId]) {
    counters[projectId] = { log: 0, event: 0, chat: 0 }
  }
  return counters[projectId]
}

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
    model: 'deepseek-chat',
    temperature: 0.7,
    max_tokens: undefined,
  },
  sidePanelOpen: true,
  sidePanelTab: 'agents',
  terminalExpanded: false,
  terminalFullscreen: false,

  setSidePanelOpen: (open) => set({ sidePanelOpen: open }),
  setSidePanelTab: (tab) => set({ sidePanelTab: tab }),
  setTerminalExpanded: (expanded) => set({ terminalExpanded: expanded }),
  setTerminalFullscreen: (fs) => set({ terminalFullscreen: fs }),

  setGlobalLlmConfig: (config) => set({ globalLlmConfig: config }),
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

  closeProject: (projectId) =>
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
    }),

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
  },

  resetProject: () => {
    const state = useStore.getState()
    if (state.activeProjectId) {
      state.closeProject(state.activeProjectId)
    }
  },
}))
