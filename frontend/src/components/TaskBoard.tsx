import { useEffect, useMemo } from 'react'
import { useStore } from '../lib/store'
import type { Task } from '../lib/store'

const PRIORITY_COLORS: Record<string, string> = { low: 'bg-surface-400', medium: 'bg-accent-cyan', high: 'bg-accent-orange', urgent: 'bg-accent-red' }
const PRIORITY_LABELS: Record<string, string> = { low: '低', medium: '中', high: '高', urgent: '紧急' }

const STATUS_LABELS: Record<string, string> = { backlog: '待办', todo: '计划中', in_progress: '进行中', review: '审核中', done: '已完成' }
const STATUS_STYLES: Record<string, string> = {
  backlog: 'bg-surface-600 text-surface-300',
  todo: 'bg-accent-cyan/20 text-accent-cyan',
  in_progress: 'bg-accent-orange/20 text-accent-orange',
  review: 'bg-accent-purple/20 text-accent-purple',
  done: 'bg-accent-green/20 text-accent-green',
}

function TaskCard({ task }: { task: Task }) {
  const pid = useStore((s) => s.activeProjectId) ?? ''
  const agents = useStore((s) => s.agentsByProject[pid] ?? [])
  const priorityColor = PRIORITY_COLORS[task.priority] || 'bg-surface-400'
  const priorityHex = { low: '#8b949e', medium: '#58a6ff', high: '#d29922', urgent: '#f85149' }[task.priority] || '#8b949e'

  return (
    <div
      className="bg-background-card rounded-lg overflow-hidden transition-all hover:ring-1 hover:ring-white/10"
      style={{ borderLeft: `3px solid ${priorityHex}` }}
    >
      {/* 标题 + 状态 */}
      <div className="px-3.5 pt-3 pb-2">
        <div className="flex items-start justify-between gap-2">
          <span className="text-sm font-medium text-surface-100 leading-snug">{task.title}</span>
          <span className={`text-xs px-1.5 py-0.5 rounded shrink-0 font-medium ${STATUS_STYLES[task.status] || STATUS_STYLES.backlog}`}>
            {STATUS_LABELS[task.status] || task.status}
          </span>
        </div>
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
  const setTasks = useStore((s) => s.setTasks)
  const setTasksLoading = useStore((s) => s.setTasksLoading)
  const addLog = useStore((s) => s.addLog)
  const stage = pipeline?.stages.find((s) => s.key === selectedStage)

  useEffect(() => {
    if (!selectedStage) return

    // 如果已有真实任务则不覆盖（来自后端 polling 或 simulation）
    const currentTasks = useStore.getState().tasksByProject[pid] ?? []
    if (currentTasks.length > 0) return

    setTasksLoading(pid,true)
    addLog(pid, { level: 'info', source: 'taskboard', message: `加载阶段 "${stage?.label || selectedStage}" 的任务...` })

    const timer = setTimeout(() => {
      const mockTasks: Task[] = [
        {
          id: 'task-1', title: '数据库表结构设计', description: '', status: 'done', priority: 'high',
          stage: selectedStage, assignedAgents: ['architect', 'backend'], createdBy: 'architect',
          statusHistory: [
            { from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 3600000).toISOString(), by: 'architect' },
            { from: 'todo', to: 'in_progress', timestamp: new Date(Date.now() - 2400000).toISOString(), by: 'backend' },
            { from: 'in_progress', to: 'done', timestamp: new Date(Date.now() - 600000).toISOString(), by: 'backend' },
          ],
          tags: ['database', 'schema'], createdAt: new Date(Date.now() - 3600000).toISOString(), updatedAt: new Date(Date.now() - 600000).toISOString(),
        },
        {
          id: 'task-2', title: '实现用户认证 API', description: '', status: 'in_progress', priority: 'high',
          stage: selectedStage, assignedAgents: ['backend'], createdBy: 'pm',
          statusHistory: [
            { from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 3000000).toISOString(), by: 'pm' },
            { from: 'todo', to: 'in_progress', timestamp: new Date(Date.now() - 1800000).toISOString(), by: 'backend' },
          ],
          tags: ['api', 'auth'], createdAt: new Date(Date.now() - 3600000).toISOString(), updatedAt: new Date(Date.now() - 600000).toISOString(),
        },
        {
          id: 'task-3', title: '编写 API 单元测试', description: '', status: 'todo', priority: 'medium',
          stage: selectedStage, assignedAgents: ['tester'], createdBy: 'backend',
          statusHistory: [
            { from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 1200000).toISOString(), by: 'backend' },
          ],
          tags: ['testing'], createdAt: new Date(Date.now() - 1200000).toISOString(), updatedAt: new Date(Date.now() - 600000).toISOString(),
        },
        {
          id: 'task-4', title: '前端登录页面开发', description: '', status: 'todo', priority: 'medium',
          stage: selectedStage, assignedAgents: ['frontend'], createdBy: 'pm',
          statusHistory: [
            { from: 'backlog', to: 'todo', timestamp: new Date(Date.now() - 900000).toISOString(), by: 'pm' },
          ],
          tags: ['frontend', 'ui'], createdAt: new Date(Date.now() - 900000).toISOString(), updatedAt: new Date(Date.now() - 300000).toISOString(),
        },
      ]

      setTasks(pid,mockTasks)
      setTasksLoading(pid,false)
      addLog(pid, { level: 'success', source: 'taskboard', message: `加载完成: ${mockTasks.length} 个任务` })
    }, 800)

    return () => clearTimeout(timer)
  }, [selectedStage, pid])

  const tasksByStatus = useMemo(() => {
    const map: Record<string, Task[]> = {}
    for (const t of tasks) { (map[t.status] ||= []).push(t) }
    return map
  }, [tasks])

  const allStatuses = ['backlog', 'todo', 'in_progress', 'review', 'done']

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
      <div className="text-xs text-surface-500 mb-2">
        {tasks.length} 个任务 · Agent 自主管理流转
      </div>
      <div className="grid grid-cols-5 gap-4">
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
