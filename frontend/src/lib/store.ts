import { create } from 'zustand'

export interface Agent {
  id: string
  name: string
  role: string
  status: 'idle' | 'thinking' | 'working' | 'waiting' | 'blocked'
  avatarColor: string
  currentTask?: string
  description?: string
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

interface WorkspaceState {
  // Pipeline
  pipeline: Pipeline | null
  selectedStage: string | null

  // Tasks
  tasks: Task[]
  tasksLoading: boolean

  // Agents
  agents: Agent[]

  // Side panel
  sidePanelOpen: boolean
  sidePanelTab: 'agents' | 'timeline' | 'cost'

  // Terminal
  terminalExpanded: boolean
  terminalFullscreen: boolean
  logs: LogEntry[]

  // Timeline
  events: TimelineEvent[]

  // Chat
  chatMessages: ChatMessage[]

  // Intervention
  interventionMode: null | 'whisper' | 'broadcast' | 'pause'

  // Cost
  costData: CostData | null

  // Global status
  isConnected: boolean
  isLoading: boolean
  error: string | null

  // Actions
  setPipeline: (pipeline: Pipeline | null) => void
  updatePipelineStage: (stageKey: string, updates: Partial<PipelineStage>) => void
  setSelectedStage: (stage: string | null) => void
  setTasks: (tasks: Task[]) => void
  setTasksLoading: (loading: boolean) => void
  setAgents: (agents: Agent[]) => void
  updateAgentStatus: (agentId: string, status: Agent['status']) => void
  updateAgent: (agentId: string, updates: Partial<Agent>) => void
  setSidePanelOpen: (open: boolean) => void
  setSidePanelTab: (tab: 'agents' | 'timeline' | 'cost') => void
  setTerminalExpanded: (expanded: boolean) => void
  setTerminalFullscreen: (fs: boolean) => void
  addLog: (log: Omit<LogEntry, 'id' | 'timestamp'>) => void
  addLogs: (logs: Omit<LogEntry, 'id' | 'timestamp'>[]) => void
  clearLogs: () => void
  addEvent: (event: Omit<TimelineEvent, 'id' | 'timestamp'>) => void
  addEvents: (events: Omit<TimelineEvent, 'id' | 'timestamp'>[]) => void
  addChatMessage: (msg: Omit<ChatMessage, 'id' | 'timestamp'>) => void
  clearChatMessages: () => void
  setInterventionMode: (mode: null | 'whisper' | 'broadcast' | 'pause') => void
  setCostData: (data: CostData | null) => void
  setConnected: (connected: boolean) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  startProject: (name: string, description: string) => void
  resetProject: () => void
}

let logCounter = 0
let eventCounter = 0
let chatCounter = 0

export const useStore = create<WorkspaceState>((set) => ({
  pipeline: null,
  selectedStage: null,
  tasks: [],
  tasksLoading: false,
  agents: [],
  sidePanelOpen: true,
  sidePanelTab: 'agents',
  terminalExpanded: false,
  terminalFullscreen: false,
  logs: [],
  events: [],
  chatMessages: [],
  interventionMode: null,
  costData: null,
  isConnected: false,
  isLoading: false,
  error: null,

  setPipeline: (pipeline) => set({ pipeline }),
  updatePipelineStage: (stageKey, updates) =>
    set((state) => ({
      pipeline: state.pipeline
        ? {
            ...state.pipeline,
            stages: state.pipeline.stages.map((s) =>
              s.key === stageKey ? { ...s, ...updates } : s,
            ),
          }
        : null,
    })),
  setSelectedStage: (stage) => set({ selectedStage: stage, tasks: [] }),
  setTasks: (tasks) => set({ tasks }),
  setTasksLoading: (loading) => set({ tasksLoading: loading }),
  setAgents: (agents) => set({ agents }),
  updateAgentStatus: (agentId, status) =>
    set((state) => ({
      agents: state.agents.map((a) =>
        a.id === agentId ? { ...a, status } : a,
      ),
    })),
  updateAgent: (agentId, updates) =>
    set((state) => ({
      agents: state.agents.map((a) =>
        a.id === agentId ? { ...a, ...updates } : a,
      ),
    })),
  setSidePanelOpen: (open) => set({ sidePanelOpen: open }),
  setSidePanelTab: (tab) => set({ sidePanelTab: tab }),
  setTerminalExpanded: (expanded) => set({ terminalExpanded: expanded }),
  setTerminalFullscreen: (fs) => set({ terminalFullscreen: fs }),
  addLog: (log) =>
    set((state) => ({
      logs: [
        ...state.logs.slice(-500),
        {
          ...log,
          id: `log-${++logCounter}`,
          timestamp: new Date().toISOString(),
        },
      ],
    })),
  addLogs: (logs) =>
    set((state) => ({
      logs: [
        ...state.logs.slice(-500),
        ...logs.map((l) => ({
          ...l,
          id: `log-${++logCounter}`,
          timestamp: new Date().toISOString(),
        })),
      ].slice(-500),
    })),
  clearLogs: () => set({ logs: [] }),
  addEvent: (event) =>
    set((state) => ({
      events: [
        ...state.events,
        {
          ...event,
          id: `evt-${++eventCounter}`,
          timestamp: new Date().toISOString(),
        },
      ].slice(-200),
    })),
  addEvents: (events) =>
    set((state) => ({
      events: [
        ...state.events,
        ...events.map((e) => ({
          ...e,
          id: `evt-${++eventCounter}`,
          timestamp: new Date().toISOString(),
        })),
      ].slice(-200),
    })),
  addChatMessage: (msg) =>
    set((state) => ({
      chatMessages: [
        ...state.chatMessages,
        {
          ...msg,
          id: `chat-${++chatCounter}`,
          timestamp: new Date().toISOString(),
        },
      ].slice(-500),
    })),
  clearChatMessages: () => set({ chatMessages: [] }),
  setInterventionMode: (mode) => set({ interventionMode: mode }),
  setCostData: (data) => set({ costData: data }),
  setConnected: (connected) => set({ isConnected: connected }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),

  startProject: (name, _description) => {
    const now = new Date().toISOString()

    const defaultAgents: Agent[] = [
      { id: 'pm', name: '产品经理', role: '产品经理', status: 'idle', avatarColor: '#58a6ff', description: '负责需求分析与任务拆解' },
      { id: 'architect', name: '架构师', role: '架构师', status: 'idle', avatarColor: '#a371f7', description: '负责技术方案设计与代码审查' },
      { id: 'backend', name: '后端开发', role: '后端开发', status: 'idle', avatarColor: '#3fb950', description: '负责后端 API 与数据库' },
      { id: 'frontend', name: '前端开发', role: '前端开发', status: 'idle', avatarColor: '#f0883e', description: '负责前端界面与交互' },
      { id: 'tester', name: '测试工程师', role: '测试工程师', status: 'idle', avatarColor: '#f85149', description: '负责测试用例与质量保障' },
      { id: 'devops', name: 'DevOps', role: '运维工程师', status: 'idle', avatarColor: '#39d2c0', description: '负责部署与基础设施' },
    ]

    const pipeline: Pipeline = {
      id: `pipeline-${Date.now()}`,
      name,
      status: 'running',
      currentStage: 'requirement_analysis',
      progress: 0,
      stages: [
        { key: 'requirement_analysis', label: '需求分析', status: 'pending', assignedAgents: ['pm', 'architect'], artifacts: [] },
        { key: 'task_breakdown', label: '任务拆解', status: 'pending', assignedAgents: ['pm', 'architect'], artifacts: [] },
        { key: 'coding', label: '编码实现', status: 'pending', assignedAgents: ['backend', 'frontend'], artifacts: [] },
        { key: 'review', label: '代码审查', status: 'pending', assignedAgents: ['architect', 'tester'], artifacts: [] },
        { key: 'testing', label: '测试验证', status: 'pending', assignedAgents: ['tester'], artifacts: [] },
        { key: 'delivery', label: '交付部署', status: 'pending', assignedAgents: ['devops'], artifacts: [] },
      ],
      createdAt: now,
    }

    set({
      pipeline,
      agents: defaultAgents,
      tasks: [],
      events: [],
      chatMessages: [],
      logs: [],
      costData: null,
      selectedStage: null,
      isLoading: true,
      isConnected: true,
      error: null,
    })
    logCounter = 0
    eventCounter = 0
    chatCounter = 0
  },

  resetProject: () =>
    set({
      pipeline: null,
      agents: [],
      tasks: [],
      events: [],
      chatMessages: [],
      logs: [],
      costData: null,
      selectedStage: null,
      isLoading: false,
      isConnected: false,
      error: null,
    }),
}))
