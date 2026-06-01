import { useState, useEffect } from 'react'
import { adjustPipelineTemplate } from '../lib/api'
import type { AdjustmentSuggestions, StageAdjustment } from '../lib/api'

export interface StageDef {
  key: string
  label: string
  description?: string
  expected_artifact?: string
  parallel_group?: string | null
}

interface StageReviewModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirmed: (confirmedStages: StageDef[]) => void
  projectName: string
  projectDescription: string
  templateId: string
  templateStages: StageDef[]
}

const STAGE_COLORS = [
  'bg-accent-cyan/20 text-accent-cyan',
  'bg-accent-green/20 text-accent-green',
  'bg-accent-purple/20 text-accent-purple',
  'bg-accent-orange/20 text-accent-orange',
  'bg-accent-cyan/20 text-accent-cyan',
  'bg-accent-green/20 text-accent-green',
  'bg-accent-purple/20 text-accent-purple',
  'bg-accent-orange/20 text-accent-orange',
]

export default function StageReviewModal({
  isOpen,
  onClose,
  onConfirmed,
  projectName,
  projectDescription,
  templateId,
  templateStages,
}: StageReviewModalProps) {
  const [stages, setStages] = useState<StageDef[]>(templateStages)
  const [showAdjust, setShowAdjust] = useState(false)
  const [adjustLoading, setAdjustLoading] = useState(false)
  const [adjustResult, setAdjustResult] = useState<AdjustmentSuggestions | null>(null)
  const [adjustApplied, setAdjustApplied] = useState(false)
  const [confirmLoading, setConfirmLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setStages(templateStages)
      setShowAdjust(false)
      setAdjustResult(null)
      setAdjustApplied(false)
    }
  }, [isOpen, templateStages])

  if (!isOpen) return null

  const handleAiSuggest = async () => {
    setShowAdjust(true)
    if (adjustResult || adjustLoading) return
    setAdjustLoading(true)
    try {
      const result = await adjustPipelineTemplate(
        projectName,
        projectDescription,
        templateId || 'custom',
      )
      setAdjustResult(result)
    } catch {
      setAdjustResult(null)
    } finally {
      setAdjustLoading(false)
    }
  }

  const handleApplySuggestion = () => {
    if (!adjustResult?.final_stages?.length) return
    const newStages: StageDef[] = adjustResult.final_stages.map((s: StageAdjustment) => ({
      key: s.key,
      label: s.label,
      description: s.description || '',
      expected_artifact: s.expected_artifact || '',
      parallel_group: s.parallel_group || null,
    }))
    setStages(newStages)
    setAdjustApplied(true)
  }

  const handleConfirm = () => {
    setConfirmLoading(true)
    onConfirmed(stages)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm animate-fade-in">
      <div className="w-[680px] bg-background-panel border border-white/10 rounded-xl shadow-panel animate-slide-up max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-white/5 flex items-center gap-3 shrink-0">
          <span className="text-xl">📋</span>
          <div>
            <h3 className="text-sm font-medium text-surface-100">确认 Pipeline 阶段</h3>
            <p className="text-xs text-surface-400">审查并调整阶段配置，确认后 Agent 将按此流程执行</p>
          </div>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4 overflow-y-auto flex-1">
          {/* Current stages preview */}
          <div>
            <label className="block text-xs text-surface-400 mb-2">
              当前阶段流程（{stages.length} 个阶段）
            </label>
            <div className="flex items-center gap-1.5 flex-wrap p-3 bg-surface-600/10 rounded-lg border border-white/5">
              {stages.map((stage, i) => (
                <span key={stage.key} className="inline-flex items-center gap-1">
                  {i > 0 && <span className="text-surface-600 text-xs">→</span>}
                  <span
                    className={`text-xs px-2 py-1 rounded ${
                      stage.parallel_group
                        ? 'bg-accent-purple/20 text-accent-purple'
                        : STAGE_COLORS[i % STAGE_COLORS.length]
                    }`}
                    title={stage.expected_artifact || stage.description}
                  >
                    {stage.label}
                    {stage.parallel_group && (
                      <span className="ml-1 text-accent-purple/60" title="可并行执行">‖</span>
                    )}
                  </span>
                </span>
              ))}
            </div>
            {/* Expected artifacts */}
            <div className="text-xs text-surface-500 mt-1.5">
              产出物：{stages.map(s => s.expected_artifact).filter(Boolean).join(' · ') || '由 Agent 自行产出'}
            </div>
          </div>

          {/* AI Suggest button */}
          {!showAdjust && (
            <button
              onClick={handleAiSuggest}
              className="w-full px-4 py-2.5 bg-accent-purple/10 border border-accent-purple/20 rounded-lg text-sm text-accent-purple hover:bg-accent-purple/20 transition-colors"
            >
              🤖 AI 建议调整阶段
            </button>
          )}

          {/* AI Adjustment Panel */}
          {showAdjust && (
            <div className="p-4 bg-accent-purple/5 border border-accent-purple/20 rounded-lg space-y-3">
              {adjustLoading ? (
                <div className="flex items-center gap-2 text-sm text-surface-400">
                  <div className="animate-spin w-4 h-4 border-2 border-accent-purple border-t-transparent rounded-full" />
                  AI 正在分析项目需求，建议 Pipeline 阶段调整...
                </div>
              ) : adjustResult ? (
                <>
                  {/* Analysis */}
                  <div className="text-sm text-surface-200">{adjustResult.analysis}</div>

                  {/* Changes summary */}
                  {adjustResult.changes && (
                    <div className="flex flex-wrap gap-1.5 text-xs">
                      {(adjustResult.changes.add?.length ?? 0) > 0 && (
                        <span className="px-2 py-0.5 rounded bg-accent-green/20 text-accent-green">
                          +{adjustResult.changes.add!.length} 新增
                        </span>
                      )}
                      {(adjustResult.changes.remove?.length ?? 0) > 0 && (
                        <span className="px-2 py-0.5 rounded bg-accent-red/20 text-accent-red">
                          -{adjustResult.changes.remove!.length} 移除
                        </span>
                      )}
                      {(adjustResult.changes.reorder?.length ?? 0) > 0 && (
                        <span className="px-2 py-0.5 rounded bg-accent-cyan/20 text-accent-cyan">
                          ↔ {adjustResult.changes.reorder!.length} 调整顺序
                        </span>
                      )}
                      {(adjustResult.changes.rename?.length ?? 0) > 0 && (
                        <span className="px-2 py-0.5 rounded bg-accent-orange/20 text-accent-orange">
                          ✎ {adjustResult.changes.rename!.length} 重命名
                        </span>
                      )}
                      {!adjustResult.changes.add?.length && !adjustResult.changes.remove?.length &&
                       !adjustResult.changes.reorder?.length && !adjustResult.changes.rename?.length && (
                        <span className="text-surface-400">无需调整，当前阶段已是最佳方案</span>
                      )}
                    </div>
                  )}

                  {/* Suggested stages */}
                  {adjustResult.final_stages?.length > 0 && (
                    <div>
                      <div className="text-xs text-surface-500 mb-1.5">建议阶段：</div>
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {adjustResult.final_stages.map((s: StageAdjustment, i: number) => (
                          <span key={s.key || i} className="inline-flex items-center gap-1">
                            {i > 0 && <span className="text-surface-600 text-xs">→</span>}
                            <span className="text-xs px-2 py-0.5 rounded bg-surface-600/50 text-surface-300">
                              {s.label}
                            </span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Apply / Retry */}
                  <div className="flex items-center gap-2">
                    {!adjustApplied ? (
                      <>
                        <button
                          onClick={handleApplySuggestion}
                          disabled={!adjustResult?.final_stages?.length}
                          className="text-xs px-3 py-1.5 rounded bg-accent-cyan/20 text-accent-cyan hover:bg-accent-cyan/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          应用建议
                        </button>
                        <span className="text-xs text-surface-500">点击应用 AI 建议的阶段方案</span>
                      </>
                    ) : (
                      <span className="text-xs text-accent-green">
                        ✓ 已应用 — 上方阶段列表已更新
                      </span>
                    )}
                    <button
                      onClick={handleAiSuggest}
                      className="text-xs px-2 py-1 rounded text-surface-400 hover:text-surface-200 transition-colors ml-auto"
                    >
                      重新分析
                    </button>
                  </div>
                </>
              ) : (
                <div className="text-sm text-surface-400">
                  LLM 分析失败，请重试
                  <button
                    onClick={handleAiSuggest}
                    className="ml-2 text-accent-purple hover:underline"
                  >
                    重试
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-white/5 flex justify-between items-center shrink-0">
          <span className="text-xs text-surface-500">
            {stages.length} 个阶段 · 确认后 Agent 将按此流程执行
          </span>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-surface-400 hover:text-surface-200 transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleConfirm}
              disabled={confirmLoading || stages.length === 0}
              className={`px-5 py-2 text-sm rounded-lg font-medium transition-all ${
                stages.length > 0
                  ? 'bg-accent-cyan text-white hover:bg-accent-cyan/90 shadow-glow-cyan'
                  : 'bg-surface-600 text-surface-400 cursor-not-allowed'
              }`}
            >
              {confirmLoading ? '启动中...' : '确认并启动'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
