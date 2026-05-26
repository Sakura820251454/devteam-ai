import { useState, useEffect, useMemo, useRef } from 'react'
import { useStore } from '../lib/store'
import type { Task } from '../lib/store'
import { updateTask as apiUpdateTask, changeTaskStatus, assignTaskAgents } from '../lib/api'

const PRIORITY_COLORS: Record<string, string> = { low: 'bg-surface-400', medium: 'bg-accent-cyan', high: 'bg-accent-orange', urgent: 'bg-accent-red' }
const PRIORITY_LABELS: Record<string, string> = { low: '低', medium: '中', high: '高', urgent: '紧急' }
const PRIORITY_ORDER = ['low', 'medium', 'high', 'urgent']

const RISK_LABELS: Record<string, string> = { low: '低风险', medium: '中风险', high: '高风险', critical: '严重' }
const RISK_COLORS: Record<string, string> = { low: 'text-accent-green', medium: 'text-accent-cyan', high: 'text-accent-orange', critical: 'text-accent-red' }

const STATUS_LABELS: Record<string, string> = { backlog: '待办', todo: '计划中', in_progress: '进行中', blocked: '阻塞', review: '审核中', done: '已完成', paused: '暂停', cancelled: '已取消' }
const STATUS_ORDER = ['backlog', 'todo', 'in_progress', 'blocked', 'review', 'done', 'paused', 'cancelled']
const STATUS_STYLES: Record<string, string> = {
  backlog: 'bg-surface-600 text-surface-300',
  todo: 'bg-accent-cyan/20 text-accent-cyan',
  in_progress: 'bg-accent-orange/20 text-accent-orange',
  blocked: 'bg-accent-red/20 text-accent-red',
  review: 'bg-accent-purple/20 text-accent-purple',
  done: 'bg-accent-green/20 text-accent-green',
  paused: 'bg-surface-600/50 text-surface-400',
  cancelled: 'bg-surface-700/50 text-surface-500 line-through',
}

function TaskCard({ task }: { task: Task }) {
  const pid = useStore((s) => s.activeProjectId) ?? ''
  const agents = useStore((s) => s.agentsByProject[pid] ?? [])
  const updateTask = useStore((s) => s.updateTask)
  const addLog = useStore((s) => s.addLog)
  const [menuOpen, setMenuOpen] = useState(false)
  const [editMode, setEditMode] = useState<'priority' | 'status' | 'agents' | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!menuOpen) return
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
        setEditMode(null)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [menuOpen])

  const priorityColor = PRIORITY_COLORS[task.priority] || 'bg-surface-400'
  const priorityHex = { low: '#8b949e', medium: '#58a6ff', high: '#d29922', urgent: '#f85149' }[task.priority] || '#8b949e'

  const handleAction = (action: 'priority' | 'status' | 'agents') => {
    setEditMode(action)
    // Don't close menu; user picks from inline options
  }

  const applyPriority = (pri: string) => {
    const now = new Date().toISOString()
    updateTask(pid, task.id, { priority: pri as Task['priority'], updatedAt: now })
    addLog(pid, { level: 'info', source: 'human', message: `任务「${task.title}」优先级 → ${PRIORITY_LABELS[pri]}` })
    apiUpdateTask(task.id, { priority: pri }).catch(() => {})
    setEditMode(null)
    setMenuOpen(false)
  }

  const applyStatus = (st: string) => {
    const now = new Date().toISOString()
    const newHistory = [
      ...(task.statusHistory || []),
      { from: task.status, to: st, timestamp: now, by: 'human' },
    ]
    updateTask(pid, task.id, { status: st, statusHistory: newHistory, updatedAt: now })
    addLog(pid, { level: 'info', source: 'human', message: `任务「${task.title}」状态 → ${STATUS_LABELS[st]}` })
    changeTaskStatus(task.id, st).catch(() => {})
    setEditMode(null)
    setMenuOpen(false)
  }

  const toggleAgent = (agentId: string) => {
    const now = new Date().toISOString()
    const current = task.assignedAgents
    const next = current.includes(agentId)
      ? current.filter((a) => a !== agentId)
      : [...current, agentId]
    if (next.length === 0) return
    updateTask(pid, task.id, { assignedAgents: next, updatedAt: now })
    assignTaskAgents(task.id, next).catch(() => {})
    const agent = agents.find((a) => a.id === agentId)
    const verb = current.includes(agentId) ? '移除' : '添加'
    addLog(pid, { level: 'info', source: 'human', message: `任务「${task.title}」负责人${verb}: ${agent?.name || agentId}` })
  }

  return (
    <div
      className="bg-background-card rounded-lg overflow-hidden transition-all hover:ring-1 hover:ring-white/10 relative group"
      style={{ borderLeft: `3px solid ${priorityHex}` }}
    >
      {/* 标题 + 状态 + 操作按钮 */}
      <div className="px-3.5 pt-3 pb-2">
        <div className="flex items-start justify-between gap-2">
          <span className="text-sm font-medium text-surface-100 leading-snug">{task.title}</span>
          <div className="flex items-center gap-1 shrink-0">
            <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${STATUS_STYLES[task.status] || STATUS_STYLES.backlog}`}>
              {STATUS_LABELS[task.status] || task.status}
            </span>
            <div ref={menuRef} className="relative">
              <button
                onClick={(e) => { e.stopPropagation(); setMenuOpen(!menuOpen); setEditMode(null) }}
                className="w-5 h-5 rounded flex items-center justify-center text-surface-500 hover:text-surface-200 hover:bg-white/5 opacity-0 group-hover:opacity-100 transition-all text-xs"
                title="任务操作"
              >
                ⋮
              </button>
              {menuOpen && (
                <div className="absolute right-0 top-6 w-36 bg-background-panel border border-white/10 rounded-lg shadow-panel z-30 py-1 text-xs">
                  <button onClick={() => handleAction('status')} className="w-full text-left px-3 py-1.5 hover:bg-white/5 text-surface-200 flex items-center gap-2">
                    <span className="text-accent-cyan">↻</span> 改状态
                  </button>
                  <button onClick={() => handleAction('priority')} className="w-full text-left px-3 py-1.5 hover:bg-white/5 text-surface-200 flex items-center gap-2">
                    <span className="text-accent-orange">⚡</span> 改优先级
                  </button>
                  <button onClick={() => handleAction('agents')} className="w-full text-left px-3 py-1.5 hover:bg-white/5 text-surface-200 flex items-center gap-2">
                    <span className="text-accent-purple">👥</span> 换负责人
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Inline editors */}
        {editMode === 'priority' && (
          <div className="mt-2 flex gap-1">
            {PRIORITY_ORDER.map((p) => (
              <button
                key={p}
                onClick={() => applyPriority(p)}
                className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                  task.priority === p
                    ? 'border-accent-cyan text-accent-cyan bg-accent-cyan/10'
                    : 'border-white/10 text-surface-400 hover:text-surface-200 hover:border-white/20'
                }`}
              >
                {PRIORITY_LABELS[p]}
              </button>
            ))}
          </div>
        )}
        {editMode === 'status' && (
          <div className="mt-2 flex flex-wrap gap-1">
            {STATUS_ORDER.map((s) => (
              <button
                key={s}
                onClick={() => applyStatus(s)}
                className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                  task.status === s
                    ? 'border-accent-cyan text-accent-cyan bg-accent-cyan/10'
                    : 'border-white/10 text-surface-400 hover:text-surface-200 hover:border-white/20'
                }`}
              >
                {STATUS_LABELS[s]}
              </button>
            ))}
          </div>
        )}
        {editMode === 'agents' && (
          <div className="mt-2 flex flex-wrap gap-1">
            {agents.map((a) => {
              const active = task.assignedAgents.includes(a.id)
              return (
                <button
                  key={a.id}
                  onClick={() => toggleAgent(a.id)}
                  className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                    active
                      ? 'border-accent-green text-accent-green bg-accent-green/10'
                      : 'border-white/10 text-surface-400 hover:text-surface-200 hover:border-white/20'
                  }`}
                >
                  {active ? '✓ ' : ''}{a.name}
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/* 元信息行 */}
      <div className="px-3.5 pb-2 flex items-center gap-3 text-xs text-surface-400 flex-wrap">
        <span className="inline-flex items-center gap-1">
          <span className={`w-1.5 h-1.5 rounded-full ${priorityColor}`} />
          {PRIORITY_LABELS[task.priority] || task.priority}
        </span>
        {task.createdBy && (
          <span className="inline-flex items-center gap-1">
            <span className="text-surface-600">👤</span>
            {task.createdBy}
          </span>
        )}
        <span className="inline-flex items-center gap-1 text-surface-500">
          <span className="text-surface-600">🕐</span>
          {new Date(task.updatedAt).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>

      {/* 负责人 */}
      {task.assignedAgents.length > 0 && (
        <div className="px-3.5 pb-2">
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-surface-600 shrink-0">负责</span>
            {task.assignedAgents.slice(0, 5).map((agentId) => {
              const agent = agents.find((a) => a.id === agentId)
              const color = agent?.avatarColor || '#8b949e'
              return (
                <div key={agentId} className="w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold border border-white/5"
                  style={{ backgroundColor: `${color}25`, color }} title={agent?.name || agentId}>
                  {(agent?.name || agentId).substring(0, 2)}
                </div>
              )
            })}
            {task.assignedAgents.length > 5 && (
              <span className="text-xs text-surface-500">+{task.assignedAgents.length - 5}</span>
            )}
          </div>
        </div>
      )}

      {/* 流转记录 — 独立区块 */}
      {task.statusHistory && task.statusHistory.length > 0 && (
        <div className="border-t border-white/5 bg-surface-800/30 px-3.5 py-2.5">
          <div className="text-xs text-surface-500 mb-2 font-medium">流转记录</div>
          <div className="space-y-1.5">
            {task.statusHistory.slice(-4).map((h, idx) => (
              <div key={idx} className="flex items-center gap-1.5 text-xs">
                <span className="text-surface-600 font-mono text-[11px] shrink-0 w-12">
                  {new Date(h.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                </span>
                <span className="text-surface-600">▸</span>
                <span className={`px-1 py-0.5 rounded text-[11px] ${STATUS_STYLES[h.from] || STATUS_STYLES.backlog}`}>
                  {STATUS_LABELS[h.from] || h.from}
                </span>
                <span className="text-surface-600">→</span>
                <span className={`px-1 py-0.5 rounded text-[11px] ${STATUS_STYLES[h.to] || STATUS_STYLES.backlog}`}>
                  {STATUS_LABELS[h.to] || h.to}
                </span>
                <span className="text-surface-600 ml-auto">{h.by}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

interface Props { projectId?: string | null; selectedStage?: string | null }

export default function TaskBoard({ projectId, selectedStage }: Props) {
  const pid = projectId ?? ''
  const tasks = useStore((s) => s.tasksByProject[pid] ?? [])
  const tasksLoading = useStore((s) => s.tasksLoadingByProject[pid] ?? false)
  const pipeline = useStore((s) => s.pipelines[pid] ?? null)
  const setTasksLoading = useStore((s) => s.setTasksLoading)
  const addLog = useStore((s) => s.addLog)
  const updateTask = useStore((s) => s.updateTask)
  const stage = pipeline?.stages.find((s) => s.key === selectedStage)

  useEffect(() => {
    if (!selectedStage) return

    const currentTasks = useStore.getState().tasksByProject[pid] ?? []
    if (currentTasks.length > 0) return

    // Show a brief loading indicator; tasks arrive from simulation (mock mode)
    // or backend polling (real mode) — the component is purely reactive.
    setTasksLoading(pid, true)
    addLog(pid, { level: 'info', source: 'taskboard', message: `加载阶段 "${stage?.label || selectedStage}" 的任务...` })

    const timer = setTimeout(() => {
      setTasksLoading(pid, false)
    }, 3000)

    return () => clearTimeout(timer)
  }, [selectedStage, pid])

  const tasksByStatus = useMemo(() => {
    const map: Record<string, Task[]> = {}
    for (const t of tasks) { (map[t.status] ||= []).push(t) }
    return map
  }, [tasks])

  const allStatuses = ['backlog', 'todo', 'in_progress', 'blocked', 'review', 'done', 'paused', 'cancelled']

  // High-risk tasks awaiting human approval
  const pendingApprovalTasks = useMemo(() => tasks.filter(
    t => t.status === 'review' && (t.riskLevel === 'high' || t.riskLevel === 'critical')
  ), [tasks])

  if (tasksLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex items-center gap-3 text-surface-500">
          <div className="w-5 h-5 rounded-full border-2 border-accent-cyan border-t-transparent animate-spin" />
          <span className="text-sm">Agent 正在整理任务...</span>
        </div>
      </div>
    )
  }

  if (tasks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-surface-600">
        <p className="text-sm">该阶段暂无任务</p>
        <p className="text-xs mt-1">Agent 将在需要时自动创建</p>
      </div>
    )
  }

  return (
    <div className="p-4">
      {pendingApprovalTasks.length > 0 && (
        <div className="mb-4 p-4 bg-accent-orange/10 border border-accent-orange/30 rounded-xl">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">⚠️</span>
            <span className="text-sm font-medium text-accent-orange">待审批任务</span>
            <span className="text-xs text-surface-400">
              ({pendingApprovalTasks.length} 个高风险任务需要人工审批)
            </span>
          </div>
          <div className="space-y-2">
            {pendingApprovalTasks.map((task) => (
              <div key={task.id} className="flex items-center justify-between bg-background-card rounded-lg px-4 py-3 border border-white/5">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-surface-100 truncate">{task.title}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${RISK_COLORS[task.riskLevel || ''] || 'text-surface-400'} bg-surface-700/50`}>
                      {RISK_LABELS[task.riskLevel || ''] || task.riskLevel}
                    </span>
                  </div>
                  <div className="text-xs text-surface-500 mt-0.5 truncate">
                    {task.description?.slice(0, 80)}{(task.description?.length || 0) > 80 ? '...' : ''}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-4">
                  <button
                    onClick={() => {
                      const now = new Date().toISOString()
                      const newHistory = [
                        ...(task.statusHistory || []),
                        { from: task.status, to: 'done', timestamp: now, by: 'human' },
                      ]
                      updateTask(pid, task.id, { status: 'done', statusHistory: newHistory, updatedAt: now } as any)
                      addLog(pid, { level: 'info', source: 'human', message: `审批通过: 「${task.title}」` })
                      changeTaskStatus(task.id, 'done', 'human').catch(() => {})
                    }}
                    className="px-3 py-1.5 text-xs rounded-lg bg-accent-green/20 text-accent-green border border-accent-green/30 hover:bg-accent-green/30 transition-colors"
                  >
                    通过
                  </button>
                  <button
                    onClick={() => {
                      const now = new Date().toISOString()
                      const newHistory = [
                        ...(task.statusHistory || []),
                        { from: task.status, to: 'in_progress', timestamp: now, by: 'human' },
                      ]
                      updateTask(pid, task.id, { status: 'in_progress', statusHistory: newHistory, updatedAt: now } as any)
                      addLog(pid, { level: 'warn', source: 'human', message: `审批驳回（需返工）: 「${task.title}」` })
                      changeTaskStatus(task.id, 'in_progress', 'human').catch(() => {})
                    }}
                    className="px-3 py-1.5 text-xs rounded-lg bg-accent-red/20 text-accent-red border border-accent-red/30 hover:bg-accent-red/30 transition-colors"
                  >
                    驳回
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      <div className="text-xs text-surface-500 mb-2">
        {tasks.length} 个任务 · Agent 自主管理流转
      </div>
      <div className="grid grid-cols-8 gap-3">
        {allStatuses.map((status) => (
          <div key={status}>
            <div className="flex items-center justify-between mb-2.5">
              <span className={`text-sm px-2 py-0.5 rounded font-medium ${STATUS_STYLES[status]}`}>
                {STATUS_LABELS[status]}
              </span>
              <span className="text-sm text-surface-500 font-mono">
                {tasksByStatus[status]?.length || 0}
              </span>
            </div>
            <div className="space-y-2.5">
              {(tasksByStatus[status] || []).map((task) => (
                <TaskCard key={task.id} task={task} />
              ))}
              {(!tasksByStatus[status] || tasksByStatus[status].length === 0) && (
                <div className="text-center py-6 text-xs text-surface-600 bg-background-card/30 rounded-lg border border-dashed border-white/5">
                  暂无
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
