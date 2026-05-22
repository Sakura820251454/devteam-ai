import { useState } from 'react'
import { useStore } from '../lib/store'
import { pausePipeline, intervenePipeline } from '../lib/api'

type InterventionMode = 'whisper' | 'broadcast' | 'pause'

interface InterventionAction {
  mode: InterventionMode
  icon: string
  label: string
  description: string
  color: string
}

const ACTIONS: InterventionAction[] = [
  {
    mode: 'whisper',
    icon: '✉',
    label: '私信指导',
    description: '给单个 Agent 发送私下指令，不影响其他人',
    color: 'accent-purple',
  },
  {
    mode: 'broadcast',
    icon: '📢',
    label: '全局广播',
    description: '向所有 Agent 传达优先级或方向调整',
    color: 'accent-cyan',
  },
  {
    mode: 'pause',
    icon: '⏸',
    label: '暂停审查',
    description: '暂停 Pipeline，手动检查后决定继续或重分配',
    color: 'accent-orange',
  },
]

interface Props { projectId?: string | null }

export default function InterventionPanel({ projectId }: Props) {
  const pid = projectId ?? ''
  const interventionMode = useStore((s) => s.interventionsByProject[pid] ?? null)
  const agents = useStore((s) => s.agentsByProject[pid] ?? [])
  const pipeline = useStore((s) => s.pipelines[pid] ?? null)
  const setInterventionMode = useStore((s) => s.setInterventionMode)
  const addEvent = useStore((s) => s.addEvent)
  const addLog = useStore((s) => s.addLog)

  const [isOpen, setIsOpen] = useState(false)
  const [message, setMessage] = useState('')
  const [targetAgent, setTargetAgent] = useState('')

  const handleOpen = (mode: InterventionMode) => {
    setInterventionMode(pid, mode)
    setMessage('')
    setTargetAgent('')
    setIsOpen(false)
  }

  const handleSend = async () => {
    if (!interventionMode || !message.trim()) return

    const pipelineId = pipeline?.id

    if (interventionMode === 'whisper' && targetAgent && pipelineId) {
      const agent = agents.find((a) => a.id === targetAgent)
      addEvent(pid, {
        type: 'message',
        agentId: 'human',
        agentName: '你',
        agentColor: '#d29922',
        content: `私信 ${agent?.name || targetAgent}: ${message}`,
        importance: 'normal',
      })
      addLog(pid, {
        level: 'info',
        source: 'intervention',
        message: `[whisper → ${agent?.name || targetAgent}] ${message}`,
      })
      try {
        await intervenePipeline(pipelineId, message, targetAgent)
      } catch (err) {
        addLog(pid, { level: 'error', source: 'intervention', message: `私信发送失败: ${err}` })
      }
    } else if (interventionMode === 'broadcast' && pipelineId) {
      addEvent(pid, {
        type: 'decision',
        agentId: 'human',
        agentName: '你',
        agentColor: '#d29922',
        content: `全局指示: ${message}`,
        detail: '此消息对所有 Agent 可见，将影响后续决策',
        importance: 'important',
      })
      addLog(pid, {
        level: 'warn',
        source: 'intervention',
        message: `[broadcast] ${message}`,
      })
      try {
        await intervenePipeline(pipelineId, message)
      } catch (err) {
        addLog(pid, { level: 'error', source: 'intervention', message: `广播发送失败: ${err}` })
      }
    } else if (interventionMode === 'pause' && pipelineId) {
      addEvent(pid, {
        type: 'action',
        agentId: 'human',
        agentName: '你',
        agentColor: '#d29922',
        content: `暂停 Pipeline${message ? `: ${message}` : ''}`,
        importance: 'critical',
      })
      addLog(pid, {
        level: 'warn',
        source: 'intervention',
        message: `[pause] Pipeline 已暂停${message ? ` — ${message}` : ''}`,
      })
      try {
        await pausePipeline(pipelineId)
      } catch (err) {
        addLog(pid, { level: 'error', source: 'intervention', message: `暂停失败: ${err}` })
      }
    }

    setMessage('')
    setInterventionMode(pid,null)
  }

  // Determine pipeline status for whether pause is available
  const canPause = pipeline?.status === 'running'

  return (
    <>
      {/* FAB */}
      <div className="fixed bottom-6 right-6 z-40">
        {/* Expanded panel */}
        {isOpen && (
          <div className="absolute bottom-16 right-0 w-72 bg-background-panel border border-white/10 rounded-xl shadow-panel overflow-hidden animate-slide-up">
            <div className="px-4 py-3 border-b border-white/5">
              <h3 className="text-base font-medium text-surface-100">干预面板</h3>
              <p className="text-sm text-surface-400 mt-0.5">
                选择干预级别介入 Agent 工作
              </p>
            </div>

            <div className="p-2 space-y-1">
              {ACTIONS.map((action) => {
                const disabled = action.mode === 'pause' && !canPause
                return (
                  <button
                    key={action.mode}
                    onClick={() => !disabled && handleOpen(action.mode)}
                    disabled={disabled}
                    className={`w-full text-left p-3 rounded-lg transition-all ${
                      disabled
                        ? 'opacity-40 cursor-not-allowed'
                        : 'hover:bg-white/5 cursor-pointer'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <span className="text-xl">{action.icon}</span>
                      <div className="flex-1">
                        <div className="text-base font-medium text-surface-100">{action.label}</div>
                        <div className="text-sm text-surface-400 mt-0.5">{action.description}</div>
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>

            <div className="px-4 py-2 border-t border-white/5">
              <button
                onClick={() => setIsOpen(false)}
                className="text-sm text-surface-500 hover:text-surface-300 w-full text-center py-1"
              >
                取消
              </button>
            </div>
          </div>
        )}

        {/* FAB Button */}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={`w-12 h-12 rounded-full flex items-center justify-center text-xl shadow-panel transition-all duration-300 ${
            isOpen
              ? 'bg-accent-red/80 hover:bg-accent-red rotate-45'
              : 'bg-accent-cyan/80 hover:bg-accent-cyan hover:shadow-glow-cyan'
          }`}
          title="干预"
        >
          {isOpen ? '+' : '⚡'}
        </button>
      </div>

      {/* Input Modal Overlay */}
      {interventionMode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm animate-fade-in">
          <div className="w-[480px] bg-background-panel border border-white/10 rounded-xl shadow-panel animate-slide-up">
            {/* Header */}
            <div className="px-5 py-3 border-b border-white/5 flex items-center gap-3">
              <span className="text-lg">
                {ACTIONS.find((a) => a.mode === interventionMode)?.icon}
              </span>
              <div>
                <h3 className="text-sm font-medium text-surface-100">
                  {ACTIONS.find((a) => a.mode === interventionMode)?.label}
                </h3>
                <p className="text-xs text-surface-400">
                  {ACTIONS.find((a) => a.mode === interventionMode)?.description}
                </p>
              </div>
            </div>

            {/* Content */}
            <div className="p-5 space-y-3">
              {/* Agent selector for whisper */}
              {interventionMode === 'whisper' && (
                <div>
                  <label className="block text-xs text-surface-400 mb-1.5">目标 Agent</label>
                  <select
                    value={targetAgent}
                    onChange={(e) => setTargetAgent(e.target.value)}
                    className="w-full bg-background-input border border-white/10 rounded-lg px-3 py-2 text-sm text-surface-100 focus:outline-none focus:border-accent-purple transition-colors"
                  >
                    <option value="">选择 Agent...</option>
                    {agents.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name}
                      </option>
                    ))}
                    {agents.length === 0 && (
                      <option value="">暂无可用 Agent</option>
                    )}
                  </select>
                </div>
              )}

              {/* Message input */}
              <div>
                <label className="block text-xs text-surface-400 mb-1.5">
                  {interventionMode === 'whisper' ? '私信内容' :
                   interventionMode === 'broadcast' ? '广播内容' :
                   '暂停原因（可选）'}
                </label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                      handleSend()
                    }
                  }}
                  placeholder={
                    interventionMode === 'whisper' ? '输入给该 Agent 的指导...' :
                    interventionMode === 'broadcast' ? '输入全局指令...' :
                    '描述暂停原因...'
                  }
                  rows={3}
                  autoFocus
                  className="w-full bg-background-input border border-white/10 rounded-lg px-3 py-2 text-sm text-surface-100 focus:outline-none focus:border-accent-cyan transition-colors resize-none font-mono"
                />
                <div className="text-xs text-surface-600 mt-1">
                  {interventionMode !== 'pause' && '⌘+Enter 发送'}
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="px-5 py-3 border-t border-white/5 flex justify-end gap-2">
              <button
                onClick={() => setInterventionMode(pid,null)}
                className="px-4 py-2 text-sm text-surface-400 hover:text-surface-200 transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleSend}
                disabled={interventionMode === 'whisper' && (!message.trim() || !targetAgent)}
                className={`px-5 py-2 text-sm rounded-lg font-medium transition-all ${
                  (interventionMode !== 'whisper' && message.trim()) ||
                  (interventionMode === 'whisper' && message.trim() && targetAgent)
                    ? 'bg-accent-cyan text-white hover:bg-accent-cyan/90'
                    : 'bg-surface-600 text-surface-400 cursor-not-allowed'
                }`}
              >
                {interventionMode === 'pause' ? '确认暂停' : '发送'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
