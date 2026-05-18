import { useState, useEffect } from 'react'

interface Agent {
  id: string
  name: string
  type: string
  description: string
  avatar_color: string
  capabilities: string[]
  source: string
  soul_data?: {
    core_principles: string[]
    execution_rules: string[]
    role_definitions?: Record<string, unknown>
  }
  status: string
  is_active: boolean
}

interface Task {
  id: string
  name: string
  description: string
  status: 'planning' | 'executing' | 'completed'
}

interface AgentAssignment {
  agentId: string
  tempRole: string
  tempDescription: string
}

interface AgentPoolModalProps {
  isOpen: boolean
  onClose: () => void
  onAgentsSelected: (agents: AgentAssignment[], taskName: string, taskDesc: string, taskId: string) => void
  currentTask?: Task
}

const PREDEFINED_TEMP_ROLES = [
  { id: 'requirement', label: '需求分析', desc: '负责需求调研和功能规划' },
  { id: 'design', label: '架构设计', desc: '负责系统架构和技术选型' },
  { id: 'backend', label: '后端开发', desc: '负责后端服务实现' },
  { id: 'frontend', label: '前端开发', desc: '负责用户界面实现' },
  { id: 'testing', label: '测试验证', desc: '负责功能测试和质量保障' },
  { id: 'review', label: '代码评审', desc: '负责代码审查和问题发现' },
  { id: 'deploy', label: '部署运维', desc: '负责部署和运维监控' },
  { id: 'document', label: '文档编写', desc: '负责技术文档编写' }
]

const getAvatarEmoji = (type: string): string => {
  const emojiMap: Record<string, string> = {
    product_manager: '👔',
    architect: '🧙',
    backend_developer: '👨‍💻',
    frontend_developer: '👩‍🎨',
    tester: '🧪',
    devops: '🚀',
    custom: '👤'
  }
  return emojiMap[type] || '👤'
}

const getRoleLabel = (type: string): string => {
  const roleMap: Record<string, string> = {
    product_manager: '产品经理',
    architect: '架构师',
    backend_developer: '后端开发',
    frontend_developer: '前端开发',
    tester: '测试工程师',
    devops: '运维工程师',
    custom: '自定义'
  }
  return roleMap[type] || type
}

export default function AgentPoolModal({ isOpen, onClose, onAgentsSelected, currentTask }: AgentPoolModalProps) {
  const [agents, setAgents] = useState<Agent[]>([])
  const [selectedAgents, setSelectedAgents] = useState<Map<string, AgentAssignment>>(new Map())
  const [taskName, setTaskName] = useState(currentTask?.name || '')
  const [taskDesc, setTaskDesc] = useState(currentTask?.description || '')
  const [loading, setLoading] = useState(false)
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      fetchAgents()
      setSelectedAgents(new Map())
      setTaskName(currentTask?.name || '')
      setTaskDesc(currentTask?.description || '')
      setExpandedAgent(null)
    }
  }, [isOpen, currentTask])

  const MOCK_AGENTS: Agent[] = [
    { id: 'data_engineer', name: '数据工程师', type: 'backend_developer', description: '负责数据管道和 ETL 流程设计', avatar_color: '#3fb950', capabilities: ['数据建模', 'ETL', 'SQL优化'], source: 'mock', status: 'idle', is_active: true, soul_data: { core_principles: ['数据准确性优先', '管道可观测性'], execution_rules: ['所有ETL必须有重试机制', '敏感数据必须脱敏'] } },
    { id: 'security_expert', name: '安全专家', type: 'architect', description: '负责安全审计和漏洞扫描', avatar_color: '#f85149', capabilities: ['渗透测试', '安全审计', 'OWASP'], source: 'mock', status: 'idle', is_active: true, soul_data: { core_principles: ['安全左移', '纵深防御'], execution_rules: ['PR合并前必须通过安全扫描', '敏感信息不得硬编码'] } },
    { id: 'ux_designer', name: 'UX设计师', type: 'frontend_developer', description: '负责用户体验设计和交互原型', avatar_color: '#f0883e', capabilities: ['用户研究', '原型设计', '可用性测试'], source: 'mock', status: 'idle', is_active: true, soul_data: { core_principles: ['以用户为中心', '渐进式增强'], execution_rules: ['新功能必须有交互原型', '遵循设计系统规范'] } },
    { id: 'tech_writer', name: '技术文档工程师', type: 'custom', description: '负责 API 文档和用户手册编写', avatar_color: '#d29922', capabilities: ['API文档', '用户手册', '教程编写'], source: 'mock', status: 'idle', is_active: true, soul_data: { core_principles: ['文档即代码', '清晰胜于花哨'], execution_rules: ['API变更必须同步更新文档', '所有示例代码必须可运行'] } },
    { id: 'ml_engineer', name: 'ML工程师', type: 'backend_developer', description: '负责机器学习模型训练和部署', avatar_color: '#a371f7', capabilities: ['模型训练', '特征工程', 'MLOps'], source: 'mock', status: 'idle', is_active: true, soul_data: { core_principles: ['模型可解释性', '数据隐私优先'], execution_rules: ['模型上线前必须通过A/B测试', '训练数据版本化管理'] } },
  ]

  const fetchAgents = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/agents/soul-based')
      if (response.ok) {
        const data = await response.json()
        setAgents(data.agents || [])
      } else {
        setAgents(MOCK_AGENTS)
      }
    } catch {
      setAgents(MOCK_AGENTS)
    } finally {
      setLoading(false)
    }
  }

  const toggleAgent = (agent: Agent) => {
    if (agent.status !== 'idle') return
    
    const newSelected = new Map(selectedAgents)
    if (newSelected.has(agent.id)) {
      newSelected.delete(agent.id)
    } else {
      newSelected.set(agent.id, {
        agentId: agent.id,
        tempRole: '',
        tempDescription: ''
      })
    }
    setSelectedAgents(newSelected)
  }

  const updateAssignment = (agentId: string, field: 'tempRole' | 'tempDescription', value: string) => {
    const newSelected = new Map(selectedAgents)
    const assignment = newSelected.get(agentId)
    if (assignment) {
      newSelected.set(agentId, { ...assignment, [field]: value })
      setSelectedAgents(newSelected)
    }
  }

  const getAgentById = (id: string) => agents.find(a => a.id === id)

  const canSubmit = taskName.trim() && 
    Array.from(selectedAgents.values()).every(a => a.tempRole.trim())

  const handleSubmit = () => {
    if (!canSubmit) return
    const taskId = `task_${Date.now()}`
    onAgentsSelected(Array.from(selectedAgents.values()), taskName.trim(), taskDesc.trim(), taskId)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-xl w-[1100px] max-h-[90vh] overflow-hidden flex flex-col">
        <div className="px-6 py-4 border-b border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-white">Agent 人才库 & 任务分配</h2>
              <p className="text-sm text-gray-400 mt-1">
                从人才库选择员工组建项目团队，分配临时职责
                <span className="ml-2 text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded">
                  基于 soul.md 定义
                </span>
              </p>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">&times;</button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="grid grid-cols-2 gap-6">
            <section>
              <h3 className="text-sm font-medium text-gray-400 mb-3">
                👥 人才库
                {loading && <span className="ml-2 text-xs text-gray-500">加载中...</span>}
                {!loading && <span className="ml-2 text-xs text-gray-500">({agents.length} 位员工)</span>}
              </h3>
              
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
                </div>
              ) : agents.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <p>暂无基于 soul.md 的 Agent</p>
                  <p className="text-xs mt-2">请先在后端 agents/ 目录添加 soul.md 文件</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {agents.map(agent => {
                    const isSelected = selectedAgents.has(agent.id)
                    const isExpanded = expandedAgent === agent.id
                    
                    return (
                      <div
                        key={agent.id}
                        className={`rounded-lg border transition-all ${
                          agent.status !== 'idle' 
                            ? 'border-gray-700 bg-gray-700/30 opacity-50'
                            : isSelected 
                              ? 'border-primary-500 bg-primary-500/20' 
                              : 'border-gray-600 bg-gray-700/50 hover:border-gray-500'
                        }`}
                      >
                        <div
                          className="p-4 cursor-pointer"
                          onClick={() => {
                            if (agent.status === 'idle') {
                              toggleAgent(agent)
                            }
                          }}
                        >
                          <div className="flex items-start gap-3">
                            <div
                              className="w-12 h-12 rounded-full flex items-center justify-center text-2xl"
                              style={{ backgroundColor: `${agent.avatar_color || '#6B7280'}30` }}
                            >
                              {getAvatarEmoji(agent.type)}
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center justify-between">
                                <div>
                                  <span className="font-medium text-white">{agent.name}</span>
                                  <span className="text-xs text-gray-400 ml-2">({getRoleLabel(agent.type)})</span>
                                  {agent.source === 'soul' && (
                                    <span className="text-xs bg-purple-500/20 text-purple-400 px-2 py-0.5 rounded ml-1">
                                      soul
                                    </span>
                                  )}
                                </div>
                                {agent.status !== 'idle' && (
                                  <span className="text-xs bg-gray-600 text-gray-300 px-2 py-0.5 rounded">
                                    忙碌中
                                  </span>
                                )}
                                {isSelected && agent.status === 'idle' && (
                                  <span className="text-primary-400">✓</span>
                                )}
                              </div>
                              <p className="text-xs text-gray-400 mt-1">{agent.description}</p>
                              <div className="flex flex-wrap gap-1 mt-2">
                                {agent.capabilities.slice(0, 3).map(c => (
                                  <span key={c} className="text-xs bg-gray-600/50 text-gray-300 px-2 py-0.5 rounded">
                                    {c}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </div>
                        </div>

                        {isExpanded && agent.soul_data && (
                          <div className="px-4 pb-4 border-t border-gray-600 mt-2 pt-4">
                            <div className="grid grid-cols-2 gap-4 text-xs">
                              {agent.soul_data.core_principles && agent.soul_data.core_principles.length > 0 && (
                                <div>
                                  <h4 className="text-gray-400 font-medium mb-2">🎯 核心原则</h4>
                                  <ul className="space-y-1">
                                    {agent.soul_data.core_principles.slice(0, 3).map((principle, idx) => (
                                      <li key={idx} className="text-gray-300">{principle}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              {agent.soul_data.execution_rules && agent.soul_data.execution_rules.length > 0 && (
                                <div>
                                  <h4 className="text-gray-400 font-medium mb-2">📋 执行规则</h4>
                                  <ul className="space-y-1">
                                    {agent.soul_data.execution_rules.slice(0, 3).map((rule, idx) => (
                                      <li key={idx} className="text-gray-300">{rule}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          </div>
                        )}

                        {agent.soul_data && agent.status === 'idle' && (
                          <div className="px-4 pb-2">
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                setExpandedAgent(isExpanded ? null : agent.id)
                              }}
                              className="text-xs text-primary-400 hover:text-primary-300"
                            >
                              {isExpanded ? '收起详情' : '查看行为准则'}
                            </button>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </section>

            <section>
              <h3 className="text-sm font-medium text-gray-400 mb-3">📋 分配职责</h3>
              
              <div className="bg-gray-700/30 rounded-lg p-4 mb-4">
                <div className="mb-3">
                  <label className="block text-xs text-gray-400 mb-1">项目名称</label>
                  <input
                    type="text"
                    value={taskName}
                    onChange={(e) => setTaskName(e.target.value)}
                    placeholder="例如: 用户管理系统开发"
                    className="w-full bg-gray-600 border border-gray-500 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">项目描述</label>
                  <textarea
                    value={taskDesc}
                    onChange={(e) => setTaskDesc(e.target.value)}
                    placeholder="描述项目目标..."
                    rows={2}
                    className="w-full bg-gray-600 border border-gray-500 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-primary-500 resize-none"
                  />
                </div>
              </div>

              {selectedAgents.size === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <p>← 从左侧选择员工</p>
                  <p className="text-xs mt-2">选择后将在这里分配职责</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {Array.from(selectedAgents.entries()).map(([agentId, assignment]) => {
                    const agent = getAgentById(agentId)
                    if (!agent) return null
                    return (
                      <div key={agentId} className="bg-gray-700/50 rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-3">
                          <span className="text-lg">{getAvatarEmoji(agent.type)}</span>
                          <span className="font-medium text-white">{agent.name}</span>
                          <span className="text-xs text-gray-400">({getRoleLabel(agent.type)})</span>
                        </div>
                        
                        <div className="space-y-2">
                          <div>
                            <label className="block text-xs text-gray-400 mb-1">本次任务职责 *</label>
                            <select
                              value={assignment.tempRole}
                              onChange={(e) => updateAssignment(agentId, 'tempRole', e.target.value)}
                              className="w-full bg-gray-600 border border-gray-500 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-primary-500"
                            >
                              <option value="">选择职责...</option>
                              {PREDEFINED_TEMP_ROLES.map(role => (
                                <option key={role.id} value={role.id}>
                                  {role.label} - {role.desc}
                                </option>
                              ))}
                            </select>
                          </div>
                          
                          <div>
                            <label className="block text-xs text-gray-400 mb-1">职责描述</label>
                            <textarea
                              value={assignment.tempDescription}
                              onChange={(e) => updateAssignment(agentId, 'tempDescription', e.target.value)}
                              placeholder="描述该员工在此任务中的具体工作..."
                              rows={2}
                              className="w-full bg-gray-600 border border-gray-500 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-primary-500 resize-none"
                            />
                          </div>
                        </div>

                        <button
                          onClick={() => toggleAgent(agent)}
                          className="mt-2 text-xs text-red-400 hover:text-red-300"
                        >
                          移除此员工
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}
            </section>
          </div>
        </div>

        <div className="px-6 py-4 border-t border-gray-700 flex justify-between items-center">
          <div className="text-sm text-gray-400">
            已选择 <span className="text-white font-medium">{selectedAgents.size}</span> 位员工
            {selectedAgents.size > 0 && (
              <span className="ml-2">
                ({Array.from(selectedAgents.values()).map(a => {
                  const role = PREDEFINED_TEMP_ROLES.find(r => r.id === a.tempRole)
                  return role?.label || '?'
                }).join(', ')})
              </span>
            )}
          </div>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-300 hover:text-white transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleSubmit}
              disabled={!canSubmit}
              className="px-6 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
            >
              启动项目 ({selectedAgents.size})
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}