import { useState, useRef, useEffect } from 'react'
import { useStore, type Agent } from '../lib/store'
import { gsap, useGSAP } from '../lib/gsap'
import { startSimulation } from '../lib/simulation'
import PipelineView from '../components/PipelineView'
import AgentTeamPanel from '../components/AgentTeamPanel'
import EventTimeline from '../components/EventTimeline'
import CostPanel from '../components/CostPanel'
import TerminalLog from '../components/TerminalLog'
import InterventionPanel from '../components/InterventionPanel'
import AgentChatPanel from '../components/AgentChatPanel'
import CreateProjectModal from '../components/CreateProjectModal'
import StageReviewModal from '../components/StageReviewModal'
import type { StageDef } from '../components/StageReviewModal'
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
  const initFromBackend = useStore((s) => s.initFromBackend)
  const fetchTeamSuggestion = useStore((s) => s.fetchTeamSuggestion)
  const storeError = useStore((s) => s.error)

  const [activeTab, setActiveTab] = useState<SideTab>('agents')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showAgentConfig, setShowAgentConfig] = useState(false)
  const [pendingProject, setPendingProject] = useState<{
    name: string
    description: string
    template: { id: string; name: string; stages: Array<{ key: string; label: string; description?: string; expected_artifact: string; parallel_group: string | null }> } | null
  }>({ name: '', description: '', template: null })
  const [showSettings, setShowSettings] = useState(false)
  const [showOpenDialog, setShowOpenDialog] = useState(false)
  const [showStageReview, setShowStageReview] = useState(false)
  const [pendingAgents, setPendingAgents] = useState<Agent[]>([])
  const [pendingTeamConfig, setPendingTeamConfig] = useState<{ strategy: string; coordinatorId?: string }>({ strategy: 'sequential' })
  const [toastError, setToastError] = useState<string | null>(null)
  const stopSimRefs = useRef<Record<string, () => void>>({})
  const headerRef = useRef<HTMLElement>(null)
  const mainRef = useRef<HTMLDivElement>(null)

  // 显示 store 中的错误（自动消失）
  useEffect(() => {
    if (storeError) {
      setToastError(storeError)
      const timer = setTimeout(() => setToastError(null), 8000)
      return () => clearTimeout(timer)
    }
  }, [storeError])

  // Detect backend LLM mode on mount
  useEffect(() => {
    fetchLlmMode()
  }, [fetchLlmMode])

  // 页面加载时从后端恢复项目列表和当前项目数据（刷新后保持状态）
  useEffect(() => {
    initFromBackend()
  }, [initFromBackend])

  // 页面加载入场动画
  useGSAP(() => {
    const tl = gsap.timeline({ defaults: { ease: 'power2.out' } })

    // Logo 从左滑入
    tl.from(headerRef.current, {
      y: -48,
      opacity: 0,
      duration: 0.5,
    })

    // 主内容区淡入 + 上移
    tl.from(
      mainRef.current,
      {
        opacity: 0,
        y: 20,
        duration: 0.6,
      },
      '-=0.2',
    )
  })

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

  const proceedWithConfig = (
    agents: Agent[],
    teamConfig: { strategy: string; coordinatorId?: string },
    confirmedStages?: StageDef[],
  ) => {
    startProject(pendingProject.name, pendingProject.description, agents, teamConfig, pendingProject.template, confirmedStages)

    setTimeout(() => {
      const state = useStore.getState()
      const pid = state.activeProjectId
      if (pid) {
        if (state.llmMode === 'real') {
          const agentIds = agents.map((a) => a.id)
          state.startRealPipeline(pid, pendingProject.name, pendingProject.description, agentIds, teamConfig, confirmedStages)
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

    setPendingAgents(agents)
    setPendingTeamConfig(teamConfig)
    setShowAgentConfig(false)
    setShowStageReview(true)
  }

  const handleStageConfirmed = (confirmedStages: StageDef[]) => {
    setShowStageReview(false)
    proceedWithConfig(pendingAgents, pendingTeamConfig, confirmedStages)
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

  const handleOpenExisting = async (workspace: WorkspaceInfo) => {
    // Check if already loaded in this session
    const existingProject = useStore.getState().projects.find(p => p.id === workspace.id)
    if (existingProject) {
      switchProject(workspace.id)
      setShowOpenDialog(false)
      return
    }

    // Restore in-memory state from workspace
    restoreProjectFromWorkspace(workspace)
    setShowOpenDialog(false)

    // For completed/failed projects, just show the archived state — no need to resume
    if (workspace.status === 'completed' || workspace.status === 'failed') return

    const state = useStore.getState()
    const pid = workspace.id

    if (state.llmMode === 'real') {
      // Find the existing pipeline — try active first, then list by project
      try {
        const { getActivePipeline, listPipelines } = await import('../lib/api')
        let backendPipeline: Record<string, unknown> | null = null

        const activePipeline = await getActivePipeline(pid)
        if (activePipeline?.id) {
          backendPipeline = activePipeline
        } else {
          // Pipeline was removed from _active_pipelines after close — look it up by project
          const { pipelines: projectPipelines } = await listPipelines(pid) as { pipelines: Array<Record<string, unknown>> }
          if (projectPipelines?.length > 0) {
            backendPipeline = projectPipelines[0]
          }
        }

        if (backendPipeline?.id) {
          const pipelineId = backendPipeline.id as string
          const backendStatus = backendPipeline.status as string
          if (backendStatus === 'paused') {
            state.setPipeline(pid, {
              ...(state.pipelines[pid] || {}),
              id: pipelineId,
              status: 'paused',
              current_stage: backendPipeline.current_stage as string,
              progress: backendPipeline.progress as number,
            } as any)
          } else if (backendStatus === 'running') {
            state.startPolling(pid, pipelineId)
          }
        }
      } catch (err) {
        console.warn('恢复流水线轮询失败:', err)
      }
    } else {
      // Mock mode: restart simulation
      stopSimRefs.current[pid]?.()
      stopSimRefs.current[pid] = startSimulation(pid, workspace.name, workspace.description)
    }
  }

  const handleResetProject = async () => {
    if (!activeProjectId) {
      resetProject()
      return
    }

    // 停止模拟（如果存在）
    stopSimRefs.current[activeProjectId]?.()
    delete stopSimRefs.current[activeProjectId]

    // 真实模式：通知后端关闭流水线（保存状态 + 停止执行）
    const state = useStore.getState()
    if (state.llmMode === 'real') {
      const pipeline = state.pipelines[activeProjectId]
      if (pipeline?.id && (pipeline.status === 'running' || pipeline.status === 'paused')) {
        try {
          const { closePipeline } = await import('../lib/api')
          await closePipeline(pipeline.id)
        } catch (err) {
          console.warn('关闭后端流水线失败:', err)
        }
      }
    }

    // skipBackend=true: 已经 await 了 closePipeline，不再重复调用
    await useStore.getState().closeProject(activeProjectId, true)
  }

  return (
    <div className="flex flex-col h-screen bg-background text-surface-50 overflow-hidden">
      {/* Top Bar */}
      <header ref={headerRef} className="h-12 bg-background-panel border-b border-white/5 flex items-center px-4 shrink-0 z-10">
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
      <div ref={mainRef} className="flex-1 flex overflow-hidden">
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

      {/* Agent Config Modal — Step 2+3: AI team suggestion + user confirmation */}
      <AgentConfigModal
        isOpen={showAgentConfig}
        onClose={() => setShowAgentConfig(false)}
        onAgentsConfigured={handleAgentsConfigured}
        projectDescription={pendingProject.description}
        fetchTeamSuggestion={fetchTeamSuggestion}
      />

      {/* Stage Review Modal — Step 4: Stage confirmation gate */}
      <StageReviewModal
        isOpen={showStageReview}
        onClose={() => setShowStageReview(false)}
        onConfirmed={handleStageConfirmed}
        projectName={pendingProject.name}
        projectDescription={pendingProject.description}
        templateId={pendingProject.template?.id || 'custom'}
        templateStages={
          pendingProject.template?.stages && pendingProject.template.stages.length > 0
            ? pendingProject.template.stages
            : [
                { key: 'requirement_analysis', label: '需求分析', description: '分析需求', expected_artifact: '需求文档.md', parallel_group: null },
                { key: 'task_breakdown', label: '任务拆解', description: '拆解任务', expected_artifact: '任务清单.md', parallel_group: null },
                { key: 'coding', label: '编码实现', description: '实现代码', expected_artifact: '代码/', parallel_group: null },
                { key: 'review', label: '代码审查', description: '审查代码', expected_artifact: '审查报告.md', parallel_group: null },
                { key: 'testing', label: '测试验证', description: '测试功能', expected_artifact: '测试报告.md', parallel_group: null },
                { key: 'delivery', label: '交付部署', description: '部署上线', expected_artifact: '交付包/', parallel_group: null },
              ]
        }
      />

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

      {/* Error Toast */}
      {toastError && (
        <div className="fixed bottom-4 right-4 z-50 max-w-md bg-accent-red/90 text-white px-4 py-3 rounded-lg shadow-lg animate-slide-up">
          <div className="flex items-start gap-2">
            <span className="text-sm mt-0.5">⚠️</span>
            <div className="flex-1">
              <div className="text-sm font-medium">启动失败</div>
              <div className="text-xs text-white/80 mt-1">{toastError}</div>
            </div>
            <button
              onClick={() => {
                setToastError(null)
                useStore.getState().error = null
              }}
              className="text-white/60 hover:text-white text-xs"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
