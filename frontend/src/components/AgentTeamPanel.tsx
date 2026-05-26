import { useState, useRef, useEffect } from 'react'
import { useStore } from '../lib/store'
import type { Agent } from '../lib/store'
import { startSimulation } from '../lib/simulation'
import { getAvailableModels, getAvailableProviders, assignAgentToProject, releaseAgentFromProject, getAvailableAgents } from '../lib/api'
import type { LLMModelInfo } from '../lib/api'
import AgentPoolModal from './AgentPoolModal'


const STATUS_LABELS: Record<string, string> = {
  idle: '空闲',
  thinking: '思考中',
  working: '工作中',
  waiting: '等待中',
  blocked: '阻塞',
}

const STATUS_STYLES: Record<string, string> = {
  idle: 'bg-surface-400',
  thinking: 'bg-accent-purple animate-pulse',
  working: 'bg-accent-green animate-pulse',
  waiting: 'bg-accent-orange animate-pulse',
  blocked: 'bg-accent-red animate-blink',
}

const PROVIDER_LABELS: Record<string, string> = {
  openai: 'OpenAI',
  deepseek: 'DeepSeek',
  anthropic: 'Anthropic',
  azure: 'Azure',
  mock: 'Mock',
}

function getAgentColor(agentId: string, _role: string): string {
  // 使用 agent id 的简单哈希选择一个颜色
  const colors = ['#58a6ff', '#a371f7', '#3fb950', '#f0883e', '#f85149', '#39d2c0', '#d29922', '#8b949e']
  let hash = 0
  for (let i = 0; i < agentId.length; i++) {
    hash = ((hash << 5) - hash) + agentId.charCodeAt(i)
    hash |= 0
  }
  return colors[Math.abs(hash) % colors.length]
}

const POOL_AGENT_COLORS = ['#58a6ff', '#a371f7', '#3fb950', '#f0883e', '#f85149', '#39d2c0', '#d29922', '#8b949e']

interface Props { projectId?: string | null }

export default function AgentTeamPanel({ projectId }: Props) {
  const pid = projectId ?? ''
  const agents = useStore((s) => s.agentsByProject[pid] ?? [])
  const globalLlmConfig = useStore((s) => s.globalLlmConfig)
  const updateAgent = useStore((s) => s.updateAgent)
  const setInterventionMode = useStore((s) => s.setInterventionMode)
  const startProject = useStore((s) => s.startProject)
  const llmMode = useStore((s) => s.llmMode)
  const startRealPipeline = useStore((s) => s.startRealPipeline)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [showPool, setShowPool] = useState(false)
  const [llmEditorAgent, setLlmEditorAgent] = useState<string | null>(null)
  const [availableProviders, setAvailableProviders] = useState<string[]>([])
  const [availableModels, setAvailableModels] = useState<Record<string, LLMModelInfo>>({})
  const [apiAgents, setApiAgents] = useState<Agent[] | null>(null)
  const [agentsLoading, setAgentsLoading] = useState(false)
  const stopSimRef = useRef<(() => void) | null>(null)

  // Agent replacement state
  const replaceAgent = useStore((s) => s.replaceAgent)
  const addLog = useStore((s) => s.addLog)
  const [replaceTarget, setReplaceTarget] = useState<string | null>(null)
  const [availableReplace, setAvailableReplace] = useState<Agent[]>([])
  const [replaceLoading, setReplaceLoading] = useState(false)
  const replaceRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!replaceTarget) return
    const handler = (e: MouseEvent) => {
      if (replaceRef.current && !replaceRef.current.contains(e.target as Node)) {
        setReplaceTarget(null)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [replaceTarget])

  const handleStartReplace = async (agentId: string) => {
    setReplaceTarget(agentId)
    setReplaceLoading(true)
    try {
      // Fetch available agents from backend (not in any project)
      const raw = await getAvailableAgents()
      const mapped: Agent[] = raw.map((a: any) => ({
        id: a.id,
        name: a.name || a.id,
        role: a.role || a.type || '团队成员',
        status: 'idle' as const,
        avatarColor: a.avatar_color || '#8b949e',
        description: a.description || '',
        llm_config: a.llm_config,
      }))
      // Filter out agents already in the project
      const currentIds = new Set(agents.map(a => a.id))
      setAvailableReplace(mapped.filter(a => !currentIds.has(a.id)))
    } catch {
      // Fallback: use apiAgents if available
      const currentIds = new Set(agents.map(a => a.id))
      setAvailableReplace((apiAgents || []).filter(a => !currentIds.has(a.id)))
    } finally {
      setReplaceLoading(false)
    }
  }

  const handleConfirmReplace = async (newAgent: Agent) => {
    const oldId = replaceTarget
    if (!oldId || !pid) return
    const oldAgent = agents.find(a => a.id === oldId)

    // Release old agent from project (fire-and-forget)
    releaseAgentFromProject(oldId, pid).catch(() => {})

    // Assign new agent to project (fire-and-forget)
    assignAgentToProject(newAgent.id, pid).catch(() => {})

    // Update store
    replaceAgent(pid, oldId, newAgent)

    // Update assigned tasks
    const tasks = useStore.getState().tasksByProject[pid] || []
    for (const task of tasks) {
      if (task.assignedAgents.includes(oldId)) {
        const next = task.assignedAgents.map(a => a === oldId ? newAgent.id : a)
        useStore.getState().updateTask(pid, task.id, {
          assignedAgents: next,
          updatedAt: new Date().toISOString(),
        })
      }
    }

    addLog(pid, {
      level: 'info',
      source: 'human',
      message: `替换 Agent: ${oldAgent?.name || oldId} → ${newAgent.name}`,
    })

    setReplaceTarget(null)
  }

  // Fetch real agents from backend when no project is active
  useEffect(() => {
    if (!pid) {
      setAgentsLoading(true)
      fetch('/api/agents')
        .then((res) => {
          if (!res.ok) throw new Error('Backend not available')
          return res.json()
        })
        .then((data) => {
          const list: any[] = data.agents || []
          const mapped: Agent[] = list.map((a: any) => ({
            id: a.id,
            name: a.name,
            role: '团队成员',
            status: (a.status as Agent['status']) || 'idle',
            avatarColor: a.avatar_color || '#8b949e',
            description: a.description,
            llm_config: a.llm_config,
          }))
          setApiAgents(mapped)
        })
        .catch(() => setApiAgents(null))
        .finally(() => setAgentsLoading(false))
    }
  }, [pid])

  const presetAgents =
    agents.length > 0 ? agents :
    apiAgents && apiAgents.length > 0 ? apiAgents :
    agentsLoading ? [] :
    []

  useEffect(() => {
    getAvailableProviders().then(setAvailableProviders).catch(() => setAvailableProviders(['openai', 'deepseek', 'anthropic', 'azure', 'mock']))
    getAvailableModels().then(setAvailableModels).catch(() => {})
  }, [])

  const getModelLabel = (agent: Agent) => {
    if (agent.llm_config) return agent.llm_config.model
    return `全局: ${globalLlmConfig.model}`
  }

  const handleWhisper = (agentId: string) => {
    setSelectedId(agentId)
    setInterventionMode(pid,'whisper')
  }

  const handleAgentsSelected = (
    assignments: Array<{ agentId: string; tempRole: string; tempDescription: string }>,
    taskName: string,
    taskDesc: string,
  ) => {
    const newAgents: Agent[] = assignments.map((a, i) => ({
      id: a.agentId,
      name: a.agentId,
      role: '团队成员',
      status: 'idle' as const,
      avatarColor: POOL_AGENT_COLORS[i % POOL_AGENT_COLORS.length],
      description: a.tempDescription || undefined,
    }))

    // Stop previous simulation and start new project
    stopSimRef.current?.()
    startProject(taskName, taskDesc, newAgents)

    if (llmMode === 'real') {
      const agentIds = newAgents.map((a) => a.id)
      const tc = useStore.getState().teamConfigs[pid] || undefined
      startRealPipeline(pid, taskName, taskDesc, agentIds, tc)
    } else {
      stopSimRef.current = startSimulation(pid, taskName, taskDesc)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2.5 border-b border-white/5 flex items-center justify-between">
        <span className="text-sm text-surface-300">
          {agentsLoading ? '加载中...' : `${presetAgents.length} 位成员`}
        </span>
        <button
          onClick={() => setShowPool(true)}
          className="text-sm text-accent-cyan hover:text-accent-cyan/80 transition-colors"
        >
          + 人才库
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
        {agentsLoading && (
          <div className="flex items-center justify-center py-8">
            <div className="w-5 h-5 border-2 border-accent-cyan/30 border-t-accent-cyan rounded-full animate-spin" />
          </div>
        )}
        {!agentsLoading && presetAgents.length === 0 && (
          <div className="text-center py-8 text-surface-500 text-sm">
            暂无可用 Agent
          </div>
        )}
        {!agentsLoading && presetAgents.map((agent) => {
          const color = agent.avatarColor || getAgentColor(agent.id, agent.role)
          const isSelected = selectedId === agent.id
          const isEditingLlm = llmEditorAgent === agent.id
          const llmCfg = agent.llm_config
          const effectiveCfg = llmCfg || globalLlmConfig
          const filteredModels = Object.entries(availableModels).filter(([, info]) => info.provider === effectiveCfg.provider)

          return (
            <div
              key={agent.id}
              className={`relative rounded-lg p-2.5 transition-all duration-200 group ${
                isSelected
                  ? 'bg-accent-cyan/10 border border-accent-cyan/30'
                  : 'bg-background-card border border-white/5 hover:border-white/10'
              }`}
            >
              <div
                className="flex items-center gap-2.5 cursor-pointer"
                onClick={() => handleWhisper(agent.id)}
              >
                <div
                  className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
                  style={{ backgroundColor: `${color}30`, color }}
                >
                  {agent.name.substring(0, 2)}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-medium text-surface-50 truncate">
                      {agent.name}
                    </span>
                    {pid && (
                      <span className="text-xs text-surface-400 truncate">
                        {agent.role}
                      </span>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setLlmEditorAgent(isEditingLlm ? null : agent.id)
                      }}
                      className={`text-xs px-1.5 py-0.5 rounded font-mono shrink-0 transition-colors ${
                        llmCfg
                          ? 'bg-accent-purple/20 text-accent-purple hover:bg-accent-purple/30'
                          : 'bg-surface-600/50 text-surface-400 hover:text-surface-300 hover:bg-surface-600'
                      }`}
                      title={llmCfg ? `${effectiveCfg.provider} / ${effectiveCfg.model}` : `全局默认: ${globalLlmConfig.model}`}
                    >
                      {getModelLabel(agent)}
                    </button>
                  </div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <div className={`w-1.5 h-1.5 rounded-full ${STATUS_STYLES[agent.status]}`} />
                    <span className="text-xs text-surface-400">
                      {STATUS_LABELS[agent.status]}
                    </span>
                    {agent.currentTask && (
                      <span className="text-xs text-surface-500 truncate">
                        · {agent.currentTask}
                      </span>
                    )}
                  </div>
                </div>

                <span
                  className="text-surface-600 group-hover:text-accent-cyan text-sm opacity-0 group-hover:opacity-100 transition-all cursor-pointer"
                  onClick={(e) => { e.stopPropagation(); handleStartReplace(agent.id) }}
                  title="替换 Agent"
                >
                  &#8646;
                </span>
              </div>

              {/* Agent replace popover */}
              {replaceTarget === agent.id && (
                <div ref={replaceRef} className="mt-2 p-2 bg-gray-800 border border-gray-600 rounded-lg space-y-1.5">
                  <div className="text-xs text-surface-400">选择替换者：</div>
                  {replaceLoading ? (
                    <div className="flex items-center gap-2 py-1 text-xs text-surface-500">
                      <div className="w-3 h-3 border-2 border-accent-cyan/30 border-t-accent-cyan rounded-full animate-spin" />
                      加载可用 Agent...
                    </div>
                  ) : availableReplace.length === 0 ? (
                    <div className="text-xs text-surface-500 py-1">暂无可用 Agent</div>
                  ) : (
                    availableReplace.slice(0, 8).map((a) => (
                      <button
                        key={a.id}
                        onClick={(e) => { e.stopPropagation(); handleConfirmReplace(a) }}
                        className="w-full text-left px-2 py-1 rounded hover:bg-white/5 text-xs text-surface-200 flex items-center gap-2 transition-colors"
                      >
                        <div
                          className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold"
                          style={{ backgroundColor: `${a.avatarColor}30`, color: a.avatarColor }}
                        >
                          {a.name.substring(0, 2)}
                        </div>
                        <span>{a.name}</span>
                      </button>
                    ))
                  )}
                </div>
              )}

              {/* Inline LLM editor popover */}
              {isEditingLlm && (
                <div
                  className="mt-2 p-3 bg-gray-800 border border-gray-600 rounded-lg space-y-2"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-surface-400">
                      {llmCfg ? 'Agent 独立配置' : `使用全局默认 (${globalLlmConfig.model})`}
                    </span>
                    {!llmCfg ? (
                      <button
                        onClick={() => {
                          updateAgent(pid, agent.id, { llm_config: { ...globalLlmConfig } })
                        }}
                        className="text-xs text-accent-cyan hover:text-accent-cyan/80"
                      >
                        覆盖为独立配置
                      </button>
                    ) : (
                      <button
                        onClick={() => {
                          updateAgent(pid, agent.id, { llm_config: undefined })
                          setLlmEditorAgent(null)
                        }}
                        className="text-xs text-accent-red hover:text-accent-red/80"
                      >
                        重置为全局默认
                      </button>
                    )}
                  </div>

                  {(llmCfg || effectiveCfg) && (
                    <>
                      <div>
                        <label className="block text-xs text-gray-500 mb-0.5">Provider</label>
                        <select
                          value={effectiveCfg.provider}
                          onChange={(e) => {
                            const newProvider = e.target.value
                            const modelsForProvider = Object.entries(availableModels).filter(([, info]) => info.provider === newProvider)
                            const newModel = modelsForProvider.length > 0 ? modelsForProvider[0][0] : effectiveCfg.model
                            updateAgent(pid, agent.id, { llm_config: { provider: newProvider, model: newModel, temperature: effectiveCfg.temperature, max_tokens: effectiveCfg.max_tokens } })
                          }}
                          className="w-full bg-gray-700 border border-gray-500 rounded px-2 py-1 text-xs text-gray-200 focus:outline-none focus:border-accent-cyan"
                        >
                          {availableProviders.map((p) => (
                            <option key={p} value={p}>{PROVIDER_LABELS[p] || p}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-0.5">Model</label>
                        <select
                          value={effectiveCfg.model}
                          onChange={(e) => updateAgent(pid, agent.id, { llm_config: { ...effectiveCfg, model: e.target.value } })}
                          className="w-full bg-gray-700 border border-gray-500 rounded px-2 py-1 text-xs text-gray-200 focus:outline-none focus:border-accent-cyan"
                        >
                          {filteredModels.map(([name, info]) => (
                            <option key={name} value={name}>{name} — {info.description}</option>
                          ))}
                          {filteredModels.length === 0 && (
                            <option value={effectiveCfg.model}>{effectiveCfg.model}</option>
                          )}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-0.5">Temperature: {effectiveCfg.temperature.toFixed(1)}</label>
                        <input
                          type="range"
                          min="0"
                          max="2"
                          step="0.1"
                          value={effectiveCfg.temperature}
                          onChange={(e) => updateAgent(pid, agent.id, { llm_config: { ...effectiveCfg, temperature: parseFloat(e.target.value) } })}
                          className="w-full accent-accent-cyan"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-0.5">Max Tokens</label>
                        <input
                          type="number"
                          value={effectiveCfg.max_tokens || ''}
                          onChange={(e) => updateAgent(pid, agent.id, { llm_config: { ...effectiveCfg, max_tokens: e.target.value ? parseInt(e.target.value) : undefined } })}
                          placeholder="模型默认"
                          className="w-full bg-gray-700 border border-gray-500 rounded px-2 py-1 text-xs text-gray-200 placeholder:text-gray-500 focus:outline-none focus:border-accent-cyan"
                        />
                      </div>
                    </>
                  )}

                  <button
                    onClick={() => setLlmEditorAgent(null)}
                    className="w-full text-xs text-gray-400 hover:text-gray-300 py-1"
                  >
                    收起
                  </button>
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div className="px-3 py-2 border-t border-white/5">
        <div className="flex gap-2 text-xs text-surface-500">
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse" />工作
          </span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-accent-purple animate-pulse" />思考
          </span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-accent-red animate-blink" />阻塞
          </span>
        </div>
      </div>

      <AgentPoolModal
        isOpen={showPool}
        onClose={() => setShowPool(false)}
        onAgentsSelected={(assignments, taskName, taskDesc) => {
          handleAgentsSelected(assignments, taskName, taskDesc)
          setShowPool(false)
        }}
      />
    </div>
  )
}
