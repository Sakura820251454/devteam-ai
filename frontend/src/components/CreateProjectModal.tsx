import { useState, useEffect } from 'react'

interface StageDef {
  key: string
  label: string
  description: string
  expected_artifact: string
  parallel_group: string | null
}

interface Template {
  id: string
  name: string
  description: string
  category: string
  suggested_strategy: string
  stages: StageDef[]
}

interface CreateProjectModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (name: string, description: string, template: Template | null) => void
}

const EXAMPLE_PROJECTS = [
  {
    name: '用户管理系统',
    desc: '构建一个企业级用户管理系统，支持用户注册、登录、角色权限管理、操作审计日志。前端用 React + Tailwind，后端用 FastAPI，数据库用 PostgreSQL。',
    templateId: 'web_application',
  },
  {
    name: '博客平台',
    desc: '开发一个支持 Markdown 的技术博客平台，包含文章发布、标签分类、评论系统、RSS 订阅、全文搜索。前后端分离架构。',
    templateId: 'web_application',
  },
  {
    name: '电商后台',
    desc: '搭建一个电商管理后台，包含商品管理、订单处理、库存跟踪、数据看板。需要角色权限控制和操作日志。',
    templateId: 'web_application',
  },
]

const CATEGORY_LABELS: Record<string, string> = {
  simple: '📝 简单任务',
  development: '🏗️ 开发项目',
  design: '🧭 方案设计',
  complex: '🏢 复杂系统',
}

const CATEGORY_ORDER = ['simple', 'development', 'design', 'complex']

const STRATEGY_LABELS: Record<string, string> = {
  sequential: '顺序执行',
  hierarchical: '层级委派',
  discussion: '圆桌讨论',
  pipeline: '流水线',
  auto: '智能推荐',
}

const MOCK_TEMPLATES: Template[] = [
  { id: 'script_automation', name: '脚本自动化', description: '编写自动化脚本，如数据导出、文件处理', category: 'simple', suggested_strategy: 'sequential', stages: [{ key: 'requirement', label: '需求理解', description: '理解脚本需求和输入输出', expected_artifact: '需求摘要.md', parallel_group: null }, { key: 'coding', label: '脚本编写', description: '编写脚本代码', expected_artifact: '脚本代码/', parallel_group: null }, { key: 'verify', label: '运行验证', description: '运行脚本验证输出正确性', expected_artifact: '验证结果.md', parallel_group: null }] },
  { id: 'knowledge_research', name: '知识查询与研究', description: '查询技术知识、分析概念、调研方案', category: 'simple', suggested_strategy: 'sequential', stages: [{ key: 'analyze', label: '问题拆解', description: '拆解问题，确定研究方向', expected_artifact: '问题分析.md', parallel_group: null }, { key: 'research', label: '信息检索', description: '搜索和分析相关资料', expected_artifact: '调研笔记.md', parallel_group: null }, { key: 'summary', label: '总结输出', description: '整理研究结果，输出报告', expected_artifact: '研究报告.md', parallel_group: null }] },
  { id: 'bug_fix', name: 'Bug 修复', description: '排查和修复代码缺陷', category: 'simple', suggested_strategy: 'sequential', stages: [{ key: 'reproduce', label: '问题复现', description: '复现 Bug，确认问题', expected_artifact: '复现步骤.md', parallel_group: null }, { key: 'analysis', label: '根因分析', description: '分析代码找出根因', expected_artifact: '根因分析.md', parallel_group: null }, { key: 'fix', label: '代码修复', description: '修复代码并自测', expected_artifact: '修复代码/', parallel_group: null }, { key: 'regression', label: '回归验证', description: '验证修复不影响其他功能', expected_artifact: '验证结果.md', parallel_group: null }] },
  { id: 'web_application', name: 'Web 应用', description: '全栈 Web 应用，前后端分离架构', category: 'development', suggested_strategy: 'pipeline', stages: [{ key: 'requirement', label: '需求分析', description: '分析用户需求', expected_artifact: '需求文档.md', parallel_group: null }, { key: 'design', label: '架构设计', description: '设计系统架构', expected_artifact: '技术方案.md', parallel_group: null }, { key: 'backend', label: '后端开发', description: '实现后端 API', expected_artifact: '后端代码/', parallel_group: 'dev' }, { key: 'frontend', label: '前端开发', description: '实现前端页面', expected_artifact: '前端代码/', parallel_group: 'dev' }, { key: 'integration', label: '集成测试', description: '前后端联调', expected_artifact: '测试报告.md', parallel_group: null }, { key: 'deployment', label: '部署上线', description: '部署到生产环境', expected_artifact: '部署配置/', parallel_group: null }] },
  { id: 'api_service', name: 'API 服务', description: '纯后端 API 服务开发', category: 'development', suggested_strategy: 'pipeline', stages: [{ key: 'requirement', label: '需求分析', description: '分析 API 需求', expected_artifact: '需求文档.md', parallel_group: null }, { key: 'design', label: '接口设计', description: '设计 API 接口和数据结构', expected_artifact: 'API设计.md', parallel_group: null }, { key: 'implement', label: '开发实现', description: '实现 API 逻辑', expected_artifact: '代码/', parallel_group: null }, { key: 'test', label: '测试', description: '接口测试和性能测试', expected_artifact: '测试报告.md', parallel_group: null }, { key: 'deploy', label: '部署', description: '部署 API 服务', expected_artifact: '部署配置/', parallel_group: null }] },
  { id: 'cli_tool', name: 'CLI 工具', description: '命令行工具开发', category: 'development', suggested_strategy: 'pipeline', stages: [{ key: 'requirement', label: '需求分析', description: '分析CLI工具用法', expected_artifact: '需求文档.md', parallel_group: null }, { key: 'develop', label: '核心开发', description: '实现核心功能', expected_artifact: '代码/', parallel_group: null }, { key: 'test', label: '测试', description: '功能测试', expected_artifact: '测试报告.md', parallel_group: null }, { key: 'release', label: '文档+发布', description: '编写README', expected_artifact: 'README.md', parallel_group: null }] },
  { id: 'custom', name: '自定义', description: 'LLM 根据需求描述动态生成阶段', category: 'development', suggested_strategy: 'auto', stages: [] },
]

export default function CreateProjectModal({ isOpen, onClose, onSubmit }: CreateProjectModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [templates, setTemplates] = useState<Template[]>([])
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('web_application')
  const [showStagePreview, setShowStagePreview] = useState(false)

  useEffect(() => {
    if (isOpen) {
      fetchTemplates()
    }
  }, [isOpen])

  const fetchTemplates = async () => {
    try {
      const response = await fetch('/api/pipelines/templates')
      if (response.ok) {
        const data = await response.json()
        if (data.templates && data.templates.length > 0) {
          setTemplates(data.templates)
          return
        }
      }
      setTemplates(MOCK_TEMPLATES)
    } catch {
      setTemplates(MOCK_TEMPLATES)
    }
  }

  const selectedTemplate = templates.find(t => t.id === selectedTemplateId) || templates[0]

  if (!isOpen) return null

  const handleSubmit = () => {
    if (!name.trim()) return
    onSubmit(name.trim(), description.trim(), selectedTemplate || null)
    setName('')
    setDescription('')
    onClose()
  }

  const handleFillExample = (example: typeof EXAMPLE_PROJECTS[0]) => {
    setName(example.name)
    setDescription(example.desc)
    setSelectedTemplateId(example.templateId)
  }

  // Group templates by category
  const groupedTemplates: Record<string, Template[]> = {}
  for (const t of templates) {
    if (!groupedTemplates[t.category]) groupedTemplates[t.category] = []
    groupedTemplates[t.category].push(t)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm animate-fade-in">
      <div className="w-[680px] bg-background-panel border border-white/10 rounded-xl shadow-panel animate-slide-up max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-white/5 flex items-center gap-3 shrink-0">
          <span className="text-xl">🚀</span>
          <div>
            <h3 className="text-sm font-medium text-surface-100">启动新项目</h3>
            <p className="text-xs text-surface-400">描述需求，选择 Pipeline 模板，Agent 团队将接管后续开发</p>
          </div>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4 overflow-y-auto flex-1">
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
              <span className="text-surface-600 ml-1">（越详细 Agent 理解越准确）</span>
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="描述你想要构建什么..."
              rows={3}
              className="w-full bg-background-input border border-white/10 rounded-lg px-3 py-2 text-sm text-surface-100 placeholder:text-surface-600 focus:outline-none focus:border-accent-cyan transition-colors resize-none"
            />
          </div>

          {/* Pipeline Template Selection */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs text-surface-400">
                Pipeline 阶段模板
                <span className="text-surface-600 ml-1">（选择后 LLM 可在需求分析时调整）</span>
              </label>
              {selectedTemplate && selectedTemplate.stages.length > 0 && (
                <button
                  onClick={() => setShowStagePreview(!showStagePreview)}
                  className="text-xs text-accent-cyan hover:text-accent-cyan/80"
                >
                  {showStagePreview ? '收起阶段' : '预览阶段'}
                </button>
              )}
            </div>

            <div className="space-y-2">
              {CATEGORY_ORDER.map(cat => {
                const catTemplates = groupedTemplates[cat]
                if (!catTemplates || catTemplates.length === 0) return null
                return (
                  <div key={cat}>
                    <span className="text-xs text-surface-500 mb-1 block">{CATEGORY_LABELS[cat]}</span>
                    <div className="grid grid-cols-3 gap-1.5">
                      {catTemplates.map(t => {
                        const isSelected = t.id === selectedTemplateId
                        return (
                          <button
                            key={t.id}
                            onClick={() => { setSelectedTemplateId(t.id); setShowStagePreview(false) }}
                            className={`text-left px-3 py-2 rounded-lg border text-xs transition-all ${
                              isSelected
                                ? 'border-accent-cyan/50 bg-accent-cyan/10'
                                : 'border-white/5 bg-background-card hover:border-white/10'
                            }`}
                          >
                            <div className="font-medium text-surface-200">{t.name}</div>
                            <div className="text-surface-500 mt-0.5 leading-relaxed line-clamp-2">{t.description}</div>
                            <div className="text-surface-600 mt-1">{STRATEGY_LABELS[t.suggested_strategy] || t.suggested_strategy}</div>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Stage Preview */}
            {showStagePreview && selectedTemplate && selectedTemplate.stages.length > 0 && (
              <div className="mt-2 p-3 bg-surface-600/20 rounded-lg border border-white/5">
                <div className="text-xs text-surface-400 mb-2">
                  {selectedTemplate.name} — {selectedTemplate.stages.length} 个阶段
                </div>
                <div className="flex items-center gap-1.5 flex-wrap">
                  {selectedTemplate.stages.map((stage, i) => (
                    <span key={stage.key} className="inline-flex items-center gap-1">
                      {i > 0 && <span className="text-surface-600">→</span>}
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        stage.parallel_group
                          ? 'bg-accent-purple/20 text-accent-purple'
                          : 'bg-surface-600/50 text-surface-300'
                      }`} title={stage.expected_artifact}>
                        {stage.label}
                        {stage.parallel_group && <span className="ml-1 text-accent-purple/60">‖</span>}
                      </span>
                    </span>
                  ))}
                </div>
                <div className="text-xs text-surface-500 mt-1.5">
                  产出物：{selectedTemplate.stages.map(s => s.expected_artifact).filter(Boolean).join(' · ')}
                </div>
              </div>
            )}
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
                  <span className="text-surface-500 ml-2 text-xs">— {ex.desc.slice(0, 60)}...</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="px-5 py-3 border-t border-white/5 flex justify-between items-center shrink-0">
          <span className="text-xs text-surface-500">
            {selectedTemplate ? `模板：${selectedTemplate.name}（${selectedTemplate.stages.length} 阶段）` : 'Agent 团队将自动分析需求'}
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
