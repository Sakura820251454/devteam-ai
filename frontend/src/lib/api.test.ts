import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as api from './api'

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('API 模块', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  describe('Agent API', () => {
    it('listAgents 应该获取 Agent 列表', async () => {
      const mockAgents = [
        { id: 'agent-1', name: 'Agent 1', role: '后端', status: 'idle' },
      ]
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAgents,
      })

      const result = await api.listAgents()

      expect(mockFetch).toHaveBeenCalledWith('/api/agents')
      expect(result).toEqual(mockAgents)
    })
  })

  describe('Session API', () => {
    it('createSession 应该创建会话', async () => {
      const mockSession = { id: 'session-1', title: '测试会话' }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSession,
      })

      const result = await api.createSession('测试会话')

      expect(mockFetch).toHaveBeenCalledWith('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: '测试会话' }),
      })
      expect(result).toEqual(mockSession)
    })

    it('listSessions 应该获取会话列表', async () => {
      const mockSessions = [
        { id: 'session-1', title: '会话 1' },
      ]
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSessions,
      })

      const result = await api.listSessions()

      expect(mockFetch).toHaveBeenCalledWith('/api/sessions')
      expect(result).toEqual(mockSessions)
    })
  })

  describe('Chat API', () => {
    it('chat 应该发送消息', async () => {
      const mockResponse = { response: '你好', agent_id: 'agent-1', session_id: 'session-1' }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      const result = await api.chat({
        agent_id: 'agent-1',
        session_id: 'session-1',
        message: '你好',
      })

      expect(mockFetch).toHaveBeenCalledWith('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: 'agent-1',
          session_id: 'session-1',
          message: '你好',
        }),
      })
      expect(result).toEqual(mockResponse)
    })
  })

  describe('Pipeline API', () => {
    it('createPipeline 应该创建 Pipeline', async () => {
      const mockPipeline = { id: 'pipeline-1', name: '测试 Pipeline', status: 'idle' }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockPipeline,
      })

      const result = await api.createPipeline('proj-1', '测试 Pipeline', ['agent-1'])

      expect(mockFetch).toHaveBeenCalledWith('/api/pipelines/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: 'proj-1',
          name: '测试 Pipeline',
          agent_ids: ['agent-1'],
          team_config: {},
        }),
      })
      expect(result).toEqual(mockPipeline)
    })

    it('startPipeline 应该启动 Pipeline', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'started', pipeline_id: 'pipeline-1' }),
      })

      await api.startPipeline('pipeline-1')

      expect(mockFetch).toHaveBeenCalledWith('/api/pipelines/pipeline-1/start', {
        method: 'POST',
      })
    })

    it('pausePipeline 应该暂停 Pipeline', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => undefined,
      })

      await api.pausePipeline('pipeline-1')

      expect(mockFetch).toHaveBeenCalledWith('/api/pipelines/pipeline-1/pause', {
        method: 'POST',
      })
    })

    it('stopPipeline 应该停止 Pipeline', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => undefined,
      })

      await api.stopPipeline('pipeline-1')

      expect(mockFetch).toHaveBeenCalledWith('/api/pipelines/pipeline-1/stop', {
        method: 'POST',
      })
    })
  })

  describe('Task API', () => {
    it('listTasks 应该获取任务列表', async () => {
      const mockTasks = [
        { id: 'task-1', title: '测试任务', status: 'todo' },
      ]
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTasks,
      })

      const result = await api.listTasks('proj-1')

      expect(mockFetch).toHaveBeenCalledWith('/api/tasks/?project_id=proj-1')
      expect(result).toEqual(mockTasks)
    })
  })

  describe('Project API', () => {
    it('createProject 应该创建项目', async () => {
      const mockProject = { id: 'proj-1', name: '测试项目', status: 'planning' }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockProject,
      })

      const result = await api.createProject('测试项目', '项目描述')

      expect(mockFetch).toHaveBeenCalledWith('/api/projects/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: '测试项目',
          description: '项目描述',
          requirements: '',
        }),
      })
      expect(result).toEqual(mockProject)
    })

    it('deleteProject 应该删除项目', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => undefined,
      })

      await api.deleteProject('proj-1')

      expect(mockFetch).toHaveBeenCalledWith('/api/projects/proj-1?cascade=true', {
        method: 'DELETE',
      })
    })
  })

  describe('错误处理', () => {
    it('应该在响应不 ok 时抛出错误', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ detail: 'Server error' }),
      })

      await expect(api.listAgents()).rejects.toThrow()
    })
  })
})
