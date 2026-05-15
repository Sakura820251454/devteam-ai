import { useState } from 'react'

interface CreateProjectModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (name: string, description: string) => void
}

const EXAMPLE_PROJECTS = [
  {
    name: '用户管理系统',
    desc: '构建一个企业级用户管理系统，支持用户注册、登录、角色权限管理、操作审计日志。前端用 React + Tailwind，后端用 FastAPI，数据库用 PostgreSQL。',
  },
  {
    name: '博客平台',
    desc: '开发一个支持 Markdown 的技术博客平台，包含文章发布、标签分类、评论系统、RSS 订阅、全文搜索。前后端分离架构。',
  },
  {
    name: '电商后台',
    desc: '搭建一个电商管理后台，包含商品管理、订单处理、库存跟踪、数据看板。需要角色权限控制和操作日志。',
  },
]

export default function CreateProjectModal({ isOpen, onClose, onSubmit }: CreateProjectModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  if (!isOpen) return null

  const handleSubmit = () => {
    if (!name.trim()) return
    onSubmit(name.trim(), description.trim())
    setName('')
    setDescription('')
    onClose()
  }

  const handleFillExample = (example: typeof EXAMPLE_PROJECTS[0]) => {
    setName(example.name)
    setDescription(example.desc)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm animate-fade-in">
      <div className="w-[520px] bg-background-panel border border-white/10 rounded-xl shadow-panel animate-slide-up">
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-white/5 flex items-center gap-3">
          <span className="text-xl">🚀</span>
          <div>
            <h3 className="text-sm font-medium text-surface-100">启动新项目</h3>
            <p className="text-xs text-surface-400">描述你的需求，Agent 团队将接管后续开发</p>
          </div>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4">
          {/* Project name */}
          <div>
            <label className="block text-xs text-surface-400 mb-1.5">项目名称</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSubmit()
              }}
              placeholder="例如：用户管理系统"
              autoFocus
              className="w-full bg-background-input border border-white/10 rounded-lg px-3 py-2 text-sm text-surface-100 placeholder:text-surface-600 focus:outline-none focus:border-accent-cyan transition-colors"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs text-surface-400 mb-1.5">
              项目描述
              <span className="text-surface-600 ml-1">（可选，越详细 Agent 理解越准确）</span>
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit()
              }}
              placeholder="描述你想要构建什么..."
              rows={4}
              className="w-full bg-background-input border border-white/10 rounded-lg px-3 py-2 text-sm text-surface-100 placeholder:text-surface-600 focus:outline-none focus:border-accent-cyan transition-colors resize-none"
            />
            <div className="text-xs text-surface-600 mt-1">Enter 提交 · ⌘+Enter 换行发送</div>
          </div>

          {/* Example projects */}
          <div>
            <label className="block text-xs text-surface-400 mb-2">快速填充示例</label>
            <div className="space-y-1.5">
              {EXAMPLE_PROJECTS.map((ex) => (
                <button
                  key={ex.name}
                  onClick={() => handleFillExample(ex)}
                  className={`w-full text-left px-3 py-2 rounded-lg border border-white/5 hover:border-accent-cyan/30 hover:bg-accent-cyan/5 transition-all text-sm ${
                    name === ex.name ? 'border-accent-cyan/50 bg-accent-cyan/10' : 'bg-background-card'
                  }`}
                >
                  <span className="text-surface-200 font-medium">{ex.name}</span>
                  <span className="text-surface-500 ml-2 text-xs">— {ex.desc.slice(0, 50)}...</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="px-5 py-3 border-t border-white/5 flex justify-between items-center">
          <span className="text-xs text-surface-500">
            Agent 团队将自动分析需求并推进 Pipeline
          </span>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-surface-400 hover:text-surface-200 transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleSubmit}
              disabled={!name.trim()}
              className={`px-5 py-2 text-sm rounded-lg font-medium transition-all ${
                name.trim()
                  ? 'bg-accent-cyan text-white hover:bg-accent-cyan/90 shadow-glow-cyan'
                  : 'bg-surface-600 text-surface-400 cursor-not-allowed'
              }`}
            >
              启动项目
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
