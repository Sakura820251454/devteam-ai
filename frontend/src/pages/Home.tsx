import { useState, useRef } from 'react'
import { useStore } from '../lib/store'
import { startSimulation } from '../lib/simulation'
import PipelineView from '../components/PipelineView'
import AgentTeamPanel from '../components/AgentTeamPanel'
import EventTimeline from '../components/EventTimeline'
import CostPanel from '../components/CostPanel'
import TerminalLog from '../components/TerminalLog'
import InterventionPanel from '../components/InterventionPanel'
import AgentChatPanel from '../components/AgentChatPanel'
import CreateProjectModal from '../components/CreateProjectModal'

type SideTab = 'agents' | 'chat' | 'timeline' | 'cost'

export default function Home() {
  const {
    pipeline,
    sidePanelOpen,
    terminalExpanded,
    terminalFullscreen,
    isConnected,
    isLoading,
    setSidePanelOpen,
    setTerminalExpanded,
    startProject,
    resetProject,
  } = useStore()

  const [activeTab, setActiveTab] = useState<SideTab>('agents')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const stopSimRef = useRef<(() => void) | null>(null)

  const progress = pipeline ? Math.round(pipeline.progress * 100) : 0
  const statusLabel =
    !isConnected ? '未连接' :
    isLoading ? '加载中...' :
    pipeline?.status === 'running' ? '运行中' :
    pipeline?.status === 'paused' ? '已暂停' :
    pipeline?.status === 'completed' ? '已完成' :
    pipeline?.status === 'failed' ? '失败' :
    '空闲'

  const statusColor =
    !isConnected ? 'bg-surface-400' :
    isLoading ? 'bg-accent-orange animate-pulse' :
    pipeline?.status === 'running' ? 'bg-accent-green animate-pulse' :
    pipeline?.status === 'paused' ? 'bg-accent-orange' :
    pipeline?.status === 'completed' ? 'bg-accent-cyan' :
    pipeline?.status === 'failed' ? 'bg-accent-red' :
    'bg-surface-400'

  const handleCreateProject = (name: string, description: string) => {
    stopSimRef.current?.()
    startProject(name, description)
    stopSimRef.current = startSimulation(name, description)
  }

  const handleOpenExample = () => {
    stopSimRef.current?.()
    const name = '示例：博客平台开发'
    const desc = '开发一个支持 Markdown 的技术博客平台，包含文章发布、标签分类、评论系统、RSS 订阅、全文搜索。前后端分离架构，FastAPI + React + PostgreSQL。'
    startProject(name, desc)
    stopSimRef.current = startSimulation(name, desc)
  }

  const handleResetProject = () => {
    stopSimRef.current?.()
    stopSimRef.current = null
    resetProject()
  }

  return (
    <div className="flex flex-col h-screen bg-background text-surface-50 overflow-hidden">
      {/* Top Bar */}
      <header className="h-12 bg-background-panel border-b border-white/5 flex items-center px-4 shrink-0 z-10">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <h1 className="text-sm font-semibold text-accent-cyan tracking-wide">
            DevTeam-AI
          </h1>
          <span className="text-surface-300 text-xs">|</span>
          <span className="text-surface-200 text-sm font-medium truncate">
            {pipeline?.name || '未创建项目'}
          </span>
          {pipeline && (
            <button
              onClick={handleResetProject}
              className="text-xs text-surface-500 hover:text-accent-red transition-colors ml-2"
              title="重置项目"
            >
              ✕
            </button>
          )}
        </div>

        <div className="flex items-center gap-4">
          {/* Pipeline progress bar (compact) */}
          {pipeline && (
            <div className="flex items-center gap-2">
              <div className="w-32 h-1.5 bg-surface-600 rounded-full overflow-hidden">
                <div
                  className="h-full bg-accent-cyan rounded-full transition-all duration-700"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className="text-xs text-surface-300 font-mono tabular-nums">
                {progress}%
              </span>
            </div>
          )}

          {/* Status indicator */}
          <div className="flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-full ${statusColor}`} />
            <span className="text-xs text-surface-300">{statusLabel}</span>
          </div>

          {/* New project button — always visible */}
          {!pipeline && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-3 py-1 bg-accent-cyan/20 text-accent-cyan rounded text-xs font-medium hover:bg-accent-cyan/30 transition-colors"
            >
              + 新项目
            </button>
          )}

          {/* Terminal toggle */}
          <button
            onClick={() => setTerminalExpanded(!terminalExpanded)}
            className={`px-2.5 py-1 rounded text-xs font-mono transition-colors ${
              terminalExpanded
                ? 'bg-accent-cyan/20 text-accent-cyan'
                : 'text-surface-300 hover:text-surface-100 hover:bg-white/5'
            }`}
          >
            &gt;_
          </button>

          {/* Side panel toggle */}
          <button
            onClick={() => setSidePanelOpen(!sidePanelOpen)}
            className={`px-2 py-1 rounded text-xs transition-colors ${
              sidePanelOpen
                ? 'text-surface-200'
                : 'text-surface-400 hover:text-surface-200'
            }`}
            title={sidePanelOpen ? '收起面板' : '展开面板'}
          >
            {sidePanelOpen ? '▸' : '◂'}
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Pipeline — 主视图 */}
        <div className="flex-1 overflow-hidden">
          <PipelineView
            onCreateProject={() => setShowCreateModal(true)}
            onOpenExample={handleOpenExample}
          />
        </div>

        {/* Side Panels */}
        {sidePanelOpen && (
          <aside className="w-80 bg-background-panel border-l border-white/5 flex flex-col shrink-0 animate-slide-in-right">
            {/* Tab Bar */}
            <div className="flex border-b border-white/5 shrink-0">
              {([
                ['agents', 'Agent'],
                ['chat', '对话'],
                ['timeline', '时间线'],
                ['cost', '成本'],
              ] as [SideTab, string][]).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setActiveTab(key)}
                  className={`flex-1 py-2.5 text-xs font-medium transition-colors relative ${
                    activeTab === key
                      ? 'text-accent-cyan'
                      : 'text-surface-400 hover:text-surface-200'
                  }`}
                >
                  {label}
                  {activeTab === key && (
                    <div className="absolute bottom-0 left-1/4 right-1/4 h-0.5 bg-accent-cyan rounded-full" />
                  )}
                </button>
              ))}
            </div>

            {/* Panel Content */}
            <div className="flex-1 overflow-hidden">
              {activeTab === 'agents' && <AgentTeamPanel />}
              {activeTab === 'chat' && <AgentChatPanel />}
              {activeTab === 'timeline' && <EventTimeline />}
              {activeTab === 'cost' && <CostPanel />}
            </div>
          </aside>
        )}
      </div>

      {/* Terminal Log */}
      {terminalExpanded && !terminalFullscreen && (
        <div className="h-48 bg-background-input border-t border-white/5 shrink-0 animate-slide-up">
          <TerminalLog />
        </div>
      )}

      {/* Terminal Fullscreen Overlay */}
      {terminalFullscreen && (
        <div className="fixed inset-0 z-50 bg-background animate-fade-in">
          <TerminalLog />
        </div>
      )}

      {/* Create Project Modal */}
      <CreateProjectModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={handleCreateProject}
      />

      {/* Intervention FAB */}
      <InterventionPanel />
    </div>
  )
}
