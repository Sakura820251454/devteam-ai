import { useEffect, useState } from 'react'
import { useStore } from '../lib/store'
import {
  getStuckTasks,
  retryTask,
  type StuckTaskInfo,
} from '../lib/api'

function StepProgressBar({ current, total, status }: { current: number; total: number; status: string }) {
  const pct = total > 0 ? Math.round((current / total) * 100) : 0
  const color = status === 'stuck' ? 'bg-accent-red' : status === 'paused' ? 'bg-accent-orange' : 'bg-accent-green'

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-ultramodern-border rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-secondary whitespace-nowrap font-mono">
        {current}/{total}
      </span>
    </div>
  )
}

function HeartbeatIndicator({ lastHeartbeat, status }: { lastHeartbeat?: string; status: string }) {
  const [delta, setDelta] = useState(0)

  useEffect(() => {
    if (!lastHeartbeat) return
    const update = () => {
      const elapsed = (Date.now() - new Date(lastHeartbeat).getTime()) / 1000
      setDelta(elapsed)
    }
    update()
    const timer = setInterval(update, 1000)
    return () => clearInterval(timer)
  }, [lastHeartbeat])

  const isStale = delta > 120
  const isRunning = status === 'running'

  return (
    <div className="flex items-center gap-1.5">
      <span
        className={`w-2 h-2 rounded-full ${
          !isRunning
            ? 'bg-muted'
            : isStale
              ? 'bg-accent-red animate-blink'
              : 'bg-accent-green animate-pulse'
        }`}
      />
      <span className="text-[10px] text-secondary font-mono">
        {isRunning ? (isStale ? 'STUCK' : `${Math.round(delta)}s ago`) : status}
      </span>
    </div>
  )
}

function MiniStuckList({ stuck }: { stuck: StuckTaskInfo[] }) {
  if (stuck.length === 0) return null

  return (
    <div className="mt-2 p-2 rounded-lg bg-accent-red/10 border border-accent-red/30">
      <div className="text-xs font-semibold text-accent-red mb-1">
        疑似卡死 ({stuck.length})
      </div>
      {stuck.slice(0, 3).map((t) => (
        <div key={t.task_id} className="text-[10px] text-secondary font-mono flex justify-between">
          <span className="truncate max-w-[160px]">{t.task_id.slice(0, 8)}...</span>
          <span>{Math.round(t.elapsed_seconds)}s</span>
        </div>
      ))}
    </div>
  )
}

interface Props { projectId?: string | null }

export function ExecutionProgressPanel({ projectId }: Props) {
  const pid = projectId ?? ''
  const pipeline = useStore((s) => s.pipelines[pid] ?? null)
  const taskExecutions = useStore((s) => s.taskExecutionsByProject[pid] ?? {})
  const stuckTasks = useStore((s) => s.stuckTasksByProject[pid] ?? [])
  const setStuckTasks = useStore((s) => s.setStuckTasks)
  const setStuckPolling = useStore((s) => s.setStuckPolling)
  const [expandedTask, setExpandedTask] = useState<string | null>(null)

  useEffect(() => {
    if (!pipeline || pipeline.status !== 'running') return

    let pollTimer: ReturnType<typeof setInterval> | null = null

    const pollExecutions = async () => {
      try {
        const stuck = await getStuckTasks(120)
        setStuckTasks(pid, stuck)
        setStuckPolling(pid, true)
      } catch {
        setStuckPolling(pid, false)
      }
    }

    pollTimer = setInterval(pollExecutions, 15000)
    pollExecutions()

    return () => {
      if (pollTimer) clearInterval(pollTimer)
      setStuckPolling(pid, false)
    }
  }, [pipeline?.id, pipeline?.status])

  const taskIds = Object.keys(taskExecutions)

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-ultramodern-border">
        <div className="text-sm font-semibold text-primary flex items-center justify-between">
          <span>执行进度</span>
          {pipeline && (
            <span className={`text-[10px] px-2 py-0.5 rounded-full ${
              pipeline.status === 'running' ? 'bg-accent-green/20 text-accent-green' :
              pipeline.status === 'paused' ? 'bg-accent-orange/20 text-accent-orange' :
              'bg-muted text-secondary'
            }`}>
              {pipeline.status === 'running' ? '运行中' : pipeline.status === 'paused' ? '已暂停' : pipeline.status}
            </span>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-3">
        {taskIds.length === 0 && stuckTasks.length === 0 && (
          <div className="text-xs text-secondary text-center py-8">
            暂无运行中的任务
          </div>
        )}

        {taskIds.map((taskId) => {
          const exec = taskExecutions[taskId]
          if (!exec) return null
          const isStuck = stuckTasks.some((s) => s.task_id === taskId)
          const isExpanded = expandedTask === taskId

          return (
            <div
              key={taskId}
              className="rounded-lg border border-ultramodern-border bg-ultramodern-surface-alt overflow-hidden"
            >
              <button
                className="w-full px-3 py-2 flex items-center justify-between hover:bg-ultramodern-hover transition-colors text-left"
                onClick={() => setExpandedTask(isExpanded ? null : taskId)}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <HeartbeatIndicator lastHeartbeat={exec.last_heartbeat} status={isStuck ? 'stuck' : exec.status} />
                    <span className="text-xs text-primary font-mono truncate">
                      {taskId.slice(0, 12)}...
                    </span>
                  </div>
                  <div className="mt-1">
                    <StepProgressBar current={exec.current_step} total={exec.total_steps} status={isStuck ? 'stuck' : exec.status} />
                  </div>
                </div>
                <svg
                  className={`w-3 h-3 text-secondary transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {isExpanded && (
                <div className="px-3 pb-3 pt-1 border-t border-ultramodern-border space-y-2">
                  {isStuck && (
                    <div className="text-[10px] text-accent-red bg-accent-red/5 rounded p-2">
                      任务疑似卡死 — 超过 120 秒无响应
                    </div>
                  )}
                  <div className="flex gap-2">
                    {exec.status === 'paused' && (
                      <button
                        className="flex-1 py-1 text-[10px] rounded bg-accent-green/20 text-accent-green hover:bg-accent-green/30 transition-colors"
                        onClick={() => retryTask(taskId, true)}
                      >
                        从检查点恢复
                      </button>
                    )}
                    {isStuck && (
                      <button
                        className="flex-1 py-1 text-[10px] rounded bg-accent-orange/20 text-accent-orange hover:bg-accent-orange/30 transition-colors"
                        onClick={() => retryTask(taskId, true)}
                      >
                        强制重试
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          )
        })}

        <MiniStuckList stuck={stuckTasks} />
      </div>
    </div>
  )
}
