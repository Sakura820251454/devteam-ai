import { useState, useEffect, useRef } from 'react'
import AgentPoolModal from './AgentPoolModal'

interface Message {
  id: string
  sender: string
  senderName: string
  content: string
  timestamp: string
  type: 'text' | 'action' | 'system'
  isPrivate?: boolean
  targetAgent?: string
}

interface Agent {
  id: string
  name: string
  role: string
  status: 'idle' | 'thinking' | 'speaking' | 'waiting'
  avatar_color?: string
  description?: string
  system_prompt?: string
}

interface AgentAssignment {
  agentId: string
  tempRole: string
  tempDescription: string
}

const getAvatarColor = (color?: string) => color || 'bg-blue-500'

const AVATAR_INITIALS: Record<string, string> = {
  '产品经理': 'PM', '架构师': 'AR', '后端开发': 'BE', '前端开发': 'FE',
  '测试工程师': 'QA', '运维工程师': 'OP', '项目经理': 'PM'
}

const DEFAULT_AGENTS: Agent[] = [
  { id: 'pm', name: '产品经理', role: '产品经理', status: 'idle', avatar_color: '#3B82F6' },
  { id: 'architect', name: '架构师', role: '架构师', status: 'idle', avatar_color: '#8B5CF6' },
  { id: 'backend', name: '后端开发', role: '后端开发', status: 'idle', avatar_color: '#10B981' },
  { id: 'frontend', name: '前端开发', role: '前端开发', status: 'idle', avatar_color: '#F59E0B' },
  { id: 'tester', name: '测试工程师', role: '测试工程师', status: 'idle', avatar_color: '#EF4444' }
]

export default function CollaborationView() {
  const [agents, setAgents] = useState<Agent[]>(DEFAULT_AGENTS)
  const [publicMessages, setPublicMessages] = useState<Message[]>([])
  const [privateMessages, setPrivateMessages] = useState<Record<string, Message[]>>({})
  const [selectedPrivateAgent, setSelectedPrivateAgent] = useState<string | null>(null)
  const [publicInput, setPublicInput] = useState('')
  const [privateInput, setPrivateInput] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const isRunningRef = useRef(false)
  const [showInterventionPanel, setShowInterventionPanel] = useState(false)
  const [interventionType, setInterventionType] = useState<string>('broadcast')
  const [interventionContent, setInterventionContent] = useState('')
  const [interventionTarget, setInterventionTarget] = useState<string>('')
  const [showAgentPoolModal, setShowAgentPoolModal] = useState(false)

  const publicEndRef = useRef<HTMLDivElement>(null)
  const privateEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = (ref: React.RefObject<HTMLDivElement>) => {
    ref.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    if (publicMessages.length > 0) scrollToBottom(publicEndRef)
  }, [publicMessages])

  useEffect(() => {
    if (Object.keys(privateMessages).length > 0) scrollToBottom(privateEndRef)
  }, [privateMessages])

  const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

  const addPublicMessage = (msg: Omit<Message, 'id' | 'timestamp'>) => {
    setPublicMessages(prev => [...prev, {
      ...msg,
      id: `pub-${Date.now()}-${Math.random()}`,
      timestamp: new Date().toLocaleTimeString()
    }])
  }

  const addPrivateMessage = (agentId: string, msg: Omit<Message, 'id' | 'timestamp'>) => {
    setPrivateMessages(prev => ({
      ...prev,
      [agentId]: [...(prev[agentId] || []), {
        ...msg,
        id: `priv-${Date.now()}-${Math.random()}`,
        timestamp: new Date().toLocaleTimeString()
      }]
    }))
  }

  const updateAgentStatus = (agentId: string, status: Agent['status']) => {
    setAgents(prev => prev.map(a => a.id === agentId ? { ...a, status } : a))
  }

  const handlePublicSend = () => {
    if (!publicInput.trim()) return
    addPublicMessage({
      sender: 'human',
      senderName: '👤 你',
      content: publicInput,
      type: 'text'
    })
    setPublicInput('')
  }

  const handlePrivateSend = () => {
    if (!privateInput.trim() || !selectedPrivateAgent) return
    const agent = agents.find(a => a.id === selectedPrivateAgent)
    addPrivateMessage(selectedPrivateAgent, {
      sender: 'human',
      senderName: '👤 你',
      content: privateInput,
      type: 'text',
      isPrivate: true,
      targetAgent: selectedPrivateAgent
    })
    addPrivateMessage(selectedPrivateAgent, {
      sender: selectedPrivateAgent,
      senderName: agent?.name || selectedPrivateAgent,
      content: `[私聊回复] 收到消息: ${privateInput}`,
      type: 'text',
      isPrivate: true,
      targetAgent: 'human'
    })
    setPrivateInput('')
  }

  const handleIntervention = (type: string) => {
    let content = ''
    switch (type) {
      case 'pause':
        content = '[强制暂停] 用户要求暂停所有讨论'
        addPublicMessage({ sender: 'system', senderName: '系统', content, type: 'action' })
        setAgents(prev => prev.map(a => ({ ...a, status: 'waiting' })))
        break
      case 'resume':
        content = '[恢复讨论] 讨论已恢复'
        addPublicMessage({ sender: 'system', senderName: '系统', content, type: 'action' })
        setAgents(prev => prev.map(a => a.status === 'waiting' ? { ...a, status: 'idle' } : a))
        break
      case 'stop':
        content = '[强制终止] 用户终止了讨论'
        addPublicMessage({ sender: 'system', senderName: '系统', content, type: 'action' })
        setAgents(prev => prev.map(a => ({ ...a, status: 'idle' })))
        isRunningRef.current = false
        setIsRunning(false)
        break
      case 'broadcast':
        if (interventionContent.trim()) {
          addPublicMessage({
            sender: 'human',
            senderName: '👤 你（全局广播）',
            content: interventionContent,
            type: 'text'
          })
          setInterventionContent('')
        }
        break
      case 'private':
        if (interventionContent.trim() && interventionTarget) {
          const agent = agents.find(a => a.id === interventionTarget)
          addPrivateMessage(interventionTarget, {
            sender: 'human',
            senderName: '👤 你（私信）',
            content: interventionContent,
            type: 'text',
            isPrivate: true,
            targetAgent: interventionTarget
          })
          addPrivateMessage(interventionTarget, {
            sender: interventionTarget,
            senderName: agent?.name || interventionTarget,
            content: `[收到指令] ${interventionContent}`,
            type: 'action',
            isPrivate: true,
            targetAgent: 'human'
          })
          setInterventionContent('')
          setInterventionTarget('')
        }
        break
      case 'priority':
        if (interventionContent.trim()) {
          addPublicMessage({
            sender: 'human',
            senderName: '👤 你（优先级指示）',
            content: `[🔴 优先] ${interventionContent}`,
            type: 'action'
          })
          setInterventionContent('')
        }
        break
    }
    setShowInterventionPanel(false)
  }

  const handleAgentsSelected = async (assignments: AgentAssignment[], taskId: string) => {
    // 从后端获取选中的 Agent 详细信息
    try {
      const response = await fetch('/api/agents/')
      if (response.ok) {
        const data = await response.json()
        const allAgents = data.agents || []
        
        // 根据选中的 assignments 构建 Agent 列表
        const selectedAgents: Agent[] = assignments.map((assignment, index) => {
          const agentData = allAgents.find((a: any) => a.id === assignment.agentId)
          if (agentData) {
            return {
              id: agentData.id,
              name: agentData.name,
              role: assignment.tempRole,
              status: 'idle' as const,
              avatar_color: agentData.avatar_color,
              description: assignment.tempDescription || agentData.description,
              system_prompt: agentData.system_prompt
            }
          }
          return null
        }).filter(Boolean) as Agent[]
        
        setAgents(selectedAgents)
        
        addPublicMessage({
          sender: 'system',
          senderName: '系统',
          content: `团队配置已更新，当前团队包含 ${selectedAgents.length} 位成员（人才库模式）`,
          type: 'system'
        })
        
        // 记录任务分配
        assignments.forEach(assignment => {
          const agent = selectedAgents.find(a => a.id === assignment.agentId)
          if (agent) {
            addPublicMessage({
              sender: 'system',
              senderName: '系统',
              content: `📋 ${agent.name} 被分配职责: ${assignment.tempRole}${assignment.tempDescription ? ` - ${assignment.tempDescription}` : ''}`,
              type: 'system'
            })
          }
        })
      }
    } catch (error) {
      console.error('Error fetching agents:', error)
      addPublicMessage({
        sender: 'system',
        senderName: '系统',
        content: '❌ 获取 Agent 信息失败，请检查后端服务',
        type: 'system'
      })
    }
  }

  const startSimulation = async () => {
    if (isRunningRef.current) return
    isRunningRef.current = true
    setIsRunning(true)
    setPublicMessages([])

    addPublicMessage({ sender: 'system', senderName: '系统', content: `🚀 项目开发启动，${agents.length} 位成员开始协作讨论...`, type: 'system' })
    await sleep(2000)

    const activeAgents = agents.slice(0, 3)
    const discussionTopics = [
      { agent: activeAgents[0]?.id, name: activeAgents[0]?.name, msg: '大家好，我们来讨论一下这个项目的需求。' },
      { agent: activeAgents[1]?.id, name: activeAgents[1]?.name, msg: '同意。从架构角度，我建议使用前后端分离架构。' },
      { agent: activeAgents[0]?.id, name: activeAgents[0]?.name, msg: '好的，那我来拆解一下任务。' },
      { agent: activeAgents[2]?.id, name: activeAgents[2]?.name, msg: '我来负责实现，有问题随时讨论。' },
      { agent: activeAgents[1]?.id, name: activeAgents[1]?.name, msg: '很好！那我们开始执行吧。' }
    ].filter(d => d.agent && activeAgents.find(a => a.id === d.agent))

    for (const topic of discussionTopics) {
      if (!isRunningRef.current) break
      updateAgentStatus(topic.agent!, 'speaking')
      addPublicMessage({ sender: topic.agent!, senderName: topic.name!, content: topic.msg, type: 'text' })
      await sleep(3000)
      updateAgentStatus(topic.agent!, 'thinking')
      await sleep(1000)
    }

    if (isRunningRef.current) {
      addPublicMessage({ sender: 'system', senderName: '系统', content: '✅ 初始讨论完成，开始执行任务。', type: 'system' })
    }
    isRunningRef.current = false
    setIsRunning(false)
  }

  const AgentAvatar = ({ agent, size = 'md', showStatus = true }: { agent: Agent; size?: 'sm' | 'md' | 'lg'; showStatus?: boolean }) => {
    const sizeClasses = { sm: 'w-8 h-8 text-xs', md: 'w-10 h-10 text-sm', lg: 'w-12 h-12 text-base' }
    const statusColors = {
      idle: 'bg-gray-400',
      thinking: 'bg-yellow-400 animate-pulse',
      speaking: 'bg-green-400 animate-pulse',
      waiting: 'bg-orange-400'
    }
    const initials = AVATAR_INITIALS[agent.name] || agent.name.substring(0, 2)

    return (
      <div className="relative">
        <div className={`${sizeClasses[size]} ${getAvatarColor(agent.avatar_color)} rounded-full flex items-center justify-center text-white font-bold shadow-lg`}>
          {initials}
        </div>
        {showStatus && (
          <div className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 ${statusColors[agent.status]} rounded-full border-2 border-gray-800`} />
        )}
      </div>
    )
  }

  const MessageBubble = ({ msg, isPrivate = false }: { msg: Message; isPrivate?: boolean }) => {
    const isHuman = msg.sender === 'human'
    const isSystem = msg.sender === 'system'
    const agent = agents.find(a => a.id === msg.sender)

    return (
      <div className={`flex ${isHuman ? 'justify-end' : 'justify-start'} mb-3`}>
        {!isHuman && !isSystem && (
          <div className="mr-2">
            <AgentAvatar agent={agent || { id: msg.sender, name: msg.senderName, role: '', status: 'idle' }} size="sm" showStatus={false} />
          </div>
        )}
        <div className={`max-w-[70%] rounded-2xl px-4 py-2.5 ${
          isSystem ? 'bg-gray-700/80 border border-gray-600' :
          isHuman ? 'bg-primary-600 text-white rounded-br-md' :
          isPrivate ? 'bg-purple-600/90 text-white rounded-bl-md' :
          'bg-gray-700 text-gray-100 rounded-bl-md'
        }`}>
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs font-medium ${isHuman || isPrivate ? 'opacity-90' : 'opacity-70'}`}>{msg.senderName}</span>
            {msg.isPrivate && <span className="text-xs bg-purple-500/50 px-1.5 py-0.5 rounded">私</span>}
            <span className={`text-xs ${isHuman || isPrivate ? 'opacity-60' : 'opacity-50'}`}>{msg.timestamp}</span>
          </div>
          <div className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex h-full bg-gray-900 text-gray-100 overflow-hidden">
      {/* Left Sidebar - Agent List */}
      <div className="w-64 bg-gray-800 border-r border-gray-700 flex flex-col">
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-lg font-bold text-primary-400 flex items-center gap-2">
            <span>🤖</span> Agent团队
          </h2>
          <div className="flex items-center justify-between mt-2">
            <p className="text-xs text-gray-500">{agents.length} 位成员</p>
            <button
              onClick={() => setShowAgentPoolModal(true)}
              className="text-xs text-primary-400 hover:text-primary-300"
            >
              从人才库选择
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {agents.map(agent => (
            <div
              key={agent.id}
              className={`bg-gray-700/50 rounded-xl p-3 cursor-pointer transition-all hover:bg-gray-700 ${
                selectedPrivateAgent === agent.id ? 'ring-2 ring-primary-500 bg-gray-700' : ''
              }`}
              onClick={() => setSelectedPrivateAgent(selectedPrivateAgent === agent.id ? null : agent.id)}
            >
              <div className="flex items-center gap-3">
                <AgentAvatar agent={agent} />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-white truncate">{agent.name}</div>
                  <div className="text-xs text-gray-400 truncate">
                    {agent.status === 'speaking' && <span className="text-green-400">发言中...</span>}
                    {agent.status === 'thinking' && <span className="text-yellow-400">思考中...</span>}
                    {agent.status === 'waiting' && <span className="text-orange-400">等待中</span>}
                    {agent.status === 'idle' && <span className="text-gray-500">空闲</span>}
                  </div>
                </div>
                {privateMessages[agent.id]?.length > 0 && (
                  <div className="bg-purple-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                    {privateMessages[agent.id].length}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="p-3 border-t border-gray-700 space-y-2">
          <button
            onClick={startSimulation}
            disabled={isRunning}
            className="w-full py-2.5 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
          >
            {isRunning ? '⏳ 运行中...' : '🚀 启动讨论'}
          </button>
          <button
            onClick={() => { isRunningRef.current = false; setIsRunning(false) }}
            disabled={!isRunning}
            className="w-full py-2 bg-red-600/80 hover:bg-red-700 disabled:bg-gray-600 disabled:opacity-50 rounded-lg font-medium transition-colors"
          >
            ⏹ 停止
          </button>
        </div>
      </div>

      {/* Center - Public Discussion Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse" />
            <h3 className="font-medium text-white">公共讨论区</h3>
            <span className="text-xs text-gray-500">所有 Agent 参与</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowInterventionPanel(!showInterventionPanel)}
              className="px-3 py-1.5 bg-orange-600/80 hover:bg-orange-600 rounded-lg text-sm font-medium transition-colors flex items-center gap-1"
            >
              🔒 强制干预
            </button>
          </div>
        </div>

        {showInterventionPanel && (
          <div className="bg-orange-900/30 border-b border-orange-800/50 p-4">
            <h4 className="text-sm font-medium text-orange-400 mb-3">🔒 强制干预面板</h4>
            <div className="flex gap-2 mb-3">
              {[
                { id: 'broadcast', label: '全局广播' },
                { id: 'private', label: '私信' },
                { id: 'priority', label: '优先指示' },
                { id: 'pause', label: '⏸ 暂停' },
                { id: 'resume', label: '▶ 恢复' },
                { id: 'stop', label: '⏹ 终止' }
              ].map(action => (
                <button
                  key={action.id}
                  onClick={() => {
                    if (['pause', 'resume', 'stop'].includes(action.id)) {
                      handleIntervention(action.id)
                    } else {
                      setInterventionType(action.id)
                    }
                  }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    ['pause', 'resume', 'stop'].includes(action.id)
                      ? 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                      : interventionType === action.id
                        ? 'bg-orange-600 text-white'
                        : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                  }`}
                >
                  {action.label}
                </button>
              ))}
            </div>
            <div className="flex gap-3">
              {interventionType === 'private' && (
                <select
                  value={interventionTarget}
                  onChange={e => setInterventionTarget(e.target.value)}
                  className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:border-orange-500"
                >
                  <option value="">选择 Agent...</option>
                  {agents.map(a => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
              )}
              <input
                type="text"
                value={interventionContent}
                onChange={e => setInterventionContent(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleIntervention(interventionType)}
                placeholder={
                  interventionType === 'broadcast' ? '输入广播内容...' :
                  interventionType === 'private' ? '输入私信内容...' :
                  interventionType === 'priority' ? '输入优先指示...' : ''
                }
                className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:border-orange-500"
              />
              <button
                onClick={() => handleIntervention(interventionType)}
                disabled={interventionType === 'private' && !interventionTarget}
                className="px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:bg-gray-600 rounded font-medium transition-colors"
              >
                发送
              </button>
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-4">
          {publicMessages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-gray-500">
                <div className="text-5xl mb-4">💬</div>
                <p className="text-lg mb-2">公共讨论区</p>
                <p className="text-sm">点击「启动讨论」开始团队协作</p>
                <p className="text-xs mt-4 text-gray-600">或点击「配置团队」自定义 Agent</p>
              </div>
            </div>
          ) : (
            publicMessages.map(msg => <MessageBubble key={msg.id} msg={msg} />)
          )}
          <div ref={publicEndRef} />
        </div>

        <div className="p-3 bg-gray-800 border-t border-gray-700">
          <div className="flex gap-2">
            <input
              type="text"
              value={publicInput}
              onChange={e => setPublicInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handlePublicSend()}
              placeholder="在公共讨论区发言..."
              className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-primary-500"
            />
            <button
              onClick={handlePublicSend}
              className="px-6 py-2.5 bg-primary-600 hover:bg-primary-700 rounded-lg font-medium transition-colors"
            >
              发送
            </button>
          </div>
          <div className="flex gap-4 mt-2 text-xs text-gray-500">
            <span>公开消息所有 Agent 可见</span>
          </div>
        </div>
      </div>

      {/* Right Sidebar - Private Chat */}
      <div className="w-80 bg-gray-800/50 border-l border-gray-700 flex flex-col">
        {selectedPrivateAgent ? (
          <>
            <div className="bg-gray-800 border-b border-gray-700 px-4 py-3">
              <div className="flex items-center gap-3">
                <AgentAvatar agent={agents.find(a => a.id === selectedPrivateAgent) || agents[0]} />
                <div>
                  <h3 className="font-medium text-white">{agents.find(a => a.id === selectedPrivateAgent)?.name}</h3>
                  <p className="text-xs text-purple-400">私聊对话</p>
                </div>
                <button onClick={() => setSelectedPrivateAgent(null)} className="ml-auto text-gray-500 hover:text-white">
                  ✕
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {(privateMessages[selectedPrivateAgent] || []).length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-gray-500">
                  <div className="text-4xl mb-3">🔒</div>
                  <p className="text-sm">私密对话</p>
                  <p className="text-xs mt-1">仅你和 {agents.find(a => a.id === selectedPrivateAgent)?.name} 可见</p>
                </div>
              ) : (
                (privateMessages[selectedPrivateAgent] || []).map(msg => (
                  <MessageBubble key={msg.id} msg={msg} isPrivate />
                ))
              )}
              <div ref={privateEndRef} />
            </div>

            <div className="p-3 bg-gray-800 border-t border-gray-700">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={privateInput}
                  onChange={e => setPrivateInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handlePrivateSend()}
                  placeholder={`私信 ${agents.find(a => a.id === selectedPrivateAgent)?.name}...`}
                  className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-purple-500"
                />
                <button
                  onClick={handlePrivateSend}
                  className="px-4 py-2.5 bg-purple-600 hover:bg-purple-700 rounded-lg font-medium transition-colors"
                >
                  发送
                </button>
              </div>
              <div className="flex items-center gap-2 mt-2 text-xs text-purple-400">
                <span className="w-2 h-2 bg-purple-500 rounded-full" />
                <span>私密消息，其他 Agent 不可见</span>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-500">
            <div className="text-5xl mb-4">🔐</div>
            <p className="text-lg mb-2">私聊区</p>
            <p className="text-sm text-center px-4">点击左侧 Agent 头像<br />开始一对一私密对话</p>
            <div className="mt-6 text-xs text-gray-600">
              <p>• 布置单独任务</p>
              <p>• 深入技术讨论</p>
              <p>• 获取专属反馈</p>
            </div>
          </div>
        )}
      </div>

      {/* Agent Pool Modal */}
      <AgentPoolModal
        isOpen={showAgentPoolModal}
        onClose={() => setShowAgentPoolModal(false)}
        onAgentsSelected={handleAgentsSelected}
      />
    </div>
  )
}
