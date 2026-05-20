import { useEffect, useRef, useState } from 'react'
import { useStore } from '../lib/store'
const LEVEL_COLORS: Record<string, string> = {
  info: 'text-surface-300',
  success: 'text-accent-green',
  warn: 'text-accent-orange',
  error: 'text-accent-red',
  debug: 'text-accent-purple',
}

const LEVEL_PREFIXES: Record<string, string> = {
  info: '·',
  success: '✓',
  warn: '⚠',
  error: '✗',
  debug: '›',
}

interface Props { projectId?: string | null }

export default function TerminalLog({ projectId }: Props) {
  const pid = projectId ?? ''
  const logs = useStore((s) => s.logsByProject[pid] ?? [])
  const terminalFullscreen = useStore((s) => s.terminalFullscreen)
  const setTerminalExpanded = useStore((s) => s.setTerminalExpanded)
  const setTerminalFullscreen = useStore((s) => s.setTerminalFullscreen)
  const clearLogs = useStore((s) => s.clearLogs)

  const containerRef = useRef<HTMLDivElement>(null)
  const [filter, setFilter] = useState<string>('all')
  const [autoScroll, setAutoScroll] = useState(true)

  const filteredLogs = filter === 'all'
    ? logs
    : logs.filter((l) => l.level === filter)

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [filteredLogs.length, autoScroll])

  const handleScroll = () => {
    if (!containerRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current
    setAutoScroll(scrollHeight - scrollTop - clientHeight < 40)
  }

  if (logs.length === 0 && !terminalFullscreen) {
    return (
      <div className="flex items-center justify-between h-full px-4 text-surface-500 terminal-text">
        <div className="flex items-center gap-3">
          <span className="text-accent-green">&gt;_</span>
          <span>终端就绪 — 等待 Agent 活动...</span>
        </div>
        <button
          onClick={() => setTerminalFullscreen(true)}
          className="text-xs text-surface-500 hover:text-surface-300 transition-colors"
        >
          ⛶ 全屏
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Terminal toolbar */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-surface-700/30 border-b border-white/5 shrink-0">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-accent-red/60" />
          <span className="w-2.5 h-2.5 rounded-full bg-accent-orange/60" />
          <span className="w-2.5 h-2.5 rounded-full bg-accent-green/60" />
          <span className="text-xs text-surface-500 font-mono ml-2">terminal</span>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Filter buttons */}
          {['all', 'info', 'warn', 'error', 'debug'].map((lvl) => (
            <button
              key={lvl}
              onClick={() => setFilter(lvl)}
              className={`text-xs px-1.5 py-0.5 rounded font-mono transition-colors ${
                filter === lvl
                  ? 'bg-white/10 text-surface-200'
                  : 'text-surface-500 hover:text-surface-300'
              }`}
            >
              {lvl === 'all' ? 'ALL' : lvl.toUpperCase()}
            </button>
          ))}

          <span className="text-surface-600 mx-1">|</span>

          <button
            onClick={() => clearLogs(pid)}
            className="text-xs text-surface-500 hover:text-surface-300 font-mono transition-colors"
          >
            clear
          </button>

          <button
            onClick={() => {
              if (terminalFullscreen) {
                setTerminalFullscreen(false)
              } else {
                setTerminalFullscreen(true)
              }
            }}
            className="text-xs text-surface-500 hover:text-surface-300 font-mono transition-colors"
          >
            {terminalFullscreen ? '⛶ exit' : '⛶ full'}
          </button>

          {!terminalFullscreen && (
            <button
              onClick={() => setTerminalExpanded(false)}
              className="text-xs text-surface-500 hover:text-surface-300 font-mono ml-1"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Log content */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-2 terminal-text"
      >
        {filteredLogs.length === 0 ? (
          <div className="text-surface-600 px-2">暂无日志...</div>
        ) : (
          filteredLogs.map((log) => (
            <div key={log.id} className="flex leading-relaxed hover:bg-white/[0.02] px-1 rounded-sm">
              <span className="text-surface-600 shrink-0 select-none mr-2">
                {new Date(log.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
              <span className={`shrink-0 mr-1.5 ${LEVEL_COLORS[log.level]}`}>
                {LEVEL_PREFIXES[log.level]}
              </span>
              <span className="text-surface-500 mr-1.5 shrink-0">[{log.source}]</span>
              <span className={`${LEVEL_COLORS[log.level]} break-all`}>{log.message}</span>
            </div>
          ))
        )}
      </div>

      {/* Auto-scroll indicator */}
      {!autoScroll && filteredLogs.length > 0 && (
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2">
          <button
            onClick={() => {
              setAutoScroll(true)
              containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight, behavior: 'smooth' })
            }}
            className="text-xs bg-accent-cyan/20 text-accent-cyan px-2 py-0.5 rounded-full font-mono"
          >
            ↓ 跟随输出
          </button>
        </div>
      )}

      {/* Empty state is shown inline above, no footer needed for full terminal */}
      {!terminalFullscreen && logs.length > 0 && (
        <div className="px-3 py-1 border-t border-white/5 shrink-0 flex items-center justify-between text-xs text-surface-600 font-mono">
          <span>{filteredLogs.length} entries</span>
          <span>{filter !== 'all' ? `filter: ${filter}` : ''}</span>
        </div>
      )}
    </div>
  )
}
