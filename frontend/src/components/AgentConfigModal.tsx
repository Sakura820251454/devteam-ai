import { useState, useEffect } from 'react'
import { getAvailableModels, getAvailableProviders } from '../lib/api'
import type { LLMModelInfo } from '../lib/api'
import { useStore } from '../lib/store'

interface SoulAgent {
  id: string
  name: string
  type: string
  description: string
  avatar_color: string
  capabilities: string[]
  status: string
  is_active: boolean
  source: string
  soul_data?: {
    name: string
    core_principles: string[]
    execution_rules: string[]
    role_definitions?: Record<string, unknown>
  }
  llm_config?: { provider: string; model: string; temperature: number; max_tokens?: number }
}

interface AgentConfigModalProps {
  isOpen: boolean
  onClose: () => void
  onAgentsConfigured: (agents: SoulAgent[], options: TeamConfig) => void
}

interface TeamConfig {
  strategy: 'sequential' | 'hierarchical' | 'discussion' | 'auto'
  coordinatorId?: string
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
  devops: '#06B6D4',
  custom: '#6B7280',
}

const STRATEGY_OPTIONS = [
  {
    id: 'sequential',
    label: '顺序执行',
    desc: '1-2 个 Agent 按序执行，无需分工',
    icon: '📋',
    example: '例：写 CSV 导出脚本、查知识概念、修 Bug',
  },
  {
    id: 'hierarchical',
    label: '层级委派',
    desc: '统筹 Agent 拆解委派 + 工人执行 + 统筹合并',
    icon: '🏗️',
    example: '例：SaaS 平台开发、微服务系统重构',
  },
  {
    id: 'discussion',
    label: '圆桌讨论',
    desc: 'Agent 集体讨论 → 达成共识 → 按结论执行',
    icon: '💬',
    example: '例：技术选型、架构方案评审',
  },
  {
    id: 'auto',
    label: '智能推荐',
    desc: 'LLM 根据需求自动选择最合适的策略',
    icon: '🤖',
    example: '不确定时选这个，需求分析后给出推荐',
  },
]

const MOCK_SOUL_AGENTS: SoulAgent[] = [
  {
    id: 'soul_xiaoli', name: '小莉', type: 'custom', description: '动手解决，不空谈。遇到问题先试，失败再换方法。', avatar_color: '#3fb950', capabilities: ['自动化脚本', 'Bug修复', '代码实现'], status: 'idle', is_active: true, source: 'soul',
    soul_data: { name: 'xiaoli', core_principles: ['动手解决，不空谈', '简洁直接', '用数据说话'], execution_rules: ['能自动化的绝不手动', '写代码前先理解需求', '代码写完自测一遍'] },
  },
  {
    id: 'soul_xiaochen', name: '小陈', type: 'custom', description: '慢就是快，前期多花时间思考，节省后期维护成本。', avatar_color: '#a371f7', capabilities: ['架构设计', '技术选型', '代码评审'], status: 'idle', is_active: true, source: 'soul',
    soul_data: { name: 'xiaochen', core_principles: ['架构是演进出来的', '慢就是快', '技术债务是真实债务'], execution_rules: ['关键决策要权衡利弊', '问为什么比问怎么做更重要', '边界情况在设计阶段就考虑'] },
  },
  {
    id: 'soul_xiaoliu', name: '小刘', type: 'custom', description: '质量是底线，没有"差不多"，只有"合格"和"不合格"。', avatar_color: '#f85149', capabilities: ['测试用例设计', '功能测试', '缺陷跟踪'], status: 'idle', is_active: true, source: 'soul',
    soul_data: { name: 'xiaoliu', core_principles: ['质量是底线', '测试是开发的伙伴', '预防胜于治疗'], execution_rules: ['需求阶段就参与', '覆盖正常、边界、异常三种场景', 'Bug报告包含复现步骤'] },
  },
  {
    id: 'soul_xiaozhang', name: '小张', type: 'custom', description: '用户体验至上，每一个功能都要从用户角度思考。', avatar_color: '#f0883e', capabilities: ['前端开发', 'UI/UX设计', '组件开发'], status: 'idle', is_active: true, source: 'soul',
    soul_data: { name: 'xiaozhang', core_principles: ['用户体验至上', '代码即艺术', '保持好奇'], execution_rules: ['从用户需求出发', '接口设计先于实现', '完成后自己先体验几遍'] },
  },
  {
    id: 'soul_xiaozhao', name: '小赵', type: 'custom', description: '稳定压倒一切，在稳定和效率之间优先选择稳定。', avatar_color: '#39d2c0', capabilities: ['CI/CD', '容器化部署', '监控告警'], status: 'idle', is_active: true, source: 'soul',
    soul_data: { name: 'xiaozhao', core_principles: ['一次折腾长期受益', '稳定压倒一切', '监控先行'], execution_rules: ['改动要有回滚方案', '写脚本解决重复问题', '部署前检查依赖环境配置'] },
  },
  {
    id: 'soul_xiaowang', name: '小王', type: 'custom', description: '解决实际问题，而不是描述解决方案。', avatar_color: '#58a6ff', capabilities: ['需求分析', '任务拆解', '进度协调'], status: 'idle', is_active: true, source: 'soul',
    soul_data: { name: 'xiaowang', core_principles: ['解决实际问题', '保持简洁', '把用户的信任当作最宝贵的资产'], execution_rules: ['单步任务立即执行', '多步任务先列计划再执行', '写代码前先读代码'] },
  },
]

function getRoleLabel(type: string): string {
  const roleMap: Record<string, string> = {
    product_manager: '产品经理',
    architect: '架构师',
    backend_developer: '后端开发',
    frontend_developer: '前端开发',
    tester: '测试工程师',
    devops: '运维工程师',
    custom: '通用型',
  }
  return roleMap[type] || type
}

export default function AgentConfigModal({ isOpen, onClose, onAgentsConfigured }: AgentConfigModalProps) {
  const { globalLlmConfig } = useStore()
  const [agents, setAgents] = useState<SoulAgent[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [teamConfig, setTeamConfig] = useState<TeamConfig>({
    strategy: 'auto',
  })
  const [loading, setLoading] = useState(false)
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null)

  // LLM config per agent
  const [agentLlmConfigs, setAgentLlmConfigs] = useState<Record<string, { provider: string; model: string; temperature: number; max_tokens?: number }>>({})
  const [expandedLlmAgent, setExpandedLlmAgent] = useState<string | null>(null)
  const [availableProviders, setAvailableProviders] = useState<string[]>([])
  const [availableModels, setAvailableModels] = useState<Record<string, LLMModelInfo>>({})

  useEffect(() => {
    if (isOpen) {
      setSelectedIds(new Set())
      setTeamConfig({ strategy: 'auto' })
      setExpandedAgent(null)
      setAgentLlmConfigs({})
      setExpandedLlmAgent(null)
      fetchAgents()
      loadLLMData()
    }
  }, [isOpen])

  const fetchAgents = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/agents/soul-based')
      if (response.ok) {
        const data = await response.json()
        const list = data.agents || []
        if (list.length > 0) {
          setAgents(list)
        } else {
          setAgents(MOCK_SOUL_AGENTS)
        }
      } else {
        setAgents(MOCK_SOUL_AGENTS)
      }
    } catch {
      setAgents(MOCK_SOUL_AGENTS)
    } finally {
      setLoading(false)
    }
  }

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

  const toggleAgent = (id: string) => {
    const agent = agents.find(a => a.id === id)
    if (agent && agent.status !== 'idle' && !selectedIds.has(id)) return

    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
      // Clean up coordinator if removed
      if (teamConfig.coordinatorId === id) {
        setTeamConfig(prev => ({ ...prev, coordinatorId: undefined }))
      }
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  const getAgentById = (id: string) => agents.find(a => a.id === id)

  const handleConfirm = () => {
    const selectedAgents = agents
      .filter(a => selectedIds.has(a.id))
      .map(a => ({
        ...a,
        llm_config: agentLlmConfigs[a.id] || undefined,
      }))

    const config: TeamConfig = { ...teamConfig }
    if (config.strategy !== 'hierarchical') {
      delete config.coordinatorId
    }

    onAgentsConfigured(selectedAgents, config)
    onClose()
  }

  // Compute summary
  const selectedAgentsList = Array.from(selectedIds).map(id => getAgentById(id)).filter(Boolean) as SoulAgent[]
  const strategyInfo = STRATEGY_OPTIONS.find(s => s.id === teamConfig.strategy)

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-xl w-[900px] max-h-[85vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-700 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white">配置 Agent 团队</h2>
            <p className="text-sm text-gray-400 mt-1">
              从 soul.md 定义的 Agent 池中选择团队成员
              <span className="ml-2 text-xs bg-purple-500/20 text-purple-400 px-2 py-0.5 rounded">
                soul-based
              </span>
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">&times;</button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Agent selection */}
          <section>
            <h3 className="text-sm font-medium text-gray-400 mb-3">
              选择团队成员
              {loading && <span className="ml-2 text-xs text-gray-500">加载中...</span>}
              {!loading && <span className="ml-2 text-xs text-gray-500">({agents.length} 位可用)</span>}
            </h3>

            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-3">
                {agents.map((agent) => {
                  const isSelected = selectedIds.has(agent.id)
                  const isUnavailable = agent.status !== 'idle'
                  const isExpanded = expandedAgent === agent.id

                  return (
                    <div
                      key={agent.id}
                      className={`rounded-lg border transition-all ${
                        isUnavailable
                          ? 'border-gray-700 bg-gray-700/30 opacity-50'
                          : isSelected
                            ? 'border-primary-500 bg-primary-500/20 ring-1 ring-primary-500'
                            : 'border-gray-600 bg-gray-700/50 hover:border-gray-500'
                      }`}
                    >
                      <div
                        className="p-4 cursor-pointer"
                        onClick={() => {
                          if (!isUnavailable || isSelected) toggleAgent(agent.id)
                        }}
                      >
                        <div className="flex items-start gap-3">
                          <div
                            className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold shrink-0"
                            style={{ backgroundColor: agent.avatar_color || TYPE_COLORS.custom }}
                          >
                            {isSelected ? '✓' : agent.name.substring(0, 1)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between">
                              <div>
                                <span className="font-medium text-white text-sm">{agent.name}</span>
                                <span className="text-xs text-gray-400 ml-1.5">
                                  {getRoleLabel(agent.type)}
                                </span>
                              </div>
                              {isUnavailable && (
                                <span className="text-xs bg-gray-600 text-gray-300 px-1.5 py-0.5 rounded">
                                  忙碌中
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-gray-400 mt-1 line-clamp-2">{agent.description}</p>
                            <div className="flex flex-wrap gap-1 mt-2">
                              {agent.capabilities.slice(0, 3).map(c => (
                                <span key={c} className="text-xs bg-gray-600/50 text-gray-300 px-1.5 py-0.5 rounded">
                                  {c}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Soul details expander */}
                      {agent.soul_data && agent.status === 'idle' && (
                        <div className="px-4 pb-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              setExpandedAgent(isExpanded ? null : agent.id)
                            }}
                            className="text-xs text-primary-400 hover:text-primary-300"
                          >
                            {isExpanded ? '收起行为准则' : '查看行为准则'}
                          </button>
                          {isExpanded && (
                            <div className="mt-2 text-xs space-y-2">
                              {agent.soul_data.core_principles && agent.soul_data.core_principles.length > 0 && (
                                <div>
                                  <h4 className="text-gray-400 font-medium mb-1">核心原则</h4>
                                  <ul className="space-y-0.5">
                                    {agent.soul_data.core_principles.slice(0, 3).map((p, i) => (
                                      <li key={i} className="text-gray-300">· {p}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              {agent.soul_data.execution_rules && agent.soul_data.execution_rules.length > 0 && (
                                <div>
                                  <h4 className="text-gray-400 font-medium mb-1">执行规则</h4>
                                  <ul className="space-y-0.5">
                                    {agent.soul_data.execution_rules.slice(0, 3).map((r, i) => (
                                      <li key={i} className="text-gray-300">· {r}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Per-agent LLM config */}
                      {isSelected && (
                        <div className="px-4 pb-3 border-t border-gray-600 pt-2" onClick={(e) => e.stopPropagation()}>
                          {getEffectiveLlmConfig(agent.id) ? (
                            <div className="flex items-center justify-between">
                              <span className="text-xs text-primary-300 font-mono">
                                {getEffectiveLlmConfig(agent.id)!.model}
                              </span>
                              <div className="flex gap-1">
                                <button
                                  onClick={() => setExpandedLlmAgent(expandedLlmAgent === agent.id ? null : agent.id)}
                                  className="text-xs text-gray-400 hover:text-gray-300 px-2 py-0.5 rounded"
                                >
                                  {expandedLlmAgent === agent.id ? '收起' : '修改'}
                                </button>
                                <button
                                  onClick={() => clearAgentLlmConfig(agent.id)}
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
                                setAgentLlmConfig(agent.id, defaultCfg)
                                setExpandedLlmAgent(agent.id)
                              }}
                              className="w-full text-xs text-gray-400 hover:text-primary-400 py-1 rounded transition-colors"
                            >
                              + 自定义 LLM（默认: {globalLlmConfig.model}）
                            </button>
                          )}

                          {expandedLlmAgent === agent.id && getEffectiveLlmConfig(agent.id) && (() => {
                            const cfg = getEffectiveLlmConfig(agent.id)!
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
                                      setAgentLlmConfig(agent.id, { ...cfg, provider: newProvider, model: newModel })
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
                                    onChange={(e) => setAgentLlmConfig(agent.id, { ...cfg, model: e.target.value })}
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
                                    type="range" min="0" max="2" step="0.1"
                                    value={cfg.temperature}
                                    onChange={(e) => setAgentLlmConfig(agent.id, { ...cfg, temperature: parseFloat(e.target.value) })}
                                    className="w-full accent-primary-500"
                                  />
                                </div>
                                <div>
                                  <label className="block text-xs text-gray-400 mb-1">Max Tokens（可选）</label>
                                  <input
                                    type="number"
                                    value={cfg.max_tokens || ''}
                                    onChange={(e) => setAgentLlmConfig(agent.id, { ...cfg, max_tokens: e.target.value ? parseInt(e.target.value) : undefined })}
                                    placeholder="模型默认"
                                    className="w-full bg-gray-600 border border-gray-500 rounded px-2 py-1 text-xs text-gray-200 placeholder:text-gray-500 focus:outline-none focus:border-primary-500"
                                  />
                                </div>
                              </div>
                            )
                          })()}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </section>

          {/* Strategy selection */}
          <section>
            <h3 className="text-sm font-medium text-gray-400 mb-3">协调策略</h3>
            <div className="grid grid-cols-4 gap-3">
              {STRATEGY_OPTIONS.map((strategy) => {
                const isActive = teamConfig.strategy === strategy.id
                return (
                  <button
                    key={strategy.id}
                    onClick={() => setTeamConfig(prev => ({ ...prev, strategy: strategy.id as TeamConfig['strategy'] }))}
                    className={`p-4 rounded-lg border text-left transition-all ${
                      isActive
                        ? 'border-primary-500 bg-primary-500/20 ring-1 ring-primary-500'
                        : 'border-gray-600 bg-gray-700/50 hover:border-gray-500'
                    }`}
                  >
                    <div className="text-2xl mb-1">{strategy.icon}</div>
                    <div className="font-medium text-white text-sm">{strategy.label}</div>
                    <div className="text-xs text-gray-400 mt-1">{strategy.desc}</div>
                    <div className="text-xs text-gray-500 mt-2 leading-relaxed">{strategy.example}</div>
                  </button>
                )
              })}
            </div>

            {/* Coordinator selector for hierarchical */}
            {teamConfig.strategy === 'hierarchical' && selectedAgentsList.length > 1 && (
              <div className="mt-3 p-3 bg-gray-700/30 rounded-lg">
                <label className="block text-xs text-gray-400 mb-2">指定统筹 Agent（负责任务拆解、委派和成果集成）</label>
                <div className="flex flex-wrap gap-2">
                  {selectedAgentsList.map(agent => (
                    <button
                      key={agent.id}
                      onClick={() => setTeamConfig(prev => ({ ...prev, coordinatorId: agent.id }))}
                      className={`px-3 py-1.5 rounded-full text-xs transition-colors ${
                        teamConfig.coordinatorId === agent.id
                          ? 'bg-primary-500 text-white'
                          : 'bg-gray-600 text-gray-300 hover:bg-gray-500'
                      }`}
                    >
                      {agent.name}
                    </button>
                  ))}
                </div>
                {!teamConfig.coordinatorId && (
                  <p className="text-xs text-amber-400 mt-2">请选择一个统筹 Agent（建议选择有统筹经验的成员）</p>
                )}
              </div>
            )}
          </section>

          {/* Team summary */}
          <section className="bg-gray-700/30 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-white">团队概览</h3>
                <p className="text-xs text-gray-400 mt-1">
                  {selectedIds.size === 0
                    ? '请选择至少 1 位团队成员'
                    : `已选 ${selectedIds.size} 位 · 策略: ${strategyInfo?.label || '—'}@${teamConfig.strategy === 'hierarchical' && teamConfig.coordinatorId ? getAgentById(teamConfig.coordinatorId)?.name || '未指定' : '—'}`
                  }
                </p>
              </div>
            </div>

            {selectedAgentsList.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-gray-600">
                {selectedAgentsList.map(agent => (
                  <span
                    key={agent.id}
                    className="text-xs px-2 py-1 rounded-full flex items-center gap-1"
                    style={{ backgroundColor: `${agent.avatar_color || TYPE_COLORS.custom}30`, color: agent.avatar_color || TYPE_COLORS.custom }}
                  >
                    {agent.name}
                    {teamConfig.coordinatorId === agent.id && (
                      <span className="text-white/70 ml-0.5">(统筹)</span>
                    )}
                    <button
                      onClick={() => toggleAgent(agent.id)}
                      className="ml-1 hover:opacity-70"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}

            {teamConfig.strategy === 'auto' && selectedAgentsList.length > 1 && (
              <div className="mt-3 p-2 bg-primary-500/10 rounded border border-primary-500/30">
                <p className="text-xs text-primary-300">
                  智能推荐模式：LLM 将在需求分析后给出推荐策略和理由，届时可手动调整
                </p>
              </div>
            )}

            {teamConfig.strategy === 'discussion' && selectedAgentsList.length > 1 && (
              <div className="mt-3 p-2 bg-amber-500/10 rounded border border-amber-500/30">
                <p className="text-xs text-amber-300">
                  圆桌讨论模式：Agent 将在公共区讨论，通过 MessageBus 发布-订阅机制各取所需，Arbitrator 在出现分歧时介入仲裁
                </p>
              </div>
            )}
          </section>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-700 flex justify-between items-center">
          <div className="text-sm text-gray-400">
            {selectedIds.size === 0
              ? '最少需要 1 位团队成员'
              : `${selectedIds.size} 位成员已就绪`
            }
            {teamConfig.strategy === 'hierarchical' && selectedIds.size > 0 && !teamConfig.coordinatorId && (
              <span className="text-amber-400 ml-2">（还需指定统筹 Agent）</span>
            )}
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
              disabled={selectedIds.size === 0 || (teamConfig.strategy === 'hierarchical' && !teamConfig.coordinatorId)}
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
