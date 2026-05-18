import { useState, useEffect } from 'react'
import { getAvailableModels, getAvailableProviders } from '../lib/api'
import type { LLMModelInfo } from '../lib/api'
import { useStore } from '../lib/store'

interface AgentTemplate {
  id: string
  name: string
  type: string
  description: string
  avatar_color: string
  system_prompt: string
  capabilities: string[]
  collaboration_style: string
  speaking_tendency: string
  tags: string[]
  is_preset: boolean
  suitable_scenarios: string[]
  llm_config?: { provider: string; model: string; temperature: number; max_tokens?: number }
}

interface AgentConfigModalProps {
  isOpen: boolean
  onClose: () => void
  onAgentsConfigured: (agents: AgentTemplate[], options: TeamConfig) => void
}

interface TeamConfig {
  mode: 'auto' | 'sequential' | 'parallel'
  complexity: 'simple' | 'medium' | 'complex'
}

const PROVIDER_LABELS: Record<string, string> = {
  openai: 'OpenAI',
  deepseek: 'DeepSeek',
  anthropic: 'Anthropic Claude',
  azure: 'Azure OpenAI',
  mock: 'Mock（测试用）',
}

const TYPE_COLORS: Record<string, string> = {
  product_manager: '#3B82F6',
  architect: '#8B5CF6',
  backend_developer: '#10B981',
  frontend_developer: '#F59E0B',
  tester: '#EF4444',
  devops: '#06B6D4'
}

const PRESET_ROLES: AgentTemplate[] = [
  {
    id: 'pm_default',
    name: '产品经理',
    type: 'product_manager',
    description: '负责需求分析、产品规划和任务拆解',
    avatar_color: '#3B82F6',
    system_prompt: '你是一位专业的产品经理，擅长将用户需求转化为可执行的任务。',
    capabilities: ['需求分析', '任务拆解', '进度跟踪'],
    collaboration_style: '主动型',
    speaking_tendency: '简洁型',
    tags: ['产品', '需求', '规划'],
    is_preset: true,
    suitable_scenarios: ['需求讨论', '任务规划']
  },
  {
    id: 'architect_default',
    name: '架构师',
    type: 'architect',
    description: '负责系统架构设计和技术选型',
    avatar_color: '#8B5CF6',
    system_prompt: '你是一位经验丰富的系统架构师，擅长设计可扩展的系统架构。',
    capabilities: ['架构设计', '技术选型', '代码评审'],
    collaboration_style: '分析型',
    speaking_tendency: '详细型',
    tags: ['架构', '设计', '技术'],
    is_preset: true,
    suitable_scenarios: ['架构设计', '技术讨论']
  },
  {
    id: 'backend_default',
    name: '后端开发',
    type: 'backend_developer',
    description: '负责后端服务开发和 API 设计',
    avatar_color: '#10B981',
    system_prompt: '你是一位资深后端开发工程师，擅长构建高效可靠的服务器端应用。',
    capabilities: ['API开发', '数据库设计', '业务逻辑'],
    collaboration_style: '务实型',
    speaking_tendency: '简洁型',
    tags: ['后端', 'API', '数据库'],
    is_preset: true,
    suitable_scenarios: ['后端开发', 'API设计']
  },
  {
    id: 'frontend_default',
    name: '前端开发',
    type: 'frontend_developer',
    description: '负责前端界面开发和用户体验优化',
    avatar_color: '#F59E0B',
    system_prompt: '你是一位专业的前端开发工程师，擅长创建美观且交互良好的用户界面。',
    capabilities: ['页面开发', '组件设计', '交互实现'],
    collaboration_style: '细节型',
    speaking_tendency: '详细型',
    tags: ['前端', 'UI', '交互'],
    is_preset: true,
    suitable_scenarios: ['前端开发', 'UI评审']
  },
  {
    id: 'tester_default',
    name: '测试工程师',
    type: 'tester',
    description: '负责质量保障和测试用例设计',
    avatar_color: '#EF4444',
    system_prompt: '你是一位专业的测试工程师，致力于确保产品质量和稳定性。',
    capabilities: ['测试用例', '功能测试', '缺陷跟踪'],
    collaboration_style: '严谨型',
    speaking_tendency: '简洁型',
    tags: ['测试', '质量', 'QA'],
    is_preset: true,
    suitable_scenarios: ['测试讨论', 'Bug评审']
  },
  {
    id: 'devops_default',
    name: '运维工程师',
    type: 'devops',
    description: '负责 DevOps、CI/CD 和部署运维',
    avatar_color: '#06B6D4',
    system_prompt: '你是一位专业的运维/DevOps工程师，擅长自动化部署和系统运维。',
    capabilities: ['CI/CD', '容器化', '监控告警'],
    collaboration_style: '稳妥型',
    speaking_tendency: '简洁型',
    tags: ['运维', 'DevOps', '部署'],
    is_preset: true,
    suitable_scenarios: ['部署讨论', '运维规划']
  }
]

const ROLE_RECOMMENDATIONS: Record<string, string[]> = {
  '需求分析': ['pm_default'],
  'API开发': ['backend_default'],
  '全栈开发': ['backend_default', 'frontend_default'],
  '完整项目': ['pm_default', 'architect_default', 'backend_default', 'frontend_default', 'tester_default'],
  '简单任务': ['backend_default'],
  '复杂系统': ['architect_default', 'backend_default', 'tester_default', 'devops_default']
}

export default function AgentConfigModal({ isOpen, onClose, onAgentsConfigured }: AgentConfigModalProps) {
  const { globalLlmConfig } = useStore()
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [teamConfig, setTeamConfig] = useState<TeamConfig>({
    mode: 'auto',
    complexity: 'simple'
  })
  const [showRecommendations, setShowRecommendations] = useState(false)

  // LLM config per agent: agentId -> { provider, model, temperature, max_tokens? }
  const [agentLlmConfigs, setAgentLlmConfigs] = useState<Record<string, { provider: string; model: string; temperature: number; max_tokens?: number }>>({})
  const [expandedLlmAgent, setExpandedLlmAgent] = useState<string | null>(null)
  const [availableProviders, setAvailableProviders] = useState<string[]>([])
  const [availableModels, setAvailableModels] = useState<Record<string, LLMModelInfo>>({})

  useEffect(() => {
    if (isOpen) {
      setSelectedIds(new Set())
      setTeamConfig({ mode: 'auto', complexity: 'simple' })
      setShowRecommendations(false)
      setAgentLlmConfigs({})
      setExpandedLlmAgent(null)
      loadLLMData()
    }
  }, [isOpen])

  const loadLLMData = async () => {
    try {
      const [providers, models] = await Promise.all([
        getAvailableProviders(),
        getAvailableModels(),
      ])
      setAvailableProviders(providers)
      setAvailableModels(models)
    } catch {
      setAvailableProviders(['openai', 'deepseek', 'anthropic', 'azure', 'mock'])
    }
  }

  const getEffectiveLlmConfig = (agentId: string) => {
    return agentLlmConfigs[agentId] || null
  }

  const setAgentLlmConfig = (agentId: string, config: { provider: string; model: string; temperature: number; max_tokens?: number }) => {
    setAgentLlmConfigs((prev) => ({ ...prev, [agentId]: config }))
  }

  const clearAgentLlmConfig = (agentId: string) => {
    setAgentLlmConfigs((prev) => {
      const next = { ...prev }
      delete next[agentId]
      return next
    })
  }

  const toggleRole = (id: string) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  const applyRecommendation = (key: string) => {
    const roleIds = ROLE_RECOMMENDATIONS[key] || []
    setSelectedIds(new Set(roleIds))
    setShowRecommendations(false)
  }

  const estimateCost = () => {
    const baseTokens = 1000
    const perAgentTokens = 500
    const selectedCount = selectedIds.size
    
    let modeMultiplier = 1
    if (teamConfig.mode === 'sequential') modeMultiplier = 1.2
    if (teamConfig.mode === 'parallel') modeMultiplier = selectedCount * 0.6

    return Math.round(baseTokens + (perAgentTokens * selectedCount * modeMultiplier))
  }

  const getComplexityLabel = () => {
    const count = selectedIds.size
    if (count <= 1) return '极简'
    if (count <= 2) return '简单'
    if (count <= 3) return '中等'
    return '复杂'
  }

  const handleConfirm = () => {
    const selectedAgents = PRESET_ROLES
      .filter(r => selectedIds.has(r.id))
      .map(r => ({
        ...r,
        llm_config: agentLlmConfigs[r.id] || undefined,
      }))
    onAgentsConfigured(selectedAgents, teamConfig)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-xl w-[850px] max-h-[85vh] overflow-hidden flex flex-col">
        <div className="px-6 py-4 border-b border-gray-700 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white">配置 Agent 团队</h2>
            <p className="text-sm text-gray-400 mt-1">选择角色组建团队，Agent 将自动讨论分工协作</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">&times;</button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <section>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-gray-400">选择角色</h3>
              <button
                onClick={() => setShowRecommendations(!showRecommendations)}
                className="text-xs text-primary-400 hover:text-primary-300"
              >
                {showRecommendations ? '收起推荐' : '查看推荐组合'}
              </button>
            </div>

            {showRecommendations && (
              <div className="bg-gray-700/30 rounded-lg p-3 mb-4">
                <p className="text-xs text-gray-400 mb-2">快速选择适合你需求的角色组合：</p>
                <div className="flex flex-wrap gap-2">
                  {Object.keys(ROLE_RECOMMENDATIONS).map(key => (
                    <button
                      key={key}
                      onClick={() => applyRecommendation(key)}
                      className="text-xs px-3 py-1.5 rounded-full bg-gray-600 hover:bg-gray-500 text-gray-200 transition-colors"
                    >
                      {key} ({ROLE_RECOMMENDATIONS[key].length}人)
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="grid grid-cols-3 gap-3">
              {PRESET_ROLES.map((role) => {
                const isSelected = selectedIds.has(role.id)
                return (
                  <button
                    key={role.id}
                    onClick={() => toggleRole(role.id)}
                    className={`p-4 rounded-lg border text-left transition-all ${
                      isSelected
                        ? 'border-primary-500 bg-primary-500/20 ring-1 ring-primary-500'
                        : 'border-gray-600 bg-gray-700/50 hover:border-gray-500'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold flex-shrink-0"
                        style={{ backgroundColor: TYPE_COLORS[role.type] }}
                      >
                        {isSelected ? '✓' : role.name.substring(0, 1)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-white">{role.name}</div>
                        <div className="text-xs text-gray-400 truncate">{role.description}</div>
                      </div>
                    </div>
                    {/* Per-agent LLM config expander */}
                    {isSelected && (
                      <div className="mt-3 pt-3 border-t border-gray-600" onClick={(e) => e.stopPropagation()}>
                        {getEffectiveLlmConfig(role.id) ? (
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-primary-300 font-mono">
                              {getEffectiveLlmConfig(role.id)!.model}
                            </span>
                            <div className="flex gap-1">
                              <button
                                onClick={() => setExpandedLlmAgent(expandedLlmAgent === role.id ? null : role.id)}
                                className="text-xs text-gray-400 hover:text-gray-300 px-2 py-0.5 rounded"
                              >
                                {expandedLlmAgent === role.id ? '收起' : '修改'}
                              </button>
                              <button
                                onClick={() => clearAgentLlmConfig(role.id)}
                                className="text-xs text-gray-400 hover:text-red-400 px-2 py-0.5 rounded"
                              >
                                重置
                              </button>
                            </div>
                          </div>
                        ) : (
                          <button
                            onClick={() => {
                              const defaultCfg = {
                                provider: globalLlmConfig.provider,
                                model: globalLlmConfig.model,
                                temperature: globalLlmConfig.temperature,
                                max_tokens: globalLlmConfig.max_tokens,
                              }
                              setAgentLlmConfig(role.id, defaultCfg)
                              setExpandedLlmAgent(role.id)
                            }}
                            className="w-full text-xs text-gray-400 hover:text-primary-400 py-1 rounded transition-colors"
                          >
                            + 自定义 LLM（默认: {globalLlmConfig.model}）
                          </button>
                        )}
                        {/* Expanded LLM config form */}
                        {expandedLlmAgent === role.id && getEffectiveLlmConfig(role.id) && (() => {
                          const cfg = getEffectiveLlmConfig(role.id)!
                          const filteredModels = Object.entries(availableModels).filter(([, info]) => info.provider === cfg.provider)
                          return (
                            <div className="mt-2 space-y-2 bg-gray-700/50 rounded-lg p-3">
                              <div>
                                <label className="block text-xs text-gray-400 mb-1">Provider</label>
                                <select
                                  value={cfg.provider}
                                  onChange={(e) => {
                                    const newProvider = e.target.value
                                    const modelsForProvider = Object.entries(availableModels).filter(([, info]) => info.provider === newProvider)
                                    const newModel = modelsForProvider.length > 0 ? modelsForProvider[0][0] : cfg.model
                                    setAgentLlmConfig(role.id, { ...cfg, provider: newProvider, model: newModel })
                                  }}
                                  className="w-full bg-gray-600 border border-gray-500 rounded px-2 py-1 text-xs text-gray-200 focus:outline-none focus:border-primary-500"
                                >
                                  {availableProviders.map((p) => (
                                    <option key={p} value={p}>{PROVIDER_LABELS[p] || p}</option>
                                  ))}
                                </select>
                              </div>
                              <div>
                                <label className="block text-xs text-gray-400 mb-1">Model</label>
                                <select
                                  value={cfg.model}
                                  onChange={(e) => setAgentLlmConfig(role.id, { ...cfg, model: e.target.value })}
                                  className="w-full bg-gray-600 border border-gray-500 rounded px-2 py-1 text-xs text-gray-200 focus:outline-none focus:border-primary-500"
                                >
                                  {filteredModels.map(([name, info]) => (
                                    <option key={name} value={name}>{name} — {info.description}</option>
                                  ))}
                                  {filteredModels.length === 0 && (
                                    <option value={cfg.model}>{cfg.model}</option>
                                  )}
                                </select>
                              </div>
                              <div>
                                <label className="block text-xs text-gray-400 mb-1">Temperature: {cfg.temperature.toFixed(1)}</label>
                                <input
                                  type="range"
                                  min="0"
                                  max="2"
                                  step="0.1"
                                  value={cfg.temperature}
                                  onChange={(e) => setAgentLlmConfig(role.id, { ...cfg, temperature: parseFloat(e.target.value) })}
                                  className="w-full accent-primary-500"
                                />
                              </div>
                              <div>
                                <label className="block text-xs text-gray-400 mb-1">Max Tokens（可选）</label>
                                <input
                                  type="number"
                                  value={cfg.max_tokens || ''}
                                  onChange={(e) => setAgentLlmConfig(role.id, { ...cfg, max_tokens: e.target.value ? parseInt(e.target.value) : undefined })}
                                  placeholder="模型默认"
                                  className="w-full bg-gray-600 border border-gray-500 rounded px-2 py-1 text-xs text-gray-200 placeholder:text-gray-500 focus:outline-none focus:border-primary-500"
                                />
                              </div>
                            </div>
                          )
                        })()}
                      </div>
                    )}
                  </button>
                )
              })}
            </div>
          </section>

          <section>
            <h3 className="text-sm font-medium text-gray-400 mb-3">协作模式</h3>
            <div className="grid grid-cols-3 gap-3">
              {[
                { id: 'auto', label: '智能协商', desc: 'Agent 自主讨论分工', icon: '🤖' },
                { id: 'sequential', label: '顺序执行', desc: '按选择顺序依次工作', icon: '📋' },
                { id: 'parallel', label: '并行执行', desc: '同时工作最后合并', icon: '⚡' }
              ].map((mode) => (
                <button
                  key={mode.id}
                  onClick={() => setTeamConfig(prev => ({ ...prev, mode: mode.id as TeamConfig['mode'] }))}
                  className={`p-4 rounded-lg border text-left transition-all ${
                    teamConfig.mode === mode.id
                      ? 'border-primary-500 bg-primary-500/20'
                      : 'border-gray-600 bg-gray-700/50 hover:border-gray-500'
                  }`}
                >
                  <div className="text-2xl mb-1">{mode.icon}</div>
                  <div className="font-medium text-white">{mode.label}</div>
                  <div className="text-xs text-gray-400 mt-1">{mode.desc}</div>
                </button>
              ))}
            </div>
          </section>

          <section className="bg-gray-700/30 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-white">团队概览</h3>
                <p className="text-xs text-gray-400 mt-1">
                  {selectedIds.size === 0 
                    ? '请选择至少一个角色' 
                    : `已选择 ${selectedIds.size} 个 Agent · 复杂度: ${getComplexityLabel()}`}
                </p>
              </div>
              <div className="text-right">
                <div className="text-xs text-gray-400">预估 Token 消耗</div>
                <div className="text-lg font-bold text-primary-400">~{estimateCost()}</div>
              </div>
            </div>

            {selectedIds.size > 0 && (
              <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-gray-600">
                {Array.from(selectedIds).map(id => {
                  const role = PRESET_ROLES.find(r => r.id === id)
                  if (!role) return null
                  return (
                    <span
                      key={id}
                      className="text-xs px-2 py-1 rounded-full flex items-center gap-1"
                      style={{ backgroundColor: `${TYPE_COLORS[role.type]}30`, color: TYPE_COLORS[role.type] }}
                    >
                      {role.name}
                      <button
                        onClick={() => toggleRole(id)}
                        className="ml-1 hover:opacity-70"
                      >
                        ×
                      </button>
                    </span>
                  )
                })}
              </div>
            )}

            {teamConfig.mode === 'auto' && selectedIds.size > 1 && (
              <div className="mt-3 p-2 bg-primary-500/10 rounded border border-primary-500/30">
                <p className="text-xs text-primary-300">
                  💡 智能协商模式：选定的 Agent 会在讨论中自主确定分工，无需预设执行顺序
                </p>
              </div>
            )}
          </section>
        </div>

        <div className="px-6 py-4 border-t border-gray-700 flex justify-between items-center">
          <div className="text-sm text-gray-400">
            {selectedIds.size === 0 
              ? '最少需要 1 个 Agent' 
              : `${selectedIds.size} 个 Agent 已就绪`}
          </div>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-300 hover:text-white transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleConfirm}
              disabled={selectedIds.size === 0}
              className="px-6 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
            >
              创建团队 ({selectedIds.size})
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
