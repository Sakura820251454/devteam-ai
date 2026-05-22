import { useState, useEffect } from 'react'
import { listWorkspaces, type WorkspaceInfo } from '../lib/api'

interface OpenProjectDialogProps {
  isOpen: boolean
  onClose: () => void
  onOpen: (workspace: WorkspaceInfo) => void
  existingProjectIds: string[]
}

const STATUS_LABELS: Record<string, { text: string; color: string }> = {
  running: { text: '运行中', color: 'bg-green-500' },
  paused: { text: '已暂停', color: 'bg-yellow-500' },
  completed: { text: '已完成', color: 'bg-blue-500' },
  failed: { text: '失败', color: 'bg-red-500' },
  cancelled: { text: '已取消', color: 'bg-slate-500' },
}

function formatDate(iso: string): string {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso.slice(0, 10)
  }
}

export default function OpenProjectDialog({ isOpen, onClose, onOpen, existingProjectIds }: OpenProjectDialogProps) {
  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen) return
    setLoading(true)
    setError(null)
    listWorkspaces()
      .then((data) => {
        setWorkspaces(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message || '无法连接到后端服务')
        setLoading(false)
      })
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-slate-900 border border-white/10 rounded-xl w-full max-w-lg max-h-[70vh] flex flex-col shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
          <h2 className="text-base font-semibold text-slate-100">打开已有项目</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors text-lg">
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {loading && (
            <div className="flex flex-col items-center gap-3 py-12 text-slate-500">
              <div className="animate-spin w-6 h-6 border-2 border-cyan-400 border-t-transparent rounded-full" />
              <span className="text-sm">正在加载已有项目...</span>
            </div>
          )}

          {error && !loading && (
            <div className="flex flex-col items-center gap-3 py-12 text-slate-400">
              <span className="text-3xl opacity-40">⚠️</span>
              <p className="text-sm text-center">{error}</p>
              <button
                onClick={() => {
                  setLoading(true)
                  setError(null)
                  listWorkspaces()
                    .then((data) => { setWorkspaces(data); setLoading(false) })
                    .catch((err) => { setError(err.message || '无法连接到后端服务'); setLoading(false) })
                }}
                className="px-4 py-1.5 bg-slate-700 text-slate-300 rounded text-sm hover:bg-slate-600 transition-colors"
              >
                重试
              </button>
            </div>
          )}

          {!loading && !error && workspaces.length === 0 && (
            <div className="flex flex-col items-center gap-3 py-12 text-slate-500">
              <span className="text-3xl opacity-40">📁</span>
              <p className="text-sm">暂无已有项目</p>
              <button
                onClick={onClose}
                className="px-4 py-1.5 bg-cyan-600/20 text-cyan-400 rounded text-sm hover:bg-cyan-600/30 transition-colors"
              >
                + 启动新项目
              </button>
            </div>
          )}

          {!loading && !error && workspaces.map((ws) => {
            const statusInfo = STATUS_LABELS[ws.status] || STATUS_LABELS.running
            const isAlreadyOpen = existingProjectIds.includes(ws.id)

            return (
              <div
                key={ws.id}
                className="bg-slate-800/50 border border-white/5 rounded-lg p-4 hover:border-white/10 transition-colors"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-sm font-medium text-slate-200 truncate">{ws.name}</h3>
                      <span className={`w-2 h-2 rounded-full shrink-0 ${statusInfo.color}`} />
                      <span className="text-xs text-slate-500">{statusInfo.text}</span>
                    </div>
                    {ws.description && (
                      <p className="text-xs text-slate-500 line-clamp-2 mb-2">{ws.description}</p>
                    )}
                    <div className="flex items-center gap-3 text-xs text-slate-600">
                      <span>{(ws.agents || []).length} 个 Agent</span>
                      <span>{(ws.stages || []).length} 个阶段</span>
                      {ws.created_at && <span>{formatDate(ws.created_at)}</span>}
                    </div>
                  </div>
                  <button
                    onClick={() => onOpen(ws)}
                    disabled={isAlreadyOpen}
                    className={`px-3 py-1.5 rounded text-xs font-medium shrink-0 transition-colors ${
                      isAlreadyOpen
                        ? 'bg-slate-700 text-slate-500 cursor-default'
                        : 'bg-cyan-600/20 text-cyan-400 hover:bg-cyan-600/30'
                    }`}
                  >
                    {isAlreadyOpen ? '已打开' : '打开'}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
