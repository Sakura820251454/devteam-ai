import { useState, useEffect } from 'react'
import { getSettings, updateSettings, listWorkspaces } from '../lib/api'
import type { AppSettings } from '../lib/api'

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
  onSettingsChanged: (workspaceRoot: string) => void
}

export default function SettingsModal({ isOpen, onClose, onSettingsChanged }: SettingsModalProps) {
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [workspaceRoot, setWorkspaceRoot] = useState('')
  const [workspaceCount, setWorkspaceCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (isOpen) {
      setMessage('')
      loadSettings()
    }
  }, [isOpen])

  const loadSettings = async () => {
    setLoading(true)
    try {
      const s = await getSettings()
      setSettings(s)
      setWorkspaceRoot(s.workspace_root)

      const wss = await listWorkspaces()
      setWorkspaceCount(wss.length)
    } catch (err) {
      setMessage('加载设置失败，后端是否已启动？')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!workspaceRoot.trim()) return
    setSaving(true)
    setMessage('')
    try {
      const updated = await updateSettings(workspaceRoot.trim())
      setSettings(updated)
      setWorkspaceRoot(updated.workspace_root)
      setMessage('已保存')
      onSettingsChanged(updated.workspace_root_resolved || updated.workspace_root)
      setTimeout(() => setMessage(''), 2000)
    } catch (err) {
      setMessage('保存失败，请检查后端连接')
    } finally {
      setSaving(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm animate-fade-in">
      <div className="w-[480px] bg-background-panel border border-white/10 rounded-xl shadow-panel animate-slide-up">
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-white/5 flex items-center gap-3">
          <span className="text-lg">⚙</span>
          <div>
            <h3 className="text-sm font-medium text-surface-100">系统设置</h3>
            <p className="text-xs text-surface-400">管理工作区存储路径</p>
          </div>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-accent-cyan" />
            </div>
          ) : (
            <>
              {/* Workspace root */}
              <div>
                <label className="block text-xs text-surface-400 mb-1.5">
                  项目工作区存储路径
                </label>
                <input
                  type="text"
                  value={workspaceRoot}
                  onChange={(e) => setWorkspaceRoot(e.target.value)}
                  placeholder="例如: D:/MyProjects 或 ~/devteam-workspaces"
                  className="w-full bg-background-input border border-white/10 rounded-lg px-3 py-2 text-sm text-surface-100 placeholder:text-surface-600 focus:outline-none focus:border-accent-cyan transition-colors font-mono"
                />
                <p className="text-xs text-surface-600 mt-1">
                  支持相对路径（相对于 DevTeam-AI 目录）和绝对路径
                </p>
              </div>

              {/* Current resolved path */}
              {settings?.workspace_root_resolved && (
                <div className="bg-background-card border border-white/5 rounded-lg p-3">
                  <div className="text-xs text-surface-500 mb-1">当前实际路径</div>
                  <div className="text-sm text-surface-200 font-mono break-all">
                    {settings.workspace_root_resolved}
                  </div>
                </div>
              )}

              {/* Info */}
              <div className="bg-background-card border border-white/5 rounded-lg p-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-surface-400">已有项目</span>
                  <span className="text-surface-200 font-mono">{workspaceCount} 个工作区</span>
                </div>
              </div>

              {/* Message */}
              {message && (
                <div className={`text-sm px-3 py-2 rounded-lg ${
                  message === '已保存'
                    ? 'bg-accent-green/10 text-accent-green border border-accent-green/20'
                    : 'bg-accent-red/10 text-accent-red border border-accent-red/20'
                }`}>
                  {message}
                </div>
              )}
            </>
          )}
        </div>

        {/* Actions */}
        <div className="px-5 py-3 border-t border-white/5 flex justify-between items-center">
          <span className="text-xs text-surface-500">
            修改后新项目将使用新路径，已有项目不受影响
          </span>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-surface-400 hover:text-surface-200 transition-colors"
            >
              关闭
            </button>
            <button
              onClick={handleSave}
              disabled={saving || !workspaceRoot.trim()}
              className={`px-5 py-2 text-sm rounded-lg font-medium transition-all ${
                saving || !workspaceRoot.trim()
                  ? 'bg-surface-600 text-surface-400 cursor-not-allowed'
                  : 'bg-accent-cyan text-white hover:bg-accent-cyan/90 shadow-glow-cyan'
              }`}
            >
              {saving ? '保存中...' : '保存'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
