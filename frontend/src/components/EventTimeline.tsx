import { useEffect, useRef } from 'react'
import { useStore } from '../lib/store'
import type { TimelineEvent } from '../lib/store'

const IMPORTANCE_STYLES: Record<string, string> = {
  normal: 'border-white/5',
  important: 'border-accent-purple/30 bg-accent-purple/5',
  critical: 'border-accent-red/30 bg-accent-red/5',
}

const TYPE_ICONS: Record<string, string> = {
  decision: '◆',
  action: '▶',
  message: '💬',
  status_change: '↻',
  artifact: '⚡',
}

function EventCard({ event }: { event: TimelineEvent }) {
  const color = event.agentColor || '#8b949e'

  return (
    <div className={`rounded-lg border px-3 py-3 animate-slide-up ${IMPORTANCE_STYLES[event.importance]}`}>
      <div className="flex items-start gap-2.5">
        {event.agentId && (
          <div
            className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 mt-0.5"
            style={{ backgroundColor: `${color}25`, color }}
          >
            {event.agentName?.substring(0, 2) || '?'}
          </div>
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            {event.agentName && (
              <span className="text-sm font-medium text-surface-200">{event.agentName}</span>
            )}
            <span className="text-xs text-surface-500">
              {TYPE_ICONS[event.type]} {event.type === 'decision' ? '决策' :
               event.type === 'action' ? '行动' :
               event.type === 'message' ? '消息' :
               event.type === 'status_change' ? '状态变更' : '产出物'}
            </span>
          </div>

          <p className="text-sm text-surface-200 leading-relaxed">{event.content}</p>

          {event.detail && (
            <p className="text-xs text-surface-400 mt-1 leading-relaxed">{event.detail}</p>
          )}

          <div className="flex items-center justify-between mt-1.5">
            <span className="text-xs text-surface-500 font-mono">
              {new Date(event.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
            {event.importance === 'critical' && (
              <span className="text-xs text-accent-red font-medium">⚠ 需关注</span>
            )}
            {event.importance === 'important' && (
              <span className="text-xs text-accent-purple font-medium">● 重要</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

interface Props { projectId?: string | null }

export default function EventTimeline({ projectId }: Props) {
  const events = useStore((s) => projectId ? s.eventsByProject[projectId] ?? [] : [])
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events.length])

  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-surface-500">
        <div className="text-3xl mb-3">📜</div>
        <p className="text-sm">暂无事件</p>
        <p className="text-xs mt-1">项目启动后将实时显示关键事件</p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto p-3 space-y-2">
      {/* Timeline line */}
      <div className="relative">
        <div className="absolute left-[20px] top-0 bottom-0 w-px bg-white/5" />

        {events.map((event) => (
          <div key={event.id} className="relative pl-9 pb-2">
            <div
              className="absolute left-[16px] top-3 w-2.5 h-2.5 rounded-full border-2 border-background-panel shrink-0"
              style={{
                backgroundColor: event.agentColor || '#8b949e',
              }}
            />
            <EventCard event={event} />
          </div>
        ))}
      </div>
      <div ref={endRef} />
    </div>
  )
}
