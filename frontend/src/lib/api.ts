const API_BASE = '/api'

export interface Agent {
  id: string
  name: string
  role: string
  status: string
  llm_config?: LLMConfig
}

export interface LLMConfig {
  provider: string
  model: string
  temperature: number
  max_tokens?: number
}

export interface LLMModelInfo {
  name: string
  provider: string
  input_cost_per_1k: number
  output_cost_per_1k: number
  max_tokens: number
  supports_streaming: boolean
  description: string
}

export interface CostSummary {
  total_cost: number
  total_tokens: number
  prompt_tokens: number
  completion_tokens: number
  call_count: number
  by_model: Record<string, { cost: number; tokens: number; calls: number }>
  by_agent: Record<string, { cost: number; tokens: number; calls: number }>
}

export interface CostRecord {
  id: string
  agent_id?: string
  task_id?: string
  model: string
  provider: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  cost: number
  created_at: string
}

export interface Message {
  id: string
  sender_id: string
  sender_name: string
  content: string
  type: string
  timestamp: string
}

export interface Session {
  id: string
  title: string
  status: string
  participants: string[]
  message_count: number
  token_used: number
  created_at: string
}

export interface ChatRequest {
  agent_id: string
  session_id: string
  message: string
}

export interface ChatResponse {
  response: string
  agent_id: string
  session_id: string
}

export async function listAgents(): Promise<Agent[]> {
  const response = await fetch(`${API_BASE}/agents`)
  if (!response.ok) {
    throw new Error(`获取Agent列表失败: ${response.statusText}`)
  }
  const data = await response.json()
  // API returns {agents: [...], total: N}
  return data.agents || data
}

export async function createSession(title?: string): Promise<Session> {
  const response = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: title || '新会话' }),
  })
  if (!response.ok) {
    throw new Error(`创建会话失败: ${response.statusText}`)
  }
  return response.json()
}

export async function listSessions(): Promise<Session[]> {
  const response = await fetch(`${API_BASE}/sessions`)
  if (!response.ok) {
    throw new Error(`获取会话列表失败: ${response.statusText}`)
  }
  return response.json()
}

export async function getSession(sessionId: string): Promise<Session> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}`)
  if (!response.ok) {
    throw new Error(`获取会话失败: ${response.statusText}`)
  }
  return response.json()
}

export async function getMessages(sessionId: string): Promise<Message[]> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/messages`)
  if (!response.ok) {
    throw new Error(`获取消息失败: ${response.statusText}`)
  }
  return response.json()
}

export async function chat(request: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!response.ok) {
    throw new Error(`聊天请求失败: ${response.statusText}`)
  }
  return response.json()
}

export class StreamError extends Error {
  constructor(message: string, public isAborted: boolean = false) {
    super(message)
    this.name = 'StreamError'
  }
}

export async function* chatStream(
  request: ChatRequest
): AsyncGenerator<string, void, unknown> {
  let response: Response | null = null
  
  try {
    response = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const errorText = await response.text().catch(() => response?.statusText || 'Unknown error')
      throw new StreamError(`请求失败: ${response.status} - ${errorText}`)
    }

    if (!response.body) {
      throw new StreamError('响应体为空')
    }

    const reader = response.body.getReader()
    
    const decoder = new TextDecoder()
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) {
          if (buffer.trim()) {
            const data = buffer.trim()
            if (data.startsWith('data: ') && data !== 'data: [DONE]') {
              yield data.slice(6)
            }
          }
          break
        }

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmedLine = line.trim()
          if (!trimmedLine.startsWith('data: ')) continue
          
          const data = trimmedLine.slice(6)
          
          if (data === '[DONE]') {
            return
          }
          
          if (data.startsWith('[ERROR]')) {
            throw new StreamError(data.slice(7))
          }
          
          yield data
        }
      }
    } catch (readError) {
      if ((readError as Error).name === 'AbortError') {
        throw new StreamError('请求被取消', true)
      }
      throw readError
    } finally {
      reader.releaseLock()
    }
    
  } catch (error) {
    if (error instanceof StreamError) {
      throw error
    }
    
    if ((error as Error).name === 'AbortError' || 
        (error as Error).message?.includes('aborted')) {
      throw new StreamError('请求被取消', true)
    }
    
    throw new StreamError(
      error instanceof Error ? error.message : '流式请求失败'
    )
  } finally {
    if (response?.body) {
      try {
        response.body.cancel()
      } catch {
        // 忽略取消错误
      }
    }
  }
}

export async function pauseSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/pause`, { 
    method: 'POST' 
  })
  if (!response.ok) {
    throw new Error(`暂停会话失败: ${response.statusText}`)
  }
}

export async function resumeSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/resume`, { 
    method: 'POST' 
  })
  if (!response.ok) {
    throw new Error(`恢复会话失败: ${response.statusText}`)
  }
}

export async function endSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/end`, { 
    method: 'POST' 
  })
  if (!response.ok) {
    throw new Error(`结束会话失败: ${response.statusText}`)
  }
}

export async function getAvailableModels(): Promise<Record<string, LLMModelInfo>> {
  const response = await fetch(`${API_BASE}/llm/models`)
  if (!response.ok) {
    throw new Error(`获取模型列表失败: ${response.statusText}`)
  }
  return response.json()
}

export async function getAvailableProviders(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/llm/providers`)
  if (!response.ok) {
    throw new Error(`获取提供商列表失败: ${response.statusText}`)
  }
  return response.json()
}

export async function getModelInfo(modelName: string): Promise<LLMModelInfo> {
  const response = await fetch(`${API_BASE}/llm/models/${modelName}`)
  if (!response.ok) {
    throw new Error(`获取模型信息失败: ${response.statusText}`)
  }
  return response.json()
}

export async function llmChat(request: {
  messages: { role: string; content: string }[]
  agent_id?: string
  model?: string
  temperature?: number
  max_tokens?: number
  track_cost?: boolean
}): Promise<{ content: string; usage: Record<string, number>; model: string; finish_reason: string }> {
  const response = await fetch(`${API_BASE}/llm/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!response.ok) {
    throw new Error(`LLM聊天失败: ${response.statusText}`)
  }
  return response.json()
}

export async function getCostSummary(agent_id?: string, task_id?: string): Promise<CostSummary> {
  const params = new URLSearchParams()
  if (agent_id) params.set('agent_id', agent_id)
  if (task_id) params.set('task_id', task_id)
  
  const response = await fetch(`${API_BASE}/llm/costs/summary?${params}`)
  if (!response.ok) {
    throw new Error(`获取成本汇总失败: ${response.statusText}`)
  }
  return response.json()
}

export async function getCostRecords(agent_id?: string, task_id?: string, limit: number = 100): Promise<CostRecord[]> {
  const params = new URLSearchParams()
  if (agent_id) params.set('agent_id', agent_id)
  if (task_id) params.set('task_id', task_id)
  params.set('limit', limit.toString())
  
  const response = await fetch(`${API_BASE}/llm/costs/records?${params}`)
  if (!response.ok) {
    throw new Error(`获取成本记录失败: ${response.statusText}`)
  }
  return response.json()
}

export async function clearCostRecords(): Promise<void> {
  const response = await fetch(`${API_BASE}/llm/costs/records`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    throw new Error(`清除成本记录失败: ${response.statusText}`)
  }
}

// ============ Workspace API ============

export interface WorkspaceInfo {
  id: string
  name: string
  description: string
  created_at: string
  updated_at: string
  status: string
  agents: Array<Record<string, unknown>>
  stages: Array<Record<string, unknown>>
  files?: WorkspaceFile[]
  workspace_path?: string
}

export interface WorkspaceFile {
  name: string
  path: string
  type: 'file' | 'directory'
  size?: number
  modified_at?: string
  children?: WorkspaceFile[]
}

export async function createWorkspace(
  projectId: string,
  name: string,
  description: string,
  agents: Array<Record<string, unknown>> = [],
  stages: Array<Record<string, unknown>> = [],
): Promise<{ workspace: WorkspaceInfo; workspace_path: string }> {
  const response = await fetch(`${API_BASE}/workspaces`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId, name, description, agents, stages }),
  })
  if (!response.ok) {
    throw new Error(`创建工作区失败: ${response.statusText}`)
  }
  return response.json()
}

export async function getWorkspace(projectId: string): Promise<WorkspaceInfo> {
  const response = await fetch(`${API_BASE}/workspaces/${projectId}`)
  if (!response.ok) {
    throw new Error(`获取工作区失败: ${response.statusText}`)
  }
  return response.json()
}

export async function listWorkspaces(): Promise<WorkspaceInfo[]> {
  const response = await fetch(`${API_BASE}/workspaces`)
  if (!response.ok) {
    throw new Error(`获取工作区列表失败: ${response.statusText}`)
  }
  const data = await response.json()
  return data.workspaces || []
}

export async function addArtifact(
  projectId: string,
  stageKey: string,
  name: string,
  content: string,
): Promise<{ path: string; stage: string; name: string }> {
  const response = await fetch(`${API_BASE}/workspaces/${projectId}/artifacts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stage_key: stageKey, name, content }),
  })
  if (!response.ok) {
    throw new Error(`添加产物失败: ${response.statusText}`)
  }
  return response.json()
}

export async function listWorkspaceFiles(
  projectId: string,
  subdir: string = '',
): Promise<WorkspaceFile[]> {
  const params = subdir ? `?subdir=${encodeURIComponent(subdir)}` : ''
  const response = await fetch(`${API_BASE}/workspaces/${projectId}/files${params}`)
  if (!response.ok) {
    throw new Error(`获取文件列表失败: ${response.statusText}`)
  }
  const data = await response.json()
  return data.files || []
}

export async function readWorkspaceFile(
  projectId: string,
  filePath: string,
): Promise<{ path: string; content: string }> {
  const response = await fetch(`${API_BASE}/workspaces/${projectId}/files/${encodeURIComponent(filePath)}`)
  if (!response.ok) {
    throw new Error(`读取文件失败: ${response.statusText}`)
  }
  return response.json()
}

export async function addWorkspaceLog(
  projectId: string,
  level: string,
  source: string,
  message: string,
): Promise<void> {
  const response = await fetch(`${API_BASE}/workspaces/${projectId}/logs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ level, source, message }),
  })
  if (!response.ok) {
    console.warn(`添加日志失败: ${response.statusText}`)
  }
}

export async function updateWorkspaceStatus(
  projectId: string,
  status: string,
  currentStage: string = '',
): Promise<void> {
  const params = new URLSearchParams({ status })
  if (currentStage) params.set('current_stage', currentStage)
  const response = await fetch(`${API_BASE}/workspaces/${projectId}/status?${params}`, {
    method: 'PATCH',
  })
  if (!response.ok) {
    console.warn(`更新工作区状态失败: ${response.statusText}`)
  }
}

export async function deleteWorkspace(projectId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/workspaces/${projectId}`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    throw new Error(`删除工作区失败: ${response.statusText}`)
  }
}

// ============ Settings API ============

export interface AppSettings {
  workspace_root: string
  workspace_root_resolved: string
}

export async function getSettings(): Promise<AppSettings> {
  const response = await fetch(`${API_BASE}/settings`)
  if (!response.ok) {
    throw new Error(`获取设置失败: ${response.statusText}`)
  }
  return response.json()
}

export async function updateSettings(workspaceRoot: string): Promise<AppSettings> {
  const response = await fetch(`${API_BASE}/settings`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workspace_root: workspaceRoot }),
  })
  if (!response.ok) {
    throw new Error(`更新设置失败: ${response.statusText}`)
  }
  return response.json()
}