import { useState, useRef, useEffect } from 'react'
import { useStore, type Agent } from '../lib/store'
import { startSimulation } from '../lib/simulation'
import PipelineView from '../components/PipelineView'
import AgentTeamPanel from '../components/AgentTeamPanel'
import EventTimeline from '../components/EventTimeline'
import CostPanel from '../components/CostPanel'
import TerminalLog from '../components/TerminalLog'
import InterventionPanel from '../components/InterventionPanel'
import AgentChatPanel from '../components/AgentChatPanel'
import CreateProjectModal from '../components/CreateProjectModal'
import AgentConfigModal from '../components/AgentConfigModal'
import SettingsModal from '../components/SettingsModal'
import ProjectSwitcher from '../components/ProjectSwitcher'
import OpenProjectDialog from '../components/OpenProjectDialog'
import type { WorkspaceInfo } from '../lib/api'

type SideTab = 'agents' | 'chat' | 'timeline' | 'cost'

export default function Home() {
  const projects = useStore((s) => s.projects)
  const activeProjectId = useStore((s) => s.activeProjectId)
  const pipeline = useStore((s) => activeProjectId ? s.pipelines[activeProjectId] ?? null : null)
  const sidePanelOpen = useStore((s) => s.sidePanelOpen)
  const terminalExpanded = useStore((s) => s.terminalExpanded)
  const terminalFullscreen = useStore((s) => s.terminalFullscreen)
  const isConnected = useStore((s) => s.isConnected)
  const isLoading = useStore((s) => s.isLoading)
  const setSidePanelOpen = useStore((s) => s.setSidePanelOpen)
  const setTerminalExpanded = useStore((s) => s.setTerminalExpanded)
  const startProject = useStore((s) => s.startProject)
  const restoreProjectFromWorkspace = useStore((s) => s.restoreProjectFromWorkspace)
  const resetProject = useStore((s) => s.resetProject)
  const setWorkspacePath = useStore((s) => s.setWorkspacePath)
  const switchProject = useStore((s) => s.switchProject)
  const fetchLlmMode = useStore((s) => s.fetchLlmMode)
  const strategyRecommendation = useStore((s) => s.strategyRecommendation)
  const fetchStrategyRecommendation = useStore((s) => s.fetchStrategyRecommendation)
  const setStrategyRecommendation = useStore((s) => s.setStrategyRecommendation)

  const [activeTab, setActiveTab] = useState<SideTab>('agents')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showAgentConfig, setShowAgentConfig] = useState(false)
  const [pendingProject, setPendingProject] = useState<{
    name: string
    description: string
    template: { id: string; name: string; stages: Array<{ key: string; label: string; expected_artifact: string; parallel_group: string | null }> } | null
  }>({ name: '', description: '', template: null })
  const [showSettings, setShowSettings] = useState(false)
  const [showOpenDialog, setShowOpenDialog] = useState(false)
  const [showStrategyConfirm, setShowStrategyConfirm] = useState(false)
  const [pendingStrategyConfig, setPendingStrategyConfig] = useState<{
    agents: Agent[]
    teamConfig: { strategy: string; coordinatorId?: string }
  } | null>(null)
  const stopSimRefs = useRef<Record<string, () => void>>({})

  // Detect backend LLM mode on mount
  useEffect(() => {
    fetchLlmMode()
  }, [fetchLlmMode])

  const progress = pipeline ? Math.round(pipeline.progress * 100) : 0
  const statusLabel =
    !isConnected ? '未连接' :
    isLoading ? '加载中...' :
    pipeline?.status === 'running' ? '运行中' :
    pipeline?.status === 'paused' ? '已暂停' :
    pipeline?.status === 'completed' ? '已完成' :
    pipeline?.status === 'failed' ? '失败' :
    activeProjectId ? '空闲' : '就绪'

  const statusColor =
    !isConnected ? 'bg-surface-400' :
    isLoading ? 'bg-accent-orange animate-pulse' :
    pipeline?.status === 'running' ? 'bg-accent-green animate-pulse' :
    pipeline?.status === 'paused' ? 'bg-accent-orange' :
    pipeline?.status === 'completed' ? 'bg-accent-cyan' :
    pipeline?.status === 'failed' ? 'bg-accent-red' :
    'bg-surface-400'

  const handleCreateProject = (name: string, description: string, template: any) => {
    setPendingProject({ name, description, template })
    setShowCreateModal(false)
    setShowAgentConfig(true)
  }

  const proceedWithConfig = (agents: Agent[], teamConfig: { strategy: string; coordinatorId?: string }) => {
    startProject(pendingProject.name, pendingProject.description, agents, teamConfig, pendingProject.template)

    setTimeout(() => {
      const state = useStore.getState()
      const pid = state.activeProjectId
      if (pid) {
        if (state.llmMode === 'real') {
          const agentIds = agents.map((a) => a.id)
          state.startRealPipeline(pid, pendingProject.name, pendingProject.description, agentIds, teamConfig)
        } else {
          stopSimRefs.current[pid]?.()
          stopSimRefs.current[pid] = startSimulation(pid, pendingProject.name, pendingProject.description)
        }
      }
    }, 0)
  }

  const handleAgentsConfigured = async (selectedAgents: Array<{
    id: string; name: string; type: string; description: string;
    avatar_color: string; capabilities: string[];
    llm_config?: { provider: string; model: string; temperature: number; max_tokens?: number }
  }>, teamConfig: { strategy: string; coordinatorId?: string }) => {
    const agents: Agent[] = selectedAgents.map((a) => ({
      id: a.id,
      name: a.name,
      role: '团队成员',
      status: 'idle' as const,
      avatarColor: a.avatar_color,
      description: a.description,
      llm_config: a.llm_config,
    }))

    if (teamConfig.strategy === 'auto') {
      // 自动策略 — 先获取 LLM 推荐，弹确认框
      setPendingStrategyConfig({ agents, teamConfig })
      setShowStrategyConfirm(true)
      const agentIds = agents.map((a) => a.id)
      fetchStrategyRecommendation(
        pendingProject.name,
        pendingProject.description,
        agentIds,
      )
      return
    }

    setShowAgentConfig(false)
    proceedWithConfig(agents, teamConfig)
  }

  const handleStrategyConfirmed = (overrideStrategy?: string) => {
    if (!pendingStrategyConfig) return

    const finalConfig = { ...pendingStrategyConfig.teamConfig }
    if (overrideStrategy) {
      finalConfig.strategy = overrideStrategy
    } else if (strategyRecommendation) {
      finalConfig.strategy = strategyRecommendation.recommended_strategy
      if (strategyRecommendation.suggested_coordinator && !finalConfig.coordinatorId) {
        finalConfig.coordinatorId = strategyRecommendation.suggested_coordinator
      }
    }

    setShowStrategyConfirm(false)
    setPendingStrategyConfig(null)
    setShowAgentConfig(false)
    setStrategyRecommendation(null)

    proceedWithConfig(pendingStrategyConfig.agents, finalConfig)
  }

  const handleOpenExample = () => {
    const name = '示例：博客平台开发'
    const desc = '开发一个支持 Markdown 的技术博客平台，包含文章发布、标签分类、评论系统、RSS 订阅、全文搜索。前后端分离架构，FastAPI + React + PostgreSQL。'
    startProject(name, desc)

    setTimeout(() => {
      const state = useStore.getState()
      const pid = state.activeProjectId
      if (pid) {
        if (state.llmMode === 'real') {
          const defaultAgentIds = (state.agentsByProject[pid] || []).map((a) => a.id)
          const tc = state.teamConfigs[pid] || undefined
          state.startRealPipeline(pid, name, desc, defaultAgentIds, tc)
        } else {
          stopSimRefs.current[pid]?.()
          stopSimRefs.current[pid] = startSimulation(pid, name, desc)
        }
      }
    }, 0)
  }

  const handleOpenExisting = (workspace: WorkspaceInfo) => {
    // Check if already loaded
    const existingProject = useStore.getState().projects.find(p => p.id === workspace.id)
    if (existingProject) {
      switchProject(workspace.id)
      setShowOpenDialog(false)
      return
    }

    // Restore in-memory state from workspace
    restoreProjectFromWorkspace(workspace)
    setShowOpenDialog(false)

    // Start simulation if project is not completed (only in mock mode)
    if (workspace.status !== 'completed') {
      setTimeout(() => {
        const state = useStore.getState()
        const pid = state.activeProjectId
        if (pid) {
          if (state.llmMode === 'real') {
            const agentIds = (state.agentsByProject[pid] || []).map((a) => a.id)
            const tc = state.teamConfigs[pid] || undefined
            state.startRealPipeline(pid, workspace.name, workspace.description, agentIds, tc)
          } else {
            stopSimRefs.current[pid]?.()
            stopSimRefs.current[pid] = startSimulation(pid, workspace.name, workspace.description)
          }
        }
      }, 0)
    }
  }

  const handleResetProject = () => {
    if (activeProjectId) {
      stopSimRefs.current[activeProjectId]?.()
      delete stopSimRefs.current[activeProjectId]
    }
    resetProject()
  }

  return (
    <div className="flex flex-col h-screen bg-background text-surface-50 overflow-hidden">
      {/* Top Bar */}
      <header className="h-12 bg-background-panel border-b border-white/5 flex items-center px-4 shrink-0 z-10">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <h1 className="text-sm font-semibold text-accent-cyan tracking-wide shrink-0">
            DevTeam-AI
          </h1>

          {/* Project Switcher */}
          <ProjectSwitcher onNewProject={() => setShowCreateModal(true)} onOpenExisting={() => setShowOpenDialog(true)} />

          {pipeline && (
            <button
              onClick={handleResetProject}
              className="text-xs text-surface-500 hover:text-accent-red transition-colors ml-2 shrink-0"
              title="关闭当前项目"
            >
              ✕
            </button>
          )}
        </div>

        <div className="flex items-center gap-4">
          {/* Pipeline progress bar */}
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

          {/* New project button */}
          {projects.length > 0 && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-3 py-1 bg-accent-cyan/20 text-accent-cyan rounded text-xs font-medium hover:bg-accent-cyan/30 transition-colors"
            >
              + 新项目
            </button>
          )}

          {/* Settings */}
          <button
            onClick={() => setShowSettings(true)}
            className="px-2 py-1 rounded text-sm text-surface-400 hover:text-surface-200 hover:bg-white/5 transition-colors"
            title="系统设置"
          >
            ⚙
          </button>

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
            projectId={activeProjectId}
            onCreateProject={() => setShowCreateModal(true)}
            onOpenExample={handleOpenExample}
            onOpenExisting={() => setShowOpenDialog(true)}
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
              {activeTab === 'agents' && <AgentTeamPanel projectId={activeProjectId} />}
              {activeTab === 'chat' && <AgentChatPanel projectId={activeProjectId} />}
              {activeTab === 'timeline' && <EventTimeline projectId={activeProjectId} />}
              {activeTab === 'cost' && <CostPanel projectId={activeProjectId} />}
            </div>
          </aside>
        )}
      </div>

      {/* Terminal Log */}
      {terminalExpanded && !terminalFullscreen && (
        <div className="h-48 bg-background-input border-t border-white/5 shrink-0 animate-slide-up">
          <TerminalLog projectId={activeProjectId} />
        </div>
      )}

      {/* Terminal Fullscreen Overlay */}
      {terminalFullscreen && (
        <div className="fixed inset-0 z-50 bg-background animate-fade-in">
          <TerminalLog projectId={activeProjectId} />
        </div>
      )}

      {/* Create Project Modal */}
      <CreateProjectModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={handleCreateProject}
      />

      {/* Agent Config Modal — step 2 after project creation */}
      <AgentConfigModal
        isOpen={showAgentConfig}
        onClose={() => setShowAgentConfig(false)}
        onAgentsConfigured={handleAgentsConfigured}
      />

      {/* Strategy Confirmation Dialog — shown when auto strategy selected */}
      {showStrategyConfirm && strategyRecommendation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 animate-fade-in">
          <div className="bg-background-panel border border-white/10 rounded-xl p-6 w-full max-w-lg shadow-2xl">
            <h2 className="text-lg font-semibold text-white mb-2">AI 策略推荐</h2>
            <p className="text-sm text-surface-400 mb-4">
              LLM 根据项目需求和你选择的 {pendingStrategyConfig?.agents.length || 0} 位团队成员，
              推荐了以下协作策略：
            </p>

            {/* Recommendation Card */}
            <div className="bg-background-input rounded-lg p-4 mb-3 border border-accent-cyan/20">
              <div className="flex items-center justify-between mb-2">
                <span className="text-accent-cyan font-medium text-sm">
                  {strategyRecommendation.recommended_strategy === 'sequential' ? '📋 顺序执行' :
                   strategyRecommendation.recommended_strategy === 'hierarchical' ? '🏗️ 层级委派' :
                   strategyRecommendation.recommended_strategy === 'discussion' ? '💬 圆桌讨论' : '—'}
                </span>
                <span className="text-xs text-surface-500">
                  置信度: {Math.round(strategyRecommendation.confidence * 100)}%
                </span>
              </div>
              <div className="w-full bg-surface-600 rounded-full h-1.5 mb-2">
                <div
                  className="h-full bg-accent-cyan rounded-full transition-all"
                  style={{ width: `${strategyRecommendation.confidence * 100}%` }}
                />
              </div>
              <p className="text-xs text-surface-300 leading-relaxed">
                {strategyRecommendation.reasoning}
              </p>
              {strategyRecommendation.suggested_coordinator && (
                <p className="text-xs text-accent-orange mt-2">
                  建议协调者: {strategyRecommendation.suggested_coordinator}
                </p>
              )}
            </div>

            {/* Alternatives */}
            {strategyRecommendation.alternative_strategies.length > 0 && (
              <div className="mb-4">
                <p className="text-xs text-surface-500 mb-2">其他可选策略</p>
                {strategyRecommendation.alternative_strategies.map((alt, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      handleStrategyConfirmed(alt.strategy)
                    }}
                    className="block w-full text-left text-xs text-surface-300 hover:bg-white/5 rounded px-3 py-1.5 mb-1 transition-colors"
                  >
                    <span className="text-surface-400">
                      {alt.strategy === 'sequential' ? '📋 顺序执行' :
                       alt.strategy === 'hierarchical' ? '🏗️ 层级委派' :
                       alt.strategy === 'discussion' ? '💬 圆桌讨论' : alt.strategy}
                    </span>
                    {' — '}{alt.reason}
                  </button>
                ))}
              </div>
            )}

            {/* Action buttons */}
            <div className="flex gap-3">
              <button
                onClick={() => handleStrategyConfirmed()}
                className="flex-1 px-4 py-2 bg-accent-cyan text-black font-medium rounded-lg hover:bg-accent-cyan/80 transition-colors text-sm"
              >
                确认使用推荐策略
              </button>
              <button
                onClick={() => {
                  setShowStrategyConfirm(false)
                  setPendingStrategyConfig(null)
                  setStrategyRecommendation(null)
                }}
                className="px-4 py-2 text-surface-400 hover:text-white transition-colors text-sm"
              >
                返回修改
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Open Project Dialog */}
      <OpenProjectDialog
        isOpen={showOpenDialog}
        onClose={() => setShowOpenDialog(false)}
        onOpen={handleOpenExisting}
        existingProjectIds={projects.map(p => p.id)}
      />

      {/* Settings Modal */}
      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        onSettingsChanged={(path) => {
          if (activeProjectId) setWorkspacePath(activeProjectId, path)
        }}
      />

      {/* Intervention FAB */}
      <InterventionPanel projectId={activeProjectId} />
    </div>
  )
}
