import { describe, it, expect, beforeEach } from 'vitest'
import { useStore } from './store'

describe('useStore', () => {
  beforeEach(() => {
    // 每个测试前重置 store
    useStore.setState({
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
      questionsByProject: {},
      tasksLoadingByProject: {},
    })
  })

  describe('项目管理', () => {
    it('createProject 应该创建项目', () => {
      const { createProject } = useStore.getState()
      createProject('proj-1', '测试项目', '项目描述')

      const { projects, activeProjectId } = useStore.getState()
      expect(projects).toHaveLength(1)
      expect(projects[0].name).toBe('测试项目')
      expect(activeProjectId).toBe('proj-1')
    })

    it('switchProject 应该切换活跃项目', () => {
      const { createProject, switchProject } = useStore.getState()
      createProject('proj-1', '项目 1', '')
      createProject('proj-2', '项目 2', '')

      switchProject('proj-2')

      const { activeProjectId } = useStore.getState()
      expect(activeProjectId).toBe('proj-2')
    })

    it('updateProjectProgress 应该更新项目进度', () => {
      const { createProject, updateProjectProgress } = useStore.getState()
      createProject('proj-1', '测试项目', '')

      updateProjectProgress('proj-1', 50)

      const { projects } = useStore.getState()
      expect(projects[0].progress).toBe(50)
    })
  })

  describe('Agent 管理', () => {
    it('setAgents 应该设置项目的 Agent 列表', () => {
      const { setAgents } = useStore.getState()
      setAgents('proj-1', [
        { id: 'agent-1', name: 'Agent 1', role: '后端', status: 'idle', avatarColor: '#3B82F6' },
        { id: 'agent-2', name: 'Agent 2', role: '前端', status: 'idle', avatarColor: '#10B981' },
      ])

      const { agentsByProject } = useStore.getState()
      expect(agentsByProject['proj-1']).toHaveLength(2)
    })

    it('updateAgentStatus 应该更新指定 Agent 状态', () => {
      const { setAgents, updateAgentStatus } = useStore.getState()
      setAgents('proj-1', [
        { id: 'agent-1', name: 'Agent 1', role: '后端', status: 'idle', avatarColor: '#3B82F6' },
      ])

      updateAgentStatus('proj-1', 'agent-1', 'working')

      const { agentsByProject } = useStore.getState()
      expect(agentsByProject['proj-1'][0].status).toBe('working')
    })
  })

  describe('Pipeline 管理', () => {
    it('setPipeline 应该设置 Pipeline', () => {
      const { setPipeline } = useStore.getState()
      setPipeline('proj-1', {
        id: 'pipeline-1',
        name: '测试 Pipeline',
        status: 'idle',
        currentStage: '需求分析',
        progress: 0,
        stages: [],
        createdAt: new Date().toISOString(),
      })

      const { pipelines } = useStore.getState()
      expect(pipelines['proj-1']).not.toBeNull()
      expect(pipelines['proj-1']?.id).toBe('pipeline-1')
    })

    it('updatePipelineStage 应该更新 Pipeline 阶段', () => {
      const { setPipeline, updatePipelineStage } = useStore.getState()
      setPipeline('proj-1', {
        id: 'pipeline-1',
        name: '测试 Pipeline',
        status: 'idle',
        currentStage: '需求分析',
        progress: 0,
        stages: [
          { key: 'req', label: '需求分析', status: 'active', assignedAgents: [], artifacts: [] },
        ],
        createdAt: new Date().toISOString(),
      })

      updatePipelineStage('proj-1', 'req', { status: 'completed' })

      const { pipelines } = useStore.getState()
      expect(pipelines['proj-1']?.stages[0].status).toBe('completed')
    })
  })

  describe('任务管理', () => {
    it('setTasks 应该设置任务列表', () => {
      const { setTasks } = useStore.getState()
      setTasks('proj-1', [
        {
          id: 'task-1',
          title: '测试任务',
          description: '',
          status: 'todo',
          priority: 'medium',
          stage: '需求分析',
          assignedAgents: [],
          createdBy: 'user',
          statusHistory: [],
          tags: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        },
      ])

      const { tasksByProject } = useStore.getState()
      expect(tasksByProject['proj-1']).toHaveLength(1)
    })

    it('updateTask 应该更新任务状态', () => {
      const { setTasks, updateTask } = useStore.getState()
      setTasks('proj-1', [
        {
          id: 'task-1',
          title: '测试任务',
          description: '',
          status: 'todo',
          priority: 'medium',
          stage: '需求分析',
          assignedAgents: [],
          createdBy: 'user',
          statusHistory: [],
          tags: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        },
      ])

      updateTask('proj-1', 'task-1', { status: 'in_progress' })

      const { tasksByProject } = useStore.getState()
      expect(tasksByProject['proj-1'][0].status).toBe('in_progress')
    })
  })

  describe('对话消息', () => {
    it('addChatMessage 应该添加消息', () => {
      const { addChatMessage } = useStore.getState()
      addChatMessage('proj-1', {
        id: 'msg-1',
        agentId: 'agent-1',
        agentName: '测试 Agent',
        agentColor: '#3B82F6',
        content: '你好',
        timestamp: new Date().toISOString(),
      })

      const { chatMessagesByProject } = useStore.getState()
      expect(chatMessagesByProject['proj-1']).toHaveLength(1)
      expect(chatMessagesByProject['proj-1'][0].content).toBe('你好')
    })

    it('clearChatMessages 应该清空消息', () => {
      const { addChatMessage, clearChatMessages } = useStore.getState()
      addChatMessage('proj-1', {
        id: 'msg-1',
        agentId: 'agent-1',
        agentName: '测试 Agent',
        agentColor: '#3B82F6',
        content: '你好',
        timestamp: new Date().toISOString(),
      })

      clearChatMessages('proj-1')

      const { chatMessagesByProject } = useStore.getState()
      expect(chatMessagesByProject['proj-1']).toHaveLength(0)
    })
  })
})
