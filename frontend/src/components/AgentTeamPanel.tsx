import { useState } from 'react'
import { useStore } from '../lib/store'
import type { Agent } from '../lib/store'
import AgentPoolModal from './AgentPoolModal'

const AGENT_COLORS: Record<string, string> = {
  pm: '#58a6ff',
  architect: '#a371f7',
  backend: '#3fb950',
  frontend: '#f0883e',
  tester: '#f85149',
  devops: '#39d2c0',
}

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

function getAgentColor(agentId: string, role: string): string {
  for (const [key, color] of Object.entries(AGENT_COLORS)) {
    if (role.includes(key) || agentId.includes(key)) return color
  }
  return '#8b949e'
}

const POOL_AGENT_COLORS = ['#58a6ff', '#a371f7', '#3fb950', '#f0883e', '#f85149', '#39d2c0', '#d29922', '#8b949e']

export default function AgentTeamPanel() {
  const { agents, setAgents, setInterventionMode } = useStore()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [showPool, setShowPool] = useState(false)

  const presetAgents = agents.length > 0 ? agents : [
    { id: 'pm', name: '产品经理', role: '产品经理', status: 'idle' as const, avatarColor: '#58a6ff' },
    { id: 'architect', name: '架构师', role: '架构师', status: 'idle' as const, avatarColor: '#a371f7' },
    { id: 'backend', name: '后端开发', role: '后端开发', status: 'idle' as const, avatarColor: '#3fb950' },
    { id: 'frontend', name: '前端开发', role: '前端开发', status: 'idle' as const, avatarColor: '#f0883e' },
    { id: 'tester', name: '测试工程师', role: '测试工程师', status: 'idle' as const, avatarColor: '#f85149' },
  ]

  const handleWhisper = (agentId: string) => {
    setSelectedId(agentId)
    setInterventionMode('whisper')
  }

  const handleAgentsSelected = (
    assignments: Array<{ agentId: string; tempRole: string; tempDescription: string }>,
  ) => {
    const roleLabels: Record<string, string> = {
      requirement: '需求分析',
      design: '架构设计',
      backend: '后端开发',
      frontend: '前端开发',
      testing: '测试验证',
      review: '代码评审',
      deploy: '部署运维',
      document: '文档编写',
    }

    const newAgents: Agent[] = assignments.map((a, i) => ({
      id: a.agentId,
      name: a.agentId,
      role: roleLabels[a.tempRole] || a.tempRole || a.agentId,
      status: 'idle' as const,
      avatarColor: POOL_AGENT_COLORS[i % POOL_AGENT_COLORS.length],
      description: a.tempDescription || undefined,
    }))

    const existingIds = new Set(agents.map((a) => a.id))
    const toAdd = newAgents.filter((a) => !existingIds.has(a.id))
    setAgents([...agents, ...toAdd])
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2.5 border-b border-white/5 flex items-center justify-between">
        <span className="text-sm text-surface-300">
          {presetAgents.length} 位成员
        </span>
        <button
          onClick={() => setShowPool(true)}
          className="text-sm text-accent-cyan hover:text-accent-cyan/80 transition-colors"
        >
          + 人才库
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
        {presetAgents.map((agent) => {
          const color = agent.avatarColor || getAgentColor(agent.id, agent.role)
          const isSelected = selectedId === agent.id

          return (
            <div
              key={agent.id}
              onClick={() => handleWhisper(agent.id)}
              className={`relative rounded-lg p-2.5 cursor-pointer transition-all duration-200 group ${
                isSelected
                  ? 'bg-accent-cyan/10 border border-accent-cyan/30'
                  : 'bg-background-card border border-white/5 hover:border-white/10'
              }`}
            >
              <div className="flex items-center gap-2.5">
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
                    <span className="text-xs text-surface-400 truncate">
                      {agent.role}
                    </span>
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

                <span className="text-surface-600 group-hover:text-accent-cyan text-sm opacity-0 group-hover:opacity-100 transition-all">
                  &#9993;
                </span>
              </div>
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
        onAgentsSelected={(assignments) => {
          handleAgentsSelected(assignments)
          setShowPool(false)
        }}
      />
    </div>
  )
}
