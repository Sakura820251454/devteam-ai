export interface Agent {
  id: string
  name: string
  personality: string
  baseRole: string
  avatar_color: string
  avatar_emoji: string
  strengths: string[]
  workHistory: string[]
  isBusy: boolean
  currentProject?: string
  llm_config?: LLMConfig
}

export interface LLMProviderType {
  OPENAI: 'openai'
  DEEPSEEK: 'deepseek'
  ANTHROPIC: 'anthropic'
  AZURE: 'azure'
  MOCK: 'mock'
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

export interface CostSummary {
  total_cost: number
  total_tokens: number
  prompt_tokens: number
  completion_tokens: number
  call_count: number
  by_model: Record<string, { cost: number; tokens: number; calls: number }>
  by_agent: Record<string, { cost: number; tokens: number; calls: number }>
}

export interface Task {
  id: string
  name: string
  description: string
  status: 'planning' | 'executing' | 'completed'
}

export interface AgentAssignment {
  agentId: string
  tempRole: string
  tempDescription: string
}

export interface TeamSession {
  id: string
  task: Task
  assignments: AgentAssignment[]
  createdAt: Date
  completedAt?: Date
}