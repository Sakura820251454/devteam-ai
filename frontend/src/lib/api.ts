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
  const response = await fetch(`${API_BASE}/agents/`)
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
  teamConfig?: { strategy: string; coordinatorId?: string },
  template?: { id: string; name: string; stages: Array<Record<string, unknown>> },
): Promise<{ workspace: WorkspaceInfo; workspace_path: string }> {
  const response = await fetch(`${API_BASE}/workspaces`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId, name, description, agents, stages, team_config: teamConfig, template }),
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
  const response = await fetch(`${API_BASE}/workspaces/`)
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
  llm_mode?: string
}

export async function getSettings(): Promise<AppSettings> {
  const response = await fetch(`${API_BASE}/settings/`)
  if (!response.ok) {
    throw new Error(`获取设置失败: ${response.statusText}`)
  }
  return response.json()
}

// ============ Execution API ============

export interface ExecutionStep {
  index: number
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  startedAt?: string
  completedAt?: string
  result?: string
  error?: string
}

export interface TaskExecutionStatus {
  task_id: string
  agent_id: string
  status: string
  current_step: number
  total_steps: number
  last_heartbeat?: string
  accumulated_result?: string
  started_at?: string
  completed_at?: string
}

export interface StuckTaskInfo {
  task_id: string
  agent_id: string
  reason: string
  elapsed_seconds: number
  current_step: number
  total_steps: number
  last_heartbeat?: string
}

export interface CheckpointInfo {
  id: string
  task_id: string
  step_index: number
  step_name: string
  partial_result?: string
  created_at?: string
}

export async function getTaskExecutionStatus(taskId: string): Promise<TaskExecutionStatus> {
  const response = await fetch(`${API_BASE}/execution/tasks/${taskId}/status`)
  if (!response.ok) throw new Error('获取执行状态失败')
  return response.json()
}

export async function retryTask(taskId: string, fromCheckpoint: boolean = true): Promise<void> {
  await fetch(`${API_BASE}/execution/tasks/${taskId}/retry?from_checkpoint=${fromCheckpoint}`, {
    method: 'POST',
  })
}

export async function getStuckTasks(thresholdSeconds?: number): Promise<StuckTaskInfo[]> {
  const params = thresholdSeconds ? `?threshold_seconds=${thresholdSeconds}` : ''
  const response = await fetch(`${API_BASE}/execution/stuck${params}`)
  if (!response.ok) throw new Error('获取卡死任务失败')
  const data = await response.json()
  return data.stuck_tasks
}

export async function getTaskHeartbeat(taskId: string): Promise<TaskExecutionStatus> {
  const response = await fetch(`${API_BASE}/execution/heartbeat/${taskId}`)
  if (!response.ok) throw new Error('获取心跳信息失败')
  return response.json()
}

export async function listCheckpoints(taskId: string): Promise<CheckpointInfo[]> {
  const response = await fetch(`${API_BASE}/execution/tasks/${taskId}/checkpoints`)
  if (!response.ok) throw new Error('获取检查点失败')
  const data = await response.json()
  return data.checkpoints
}

export async function restoreCheckpoint(taskId: string, checkpointId: string): Promise<void> {
  await fetch(`${API_BASE}/execution/tasks/${taskId}/checkpoints/${checkpointId}/restore`, {
    method: 'POST',
  })
}

export async function getMonitorStatus(): Promise<{ monitoring: boolean }> {
  const response = await fetch(`${API_BASE}/execution/monitor/status`)
  if (!response.ok) throw new Error('获取监控状态失败')
  return response.json()
}

export async function pausePipeline(pipelineId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/pipelines/${pipelineId}/pause`, { method: 'POST' })
  if (!response.ok) throw new Error('暂停流水线失败')
}

export async function resumePipeline(pipelineId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/pipelines/${pipelineId}/resume`, { method: 'POST' })
  if (!response.ok) throw new Error('恢复流水线失败')
}

export async function stopPipeline(pipelineId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/pipelines/${pipelineId}/stop`, { method: 'POST' })
  if (!response.ok) throw new Error('停止流水线失败')
}

export async function closePipeline(pipelineId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/pipelines/${pipelineId}/close`, { method: 'POST' })
  if (!response.ok) throw new Error('关闭流水线失败')
}

export async function resumeFromClose(pipelineId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/pipelines/${pipelineId}/resume-from-close`, { method: 'POST' })
  if (!response.ok) throw new Error('恢复流水线失败')
}

export async function createPipeline(projectId: string, name: string, agentIds: string[], teamConfig?: { strategy: string; coordinatorId?: string }): Promise<{ id: string; project_id: string; name: string; status: string }> {
  const response = await fetch(`${API_BASE}/pipelines/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId, name, agent_ids: agentIds, team_config: teamConfig || {} }),
  })
  if (!response.ok) {
    const err = await response.json().catch(() => null)
    const detail = err?.detail || '创建流水线失败'
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return response.json()
}

export async function startPipeline(pipelineId: string): Promise<{ status: string; pipeline_id: string }> {
  const response = await fetch(`${API_BASE}/pipelines/${pipelineId}/start`, { method: 'POST' })
  if (!response.ok) throw new Error('启动流水线失败')
  return response.json()
}

export async function getActivePipeline(projectId: string): Promise<Record<string, unknown> | null> {
  const response = await fetch(`${API_BASE}/pipelines/active?project_id=${encodeURIComponent(projectId)}`)
  if (!response.ok) throw new Error('获取活跃流水线失败')
  const data = await response.json()
  return data.pipeline || null
}

export async function listPipelines(projectId: string): Promise<{ pipelines: Array<Record<string, unknown>> }> {
  const response = await fetch(`${API_BASE}/pipelines/?project_id=${encodeURIComponent(projectId)}`)
  if (!response.ok) throw new Error('获取流水线列表失败')
  return response.json()
}

export async function getPipeline(pipelineId: string): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE}/pipelines/${pipelineId}`)
  if (!response.ok) throw new Error('获取流水线失败')
  return response.json()
}

export async function getPipelineLogs(pipelineId: string, limit: number = 50): Promise<{ logs: Array<{ stage: string; message: string; level: string; timestamp: string }> }> {
  const response = await fetch(`${API_BASE}/pipelines/${pipelineId}/logs?limit=${limit}`)
  if (!response.ok) throw new Error('获取流水线日志失败')
  return response.json()
}

export async function listTasks(projectId?: string, status?: string): Promise<Array<Record<string, unknown>>> {
  const params = new URLSearchParams()
  if (projectId) params.set('project_id', projectId)
  if (status) params.set('status', status)
  const qs = params.toString()
  const response = await fetch(`${API_BASE}/tasks/${qs ? '?' + qs : ''}`)
  if (!response.ok) throw new Error('获取任务列表失败')
  return response.json()
}

// ========== Task Analysis API (Step 2) ==========

export interface TaskAnalysis {
  domain: string
  task_type: string
  sub_types: string[]
  complexity: string
  breakdown: string[]
  key_challenge: string
  analysis_summary: string
}

export async function analyzeTask(taskDescription: string): Promise<TaskAnalysis> {
  const response = await fetch(`${API_BASE}/task-analysis/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_description: taskDescription }),
  })
  if (!response.ok) throw new Error('任务分析失败')
  return response.json()
}

// ========== Team Suggestion API (Step 3) ==========

export interface SuggestedRole {
  role_name: string
  responsibilities: string
  required_capabilities: string[]
  suggested_soul: string
  matching_reason: string
  priority: string
}

export interface StrategySuggestion {
  recommended: string
  reasoning: string
  alternatives: Array<{ strategy: string; reason: string }>
}

export interface TeamSuggestion {
  team_name: string
  roles: SuggestedRole[]
  strategy: StrategySuggestion
  overall_rationale: string
}

export interface TeamSuggestionResponse {
  analysis: TaskAnalysis
  suggestion: TeamSuggestion
}

export async function suggestTeam(taskDescription: string): Promise<TeamSuggestionResponse> {
  const response = await fetch(`${API_BASE}/team-suggestion/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_description: taskDescription }),
  })
  if (!response.ok) throw new Error('团队建议失败')
  return response.json()
}

// ========== Strategy Recommendation API ==========

export interface StrategyRecommendation {
  recommended_strategy: string
  confidence: number
  reasoning: string
  suggested_coordinator: string | null
  alternative_strategies: Array<{ strategy: string; reason: string }>
}

export async function recommendStrategy(
  projectName: string,
  projectDescription: string,
  agentIds: string[],
  requirements: string = '',
  templateId?: string,
): Promise<StrategyRecommendation> {
  const response = await fetch(`${API_BASE}/pipelines/recommend-strategy`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_name: projectName,
      project_description: projectDescription,
      requirements,
      agent_ids: agentIds,
      template_id: templateId || null,
    }),
  })
  if (!response.ok) throw new Error('策略推荐失败')
  return response.json()
}

// ========== Pipeline Template Adjustment API ==========

export interface StageAdjustment {
  key: string
  label: string
  description: string
  expected_artifact: string
  parallel_group: string | null
}

export interface AdjustmentSuggestions {
  analysis: string
  recommended_strategy: string
  changes: {
    add: Array<{ label: string; description: string; expected_artifact: string; position: number }>
    remove: string[]
    reorder: Array<{ key: string; new_position: number }>
    rename: Array<{ key: string; new_label: string }>
  }
  final_stages: StageAdjustment[]
}

export async function adjustPipelineTemplate(
  projectName: string,
  projectDescription: string,
  templateId: string,
): Promise<AdjustmentSuggestions> {
  const response = await fetch(`${API_BASE}/pipelines/templates/adjust`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_name: projectName, project_description: projectDescription, template_id: templateId }),
  })
  if (!response.ok) throw new Error('调整模板失败')
  return response.json()
}

export async function applyPipelineAdjustment(
  templateId: string,
  adjustments: Record<string, unknown>,
): Promise<{ stages: StageAdjustment[] }> {
  const response = await fetch(`${API_BASE}/pipelines/templates/apply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ template_id: templateId, adjustments }),
  })
  if (!response.ok) throw new Error('应用调整失败')
  return response.json()
}

export async function updatePipelineStages(
  pipelineId: string,
  stages: StageAdjustment[],
  projectId?: string,
): Promise<{ status: string; stages: StageAdjustment[] }> {
  const response = await fetch(`${API_BASE}/pipelines/${pipelineId}/stages`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stages, project_id: projectId || undefined }),
  })
  if (!response.ok) throw new Error('保存流水线阶段失败')
  return response.json()
}

export async function confirmPipelineStages(
  pipelineId: string,
  stages: StageAdjustment[],
  projectId?: string,
): Promise<{ status: string; stages: StageAdjustment[] }> {
  const response = await fetch(`${API_BASE}/pipelines/${pipelineId}/confirm-stages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stages, project_id: projectId || undefined }),
  })
  if (!response.ok) throw new Error('确认流水线阶段失败')
  return response.json()
}

export async function retryTaskWithFeedback(taskId: string, agentId: string): Promise<{ status: string; error?: string }> {
  const response = await fetch(`${API_BASE}/execution/tasks/${taskId}/retry-with-feedback?agent_id=${encodeURIComponent(agentId)}`, {
    method: 'POST',
  })
  if (!response.ok) throw new Error('重试失败')
  return response.json()
}

export async function getArtifactStatus(projectId: string, stages: Array<Record<string, unknown>>): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE}/workspaces/${projectId}/artifacts/status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stages }),
  })
  if (!response.ok) throw new Error('获取产出物状态失败')
  return response.json()
}

export interface InterventionItem {
  type: string
  task_id?: string | null
  task_title?: string
  agent_name?: string
  question?: string
  context?: string
  options?: string
  risk_level?: string
  message?: string
  agent_id?: string | null
  timestamp: string
}

export interface AgentQuestion {
  type: 'question_for_user'
  task_id: string | null
  task_title: string
  agent_name: string
  question: string
  context: string
  options: string
  timestamp: string
}

export async function getInterventionQueue(): Promise<{ queue: InterventionItem[] }> {
  const response = await fetch(`${API_BASE}/pipelines/interventions/queue`)
  if (!response.ok) throw new Error('获取干预队列失败')
  return response.json()
}

export async function respondToAgent(
  pipelineId: string,
  taskId: string | null,
  answer: string,
): Promise<{ status: string; task_id: string | null }> {
  const response = await fetch(`${API_BASE}/pipelines/${pipelineId}/respond-to-agent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_id: taskId, answer }),
  })
  if (!response.ok) throw new Error('答复Agent失败')
  return response.json()
}

export async function intervenePipeline(
  pipelineId: string,
  message: string,
  agentId?: string,
): Promise<void> {
  await fetch(`${API_BASE}/pipelines/${pipelineId}/intervene`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, agent_id: agentId || null }),
  })
}

export async function getPipelineStatus(pipelineId: string): Promise<{
  pipeline_id: string
  status: string
  current_stage: string
  progress: number
  running_tasks: Array<Record<string, unknown>>
  is_paused: boolean
}> {
  const response = await fetch(`${API_BASE}/pipelines/${pipelineId}/status`)
  if (!response.ok) throw new Error('获取流水线状态失败')
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

// ========== 多项目管理 API ==========

export interface ProjectSummary {
  id: string
  name: string
  description: string
  status: string
  current_phase: string
  pipeline_count: number
  active_pipeline: Record<string, unknown> | null
  task_count: number
  agent_count: number
  agents: Array<{ id: string; name: string; type: string }>
  created_at: string
  updated_at: string
}

export async function listProjects(status?: string): Promise<Array<{ id: string; name: string; description: string; status: string; current_phase: string; requirements: string; created_at: string; updated_at: string }>> {
  const params = status ? `?status=${status}` : ''
  const response = await fetch(`${API_BASE}/projects/${params}`)
  if (!response.ok) throw new Error('获取项目列表失败')
  return response.json()
}

export async function createProject(name: string, description: string, requirements: string = ''): Promise<{ id: string; name: string; status: string }> {
  const response = await fetch(`${API_BASE}/projects/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description, requirements }),
  })
  if (!response.ok) throw new Error('创建项目失败')
  return response.json()
}

export async function getProjectSummary(projectId: string): Promise<ProjectSummary> {
  const response = await fetch(`${API_BASE}/projects/${projectId}/summary`)
  if (!response.ok) throw new Error('获取项目汇总失败')
  return response.json()
}

export async function deleteProject(projectId: string, cascade: boolean = true): Promise<void> {
  const response = await fetch(`${API_BASE}/projects/${projectId}?cascade=${cascade}`, {
    method: 'DELETE',
  })
  if (!response.ok) throw new Error('删除项目失败')
}

export async function assignAgentToProject(agentId: string, projectId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/agents/${agentId}/assign`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId }),
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '分配失败' }))
    throw new Error(err.detail || 'Agent 分配失败')
  }
}

export async function releaseAgentFromProject(agentId: string, projectId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/agents/${agentId}/release`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId }),
  })
  if (!response.ok) {
    throw new Error('Agent 释放失败')
  }
}

export async function getAvailableAgents(): Promise<Array<Record<string, unknown>>> {
  const response = await fetch(`${API_BASE}/agents/?available=true`)
  if (!response.ok) throw new Error('获取可用 Agent 失败')
  const data = await response.json()
  return data.agents
}

export async function getProjectAgents(projectId: string): Promise<Array<Record<string, unknown>>> {
  const response = await fetch(`${API_BASE}/agents/?project_id=${projectId}`)
  if (!response.ok) throw new Error('获取项目 Agent 失败')
  const data = await response.json()
  return data.agents
}

export async function getAgentProject(agentId: string): Promise<{ agent_id: string; project_id: string | null; status: string }> {
  const response = await fetch(`${API_BASE}/agents/${agentId}/project`)
  if (!response.ok) throw new Error('获取 Agent 项目失败')
  return response.json()
}

// ========== Task Mutation API ==========

export async function updateTask(
  taskId: string,
  updates: { title?: string; description?: string; priority?: string; tags?: string[] },
): Promise<void> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  })
  if (!response.ok) console.warn(`更新任务失败: ${response.statusText}`)
}

export async function changeTaskStatus(
  taskId: string,
  status: string,
  changedBy: string = 'human',
): Promise<void> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}/status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status, changed_by: changedBy }),
  })
  if (!response.ok) console.warn(`变更任务状态失败: ${response.statusText}`)
}

export async function assignTaskAgents(
  taskId: string,
  agentIds: string[],
): Promise<void> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}/assign`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent_ids: agentIds }),
  })
  if (!response.ok) console.warn(`分配任务失败: ${response.statusText}`)
}

// ========== Skills API (Phase 4 学习系统) ==========

export interface SkillInfo {
  id: string
  name: string
  category: string
  success_rate: number
  usage_count: number
  trigger_keywords: string[]
  description: string
}

export interface AgentLearningStats {
  total_trajectories: number
  successful_trajectories: number
  success_rate: number
  total_skills: number
  skills_by_category: Record<string, { count: number; avg_confidence: number }>
}

export async function getAgentSkills(agentId: string): Promise<SkillInfo[]> {
  const response = await fetch(`${API_BASE}/skills/agent/${agentId}/stats`)
  if (!response.ok) throw new Error('获取技能统计失败')
  return response.json()
}

export async function recommendSkills(
  taskDescription: string,
  agentId?: string,
): Promise<Array<{ skill: SkillInfo; score: number; reason: string }>> {
  const response = await fetch(`${API_BASE}/skills/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_description: taskDescription, agent_id: agentId || null }),
  })
  if (!response.ok) throw new Error('技能推荐失败')
  return response.json()
}

// ========== Equipment API (Phase 5 装备系统) ==========

export interface ToolInfo {
  id: string
  name: string
  description: string
  tool_type: string
  cost: { cpu: number; memory: number; tokens: number }
}

export async function listTools(): Promise<ToolInfo[]> {
  const response = await fetch(`${API_BASE}/equipment/tools`)
  if (!response.ok) throw new Error('获取工具列表失败')
  const data = await response.json()
  return data.tools || data
}

export async function getAgentEquipment(agentId: string): Promise<ToolInfo[]> {
  const response = await fetch(`${API_BASE}/equipment/agent/${agentId}/equipment`)
  if (!response.ok) throw new Error('获取Agent装备失败')
  const data = await response.json()
  return data.tools || data
}

// ========== Agent Template API ==========

export interface AgentTemplate {
  id: string
  name: string
  type: string
  description: string
  capabilities: string[]
  tags: string[]
}

export async function getAgentTemplates(): Promise<AgentTemplate[]> {
  const response = await fetch(`${API_BASE}/agents/templates`)
  if (!response.ok) throw new Error('获取Agent模板失败')
  const data = await response.json()
  return data.templates || data
}

export async function getPipelineTemplates(category?: string): Promise<{
  templates: Array<{
    id: string; name: string; description: string; category: string
    suggested_strategy: string; stages: Array<Record<string, unknown>>
  }>
  categories: Array<{ key: string; label: string }>
}> {
  const params = category ? `?category=${encodeURIComponent(category)}` : ''
  const response = await fetch(`${API_BASE}/pipelines/templates${params}`)
  if (!response.ok) throw new Error('获取Pipeline模板失败')
  return response.json()
}