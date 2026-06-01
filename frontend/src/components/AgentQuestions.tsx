import { useState } from 'react'
import type { AgentQuestion } from '../lib/api'
import { respondToAgent } from '../lib/api'

interface AgentQuestionsProps {
  projectId: string
  pipelineId: string
  questions: AgentQuestion[]
  onResponded: () => void
}

export default function AgentQuestions({
  projectId: _projectId,
  pipelineId,
  questions,
  onResponded,
}: AgentQuestionsProps) {
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [submitting, setSubmitting] = useState<Record<number, boolean>>({})
  const [answered, setAnswered] = useState<Record<number, boolean>>({})

  if (questions.length === 0) return null

  const handleSubmit = async (index: number) => {
    const answer = answers[index]?.trim()
    if (!answer) return

    setSubmitting(s => ({ ...s, [index]: true }))
    try {
      const q = questions[index]
      await respondToAgent(pipelineId, q.task_id, answer)
      setAnswered(s => ({ ...s, [index]: true }))
      onResponded()
    } catch (err) {
      console.error('答复Agent失败:', err)
    } finally {
      setSubmitting(s => ({ ...s, [index]: false }))
    }
  }

  return (
    <div className="px-5 py-3 border-b border-accent-orange/30 bg-accent-orange/5 space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-sm">❓</span>
        <span className="text-sm font-medium text-accent-orange">
          Agent 需要你的澄清（{questions.length} 个问题）
        </span>
        <span className="text-xs text-surface-500">
          Pipeline 已暂停，等待你的答复
        </span>
      </div>

      {questions.map((q, i) => (
        <div
          key={`${q.task_id || 'analysis'}-${i}`}
          className={`p-3 rounded-lg border transition-all ${
            answered[i]
              ? 'border-accent-green/30 bg-accent-green/5 opacity-60'
              : 'border-accent-orange/20 bg-background-card'
          }`}
        >
          {/* Agent info */}
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs text-surface-500">
              {q.agent_name}
            </span>
            {q.task_title && (
              <>
                <span className="text-surface-600">·</span>
                <span className="text-xs text-surface-500">{q.task_title}</span>
              </>
            )}
          </div>

          {/* Question */}
          <div className="text-sm text-surface-200 mb-2 font-medium">
            {q.question}
          </div>

          {/* Context */}
          {q.context && (
            <div className="text-xs text-surface-500 mb-3 bg-surface-600/20 rounded px-2 py-1">
              {q.context}
            </div>
          )}

          {/* Options */}
          {q.options && (
            <div className="flex flex-wrap gap-1.5 mb-3">
              {q.options.split('\n').filter(Boolean).map((opt, oi) => (
                <button
                  key={oi}
                  onClick={() =>
                    setAnswers(a => ({
                      ...a,
                      [i]: opt.replace(/^[-*]\s*/, ''),
                    }))
                  }
                  disabled={answered[i]}
                  className={`text-xs px-2 py-1 rounded border transition-colors ${
                    answers[i] === opt.replace(/^[-*]\s*/, '')
                      ? 'border-accent-cyan/50 bg-accent-cyan/10 text-accent-cyan'
                      : 'border-white/10 text-surface-400 hover:border-white/20 hover:text-surface-200'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {opt.replace(/^[-*]\s*/, '')}
                </button>
              ))}
            </div>
          )}

          {/* Answer input */}
          {answered[i] ? (
            <div className="text-xs text-accent-green flex items-center gap-1">
              <span>✓</span> 已答复: {answers[i]}
            </div>
          ) : (
            <div className="flex gap-2">
              <input
                type="text"
                value={answers[i] || ''}
                onChange={(e) =>
                  setAnswers(a => ({ ...a, [i]: e.target.value }))
                }
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSubmit(i)
                  }
                }}
                placeholder="输入你的答复..."
                className="flex-1 bg-background-input border border-white/10 rounded-lg px-3 py-1.5 text-sm text-surface-100 placeholder:text-surface-600 focus:outline-none focus:border-accent-cyan transition-colors"
              />
              <button
                onClick={() => handleSubmit(i)}
                disabled={submitting[i] || !answers[i]?.trim()}
                className="px-3 py-1.5 text-sm rounded-lg bg-accent-cyan/20 text-accent-cyan hover:bg-accent-cyan/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
              >
                {submitting[i] ? '发送中...' : '回复'}
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
