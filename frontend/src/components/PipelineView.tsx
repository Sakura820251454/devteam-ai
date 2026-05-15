import { useStore } from '../lib/store'
import type { PipelineStage, Agent, Pipeline } from '../lib/store'
import TaskBoard from './TaskBoard'

const STAGE_ICONS: Record<string, { icon: string; desc: string }> = {
  requirement_analysis: { icon: '🔍', desc: 'Agent 分析需求、澄清模糊点、产出需求文档' },
  task_breakdown: { icon: '📋', desc: '将需求拆解为可执行的技术任务' },
  coding: { icon: '⚡', desc: 'Agent 并行编码、实时协作' },
  review: { icon: '🔎', desc: 'Agent 交叉审查代码质量与规范' },
  testing: { icon: '🧪', desc: '自动化测试执行与问题修复' },
  delivery: { icon: '🚀', desc: '代码合并、构建、部署' },
  research: { icon: '📖', desc: '收集和整理相关领域资料' },
  analysis: { icon: '📊', desc: '对收集的数据进行深度分析' },
  drafting: { icon: '✍️', desc: '撰写报告初稿' },
  internal_review: { icon: '👁️', desc: '团队内部评审和修改建议' },
  finalize: { icon: '✅', desc: '定稿并交付最终版本' },
}

function getStageMeta(key: string) {
  return STAGE_ICONS[key] || { icon: '📌', desc: `执行 "${key}" 阶段` }
}

const STAGE_STATUS_STYLES: Record<string, { bg: string; border: string; dot: string; text: string }> = {
  pending:    { bg: 'bg-transparent', border: 'border-white/5', dot: 'bg-surface-600', text: 'text-surface-500' },
  active:     { bg: 'bg-accent-cyan/5', border: 'border-accent-cyan/30 animate-pulse-border', dot: 'bg-accent-cyan animate-pulse-glow', text: 'text-surface-100' },
  completed:  { bg: 'bg-accent-green/5', border: 'border-accent-green/20', dot: 'bg-accent-green', text: 'text-surface-200' },
  blocked:    { bg: 'bg-accent-red/5', border: 'border-accent-red/30', dot: 'bg-accent-red animate-blink', text: 'text-surface-100' },
}

function StageConnector({ status }: { status: string }) {
  return (
    <div className="flex justify-center py-1">
      <div className={`w-0.5 h-8 rounded-full transition-all duration-700 ${
        status === 'active' ? 'bg-gradient-to-b from-accent-cyan to-surface-600' :
        status === 'completed' ? 'bg-accent-green' : 'bg-surface-700'
      }`} />
    </div>
  )
}

function AgentAvatar({ agent }: { agent: Agent }) {
  return (
    <div
      className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border border-white/10"
      style={{ backgroundColor: `${agent.avatarColor}25`, color: agent.avatarColor }}
      title={`${agent.name} (${agent.status})`}
    >
      {agent.name.substring(0, 2)}
    </div>
  )
}

function StageCard({
  stage, isSelected, onClick, agents, compact,
}: {
  stage: PipelineStage; isSelected: boolean; onClick: () => void; agents: Agent[]; compact?: boolean
}) {
  const meta = getStageMeta(stage.key)
  const styles = STAGE_STATUS_STYLES[stage.status] || STAGE_STATUS_STYLES.pending
  const stageAgents = agents.filter((a) => stage.assignedAgents.includes(a.id))

  const formatDuration = (start?: string, end?: string) => {
    if (!start) return null
    const min = Math.round(((end ? new Date(end).getTime() : Date.now()) - new Date(start).getTime()) / 60000)
    if (min < 1) return '< 1min'
    if (min < 60) return `${min}min`
    return `${Math.floor(min / 60)}h ${min % 60}m`
  }

  const duration = formatDuration(stage.startedAt, stage.completedAt)

  if (compact) {
    return (
      <div
        onClick={onClick}
        className={`rounded-lg border px-3 py-2.5 cursor-pointer transition-all duration-200 group ${
          styles.bg} ${styles.border} ${
          isSelected ? 'shadow-glow-cyan border-accent-cyan' : 'hover:border-white/10'
        }`}
      >
        <div className="flex items-center gap-2">
          <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${styles.dot}`} />
          <span className="text-sm">{meta.icon}</span>
          <span className={`text-sm font-medium ${styles.text}`}>{stage.label || stage.key}</span>
          <span className={`ml-auto text-xs px-1.5 py-0.5 rounded ${
            stage.status === 'active' ? 'bg-accent-cyan/20 text-accent-cyan' :
            stage.status === 'completed' ? 'bg-accent-green/20 text-accent-green' :
            stage.status === 'blocked' ? 'bg-accent-red/20 text-accent-red' : 'text-surface-500'
          }`}>
            {stage.status === 'active' ? '进行中' : stage.status === 'completed' ? '✓' : stage.status === 'blocked' ? '!' : ''}
          </span>
        </div>
        {duration && <div className="text-xs text-surface-600 font-mono mt-1 ml-7">⏱ {duration}</div>}
      </div>
    )
  }

  return (
    <div
      onClick={onClick}
      className={`relative rounded-xl border p-5 cursor-pointer transition-all duration-300 group ${
        styles.bg} ${styles.border} ${
        isSelected ? 'shadow-glow-cyan' : 'hover:border-white/10 hover:bg-white/[0.02]'
      }`}
    >
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-3 h-3 rounded-full shrink-0 ${styles.dot} relative`}>
          {stage.status === 'active' && <div className="absolute inset-0 rounded-full bg-accent-cyan animate-ping opacity-30" />}
        </div>
        <span className="text-xl">{meta.icon}</span>
        <h3 className={`font-semibold text-base ${styles.text}`}>{stage.label || stage.key}</h3>
        <span className={`ml-auto text-xs px-2.5 py-0.5 rounded-full font-medium ${
          stage.status === 'active' ? 'bg-accent-cyan/20 text-accent-cyan' :
          stage.status === 'completed' ? 'bg-accent-green/20 text-accent-green' :
          stage.status === 'blocked' ? 'bg-accent-red/20 text-accent-red' : 'bg-surface-600/50 text-surface-500'
        }`}>
          {stage.status === 'active' ? '进行中' : stage.status === 'completed' ? '已完成' : stage.status === 'blocked' ? '阻塞' : '待开始'}
        </span>
      </div>

      <p className="text-sm text-surface-400 mb-3 leading-relaxed">{meta.desc}</p>

      {stageAgents.length > 0 && (
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs text-surface-500">负责:</span>
          {stageAgents.map((a) => <AgentAvatar key={a.id} agent={a} />)}
        </div>
      )}

      {stage.artifacts.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {stage.artifacts.map((artifact) => (
            <span key={artifact} className="text-xs px-2 py-0.5 rounded bg-white/5 text-surface-400">
              {artifact}
            </span>
          ))}
        </div>
      )}

      {duration && <div className="text-xs text-surface-500 font-mono">⏱ {duration}</div>}

      {stage.status !== 'pending' && (
        <div className="absolute top-4 right-4 text-surface-600 group-hover:text-accent-cyan transition-colors text-sm opacity-0 group-hover:opacity-100">
          {isSelected ? '收起 ▲' : '展开 ▼'}
        </div>
      )}
    </div>
  )
}

function ProjectStats({ pipeline }: { pipeline: Pipeline }) {
  const completed = pipeline.stages.filter((s) => s.status === 'completed').length
  const total = pipeline.stages.length
  const inProgress = pipeline.stages.filter((s) => s.status === 'active').length
  const blocked = pipeline.stages.filter((s) => s.status === 'blocked').length
  const elapsed = pipeline.stages[0]?.startedAt
    ? Math.round((Date.now() - new Date(pipeline.stages[0].startedAt).getTime()) / 60000)
    : 0

  return (
    <div className="grid grid-cols-2 gap-3">
      <div className="bg-background-card border border-white/5 rounded-lg p-4">
        <div className="text-xs text-surface-500 mb-1">阶段进度</div>
        <div className="text-2xl font-bold text-surface-100 font-mono">{completed}/{total}</div>
        <div className="text-xs text-surface-500 mt-1">已完成阶段</div>
      </div>
      <div className="bg-background-card border border-white/5 rounded-lg p-4">
        <div className="text-xs text-surface-500 mb-1">已用时间</div>
        <div className="text-2xl font-bold text-surface-100 font-mono">
          {elapsed < 60 ? `${elapsed}m` : `${Math.floor(elapsed / 60)}h ${elapsed % 60}m`}
        </div>
        <div className="text-xs text-surface-500 mt-1">自项目启动</div>
      </div>
      <div className="bg-background-card border border-white/5 rounded-lg p-4">
        <div className="text-xs text-surface-500 mb-1">进行中</div>
        <div className="text-2xl font-bold text-accent-orange font-mono">{inProgress}</div>
        <div className="text-xs text-surface-500 mt-1">个阶段正在执行</div>
      </div>
      <div className="bg-background-card border border-white/5 rounded-lg p-4">
        <div className="text-xs text-surface-500 mb-1">阻塞</div>
        <div className={`text-2xl font-bold font-mono ${blocked > 0 ? 'text-accent-red' : 'text-surface-100'}`}>
          {blocked}
        </div>
        <div className="text-xs text-surface-500 mt-1">{blocked > 0 ? '需关注' : '无阻塞'}</div>
      </div>
    </div>
  )
}

interface PipelineViewProps {
  onCreateProject: () => void
  onOpenExample: () => void
}

export default function PipelineView({ onCreateProject, onOpenExample }: PipelineViewProps) {
  const {
    pipeline, selectedStage, agents,
    setSelectedStage,
    addLog,
  } = useStore()

  const handleStageClick = (stageKey: string) => {
    if (selectedStage === stageKey) {
      setSelectedStage(null)
    } else {
      setSelectedStage(stageKey)
      const stage = pipeline?.stages.find((s) => s.key === stageKey)
      addLog({ level: 'info', source: 'pipeline', message: `进入阶段: ${stage?.label || stageKey}` })
    }
  }

  if (!pipeline) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-surface-500 p-8">
        <div className="text-6xl mb-6 opacity-30">⚙️</div>
        <h2 className="text-xl font-semibold text-surface-300 mb-2">等待项目启动</h2>
        <p className="text-sm text-surface-500 mb-6">创建一个项目，Agent 团队将自动接管开发流程</p>
        <div className="flex gap-3">
          <button
            onClick={onCreateProject}
            className="px-5 py-2.5 bg-accent-cyan text-white rounded-lg font-medium text-sm hover:bg-accent-cyan/90 transition-all shadow-glow-cyan"
          >
            🚀 启动新项目
          </button>
          <button
            onClick={onOpenExample}
            className="px-5 py-2.5 bg-surface-600 text-surface-300 rounded-lg font-medium text-sm hover:bg-surface-500 transition-all"
          >
            📂 打开示例项目
          </button>
        </div>
      </div>
    )
  }

  const activeStageIdx = pipeline.stages.findIndex((s) => s.key === pipeline.currentStage)

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-5 py-3 border-b border-white/5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className={`w-2.5 h-2.5 rounded-full ${
            pipeline.status === 'running' ? 'bg-accent-green animate-pulse' :
            pipeline.status === 'paused' ? 'bg-accent-orange' :
            pipeline.status === 'completed' ? 'bg-accent-cyan' :
            pipeline.status === 'failed' ? 'bg-accent-red' : 'bg-surface-400'
          }`} />
          <span className="text-sm font-medium text-surface-200">{pipeline.name}</span>
          <span className="text-surface-600">·</span>
          <span className="text-sm text-surface-500">阶段 {activeStageIdx + 1}/{pipeline.stages.length}</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-28 h-1.5 bg-surface-600 rounded-full overflow-hidden">
            <div className="h-full bg-accent-cyan rounded-full transition-all duration-700" style={{ width: `${Math.round(pipeline.progress * 100)}%` }} />
          </div>
          <span className="text-sm text-surface-500 font-mono">{Math.round(pipeline.progress * 100)}%</span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden flex">
        {selectedStage ? (
          <>
            <div className="w-64 shrink-0 border-r border-white/5 overflow-y-auto p-3 space-y-1.5">
              <div className="text-xs text-surface-500 px-1 mb-2 uppercase tracking-wider">Pipeline</div>
              {pipeline.stages.map((stage: PipelineStage) => (
                <StageCard
                  key={stage.key}
                  stage={stage}
                  isSelected={selectedStage === stage.key}
                  onClick={() => handleStageClick(stage.key)}
                  agents={agents}
                  compact
                />
              ))}
            </div>

            <div className="flex-1 overflow-y-auto">
              <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between">
                <div>
                  <span className="text-sm font-medium text-surface-200">
                    {pipeline.stages.find((s) => s.key === selectedStage)?.label || selectedStage}
                  </span>
                  <span className="text-sm text-surface-500 ml-2">· 任务看板</span>
                </div>
                <button
                  onClick={() => setSelectedStage(null)}
                  className="text-xs text-surface-500 hover:text-surface-200 transition-colors"
                >
                  ✕ 关闭
                </button>
              </div>
              <TaskBoard />
            </div>
          </>
        ) : (
          <div className="flex-1 overflow-y-auto">
            <div className="flex gap-6 p-6 h-full">
              <div className="flex-1 max-w-[600px] space-y-0">
                {pipeline.stages.map((stage: PipelineStage, idx: number) => (
                  <div key={stage.key}>
                    <StageCard
                      stage={stage}
                      isSelected={false}
                      onClick={() => handleStageClick(stage.key)}
                      agents={agents}
                    />
                    {idx < pipeline.stages.length - 1 && <StageConnector status={stage.status} />}
                  </div>
                ))}
              </div>

              <div className="flex-1 space-y-4 pt-1">
                <ProjectStats pipeline={pipeline!} />

                <div className="bg-background-card border border-white/5 rounded-lg p-4">
                  <div className="text-xs text-surface-500 mb-3 uppercase tracking-wider">团队状态</div>
                  <div className="space-y-2">
                    {agents.slice(0, 6).map((agent) => (
                      <div key={agent.id} className="flex items-center gap-2.5">
                        <div className="w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold" style={{ backgroundColor: `${agent.avatarColor}25`, color: agent.avatarColor }}>
                          {agent.name.substring(0, 2)}
                        </div>
                        <span className="text-sm text-surface-300 flex-1">{agent.name}</span>
                        <span className={`text-xs ${
                          agent.status === 'idle' ? 'text-surface-500' :
                          agent.status === 'working' ? 'text-accent-green' :
                          agent.status === 'thinking' ? 'text-accent-purple' :
                          'text-accent-orange'
                        }`}>
                          {agent.status === 'idle' ? '空闲' :
                           agent.status === 'working' ? '工作中' :
                           agent.status === 'thinking' ? '思考中' :
                           agent.status === 'waiting' ? '等待中' : '阻塞'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-background-card border border-white/5 rounded-lg p-4">
                  <div className="text-xs text-surface-500 mb-2 uppercase tracking-wider">关于 Pipeline</div>
                  <p className="text-sm text-surface-400 leading-relaxed">
                    Pipeline 展示项目从需求到交付的完整生命周期。每个阶段由 Agent 自主推进，你只需观察和必要时介入。
                  </p>
                  <div className="mt-3 flex gap-2 text-xs">
                    <span className="flex items-center gap-1 text-surface-500">
                      <span className="w-2 h-2 rounded-full bg-accent-cyan animate-pulse" /> 进行中
                    </span>
                    <span className="flex items-center gap-1 text-surface-500">
                      <span className="w-2 h-2 rounded-full bg-accent-green" /> 已完成
                    </span>
                    <span className="flex items-center gap-1 text-surface-500">
                      <span className="w-2 h-2 rounded-full bg-accent-red" /> 阻塞
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
