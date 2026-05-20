import { useStore } from '../lib/store'

function formatCost(cost: number): string {
  if (cost < 0.01) return '< $0.01'
  return `$${cost.toFixed(2)}`
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

interface Props { projectId?: string | null }

export default function CostPanel({ projectId }: Props) {
  const costData = useStore((s) => projectId ? s.costDataByProject[projectId] ?? null : null)

  if (!costData) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-surface-500">
        <div className="text-3xl mb-3">💰</div>
        <p className="text-sm">暂无成本数据</p>
        <p className="text-xs mt-1">项目启动后将追踪 Token 消耗</p>
      </div>
    )
  }

  const byAgent = Object.entries(costData.byAgent).sort(([, a], [, b]) => b.cost - a.cost)
  const byModel = Object.entries(costData.byModel).sort(([, a], [, b]) => b.cost - a.cost)

  return (
    <div className="h-full overflow-y-auto p-3 space-y-4">
      {/* Total */}
      <div className="bg-background-card rounded-lg border border-white/5 p-3">
        <div className="text-xs text-surface-400 uppercase tracking-wider mb-2">总消耗</div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold text-surface-50 font-mono">
            {formatCost(costData.totalCost)}
          </span>
          <span className="text-xs text-surface-400">
            {formatTokens(costData.totalTokens)} tokens
          </span>
        </div>
        <div className="flex gap-4 mt-2 text-xs text-surface-500">
          <span>调用 {costData.callCount} 次</span>
          <span>输入 {formatTokens(costData.promptTokens)}</span>
          <span>输出 {formatTokens(costData.completionTokens)}</span>
        </div>
      </div>

      {/* By Agent */}
      {byAgent.length > 0 && (
        <div>
          <div className="text-xs text-surface-400 uppercase tracking-wider mb-2">按 Agent</div>
          <div className="space-y-1.5">
            {byAgent.map(([agentId, data]) => {
              const pct = (data.cost / costData.totalCost) * 100
              return (
                <div key={agentId} className="bg-background-card rounded-lg border border-white/5 p-2.5">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-surface-200 font-medium">{agentId}</span>
                    <span className="text-xs font-mono text-surface-200">{formatCost(data.cost)}</span>
                  </div>
                  <div className="h-1 bg-surface-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent-green rounded-full transition-all duration-500"
                      style={{ width: `${Math.max(pct, 2)}%` }}
                    />
                  </div>
                  <div className="text-xs text-surface-500 mt-1">
                    {formatTokens(data.tokens)} tokens · {data.calls} 次调用
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* By Model */}
      {byModel.length > 0 && (
        <div>
          <div className="text-xs text-surface-400 uppercase tracking-wider mb-2">按模型</div>
          <div className="space-y-1.5">
            {byModel.map(([model, data]) => {
              const pct = (data.cost / costData.totalCost) * 100
              return (
                <div key={model} className="flex items-center justify-between py-1">
                  <span className="text-xs text-surface-300">{model}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1 bg-surface-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-accent-purple rounded-full transition-all duration-500"
                        style={{ width: `${Math.max(pct, 2)}%` }}
                      />
                    </div>
                    <span className="text-xs font-mono text-surface-400">{formatCost(data.cost)}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
