import { useState, useEffect, useRef } from 'react'

interface Message {
  id: string
  sender: string
  senderName: string
  content: string
  timestamp: string
  type: 'text' | 'action' | 'system'
}

interface Task {
  id: string
  title: string
  status: string
  priority: string
}

interface Pipeline {
  id: string
  name: string
  status: string
  current_stage: string
  progress: number
  logs: Array<{ stage: string; message: string; level: string; timestamp: string }>
}

interface Agent {
  id: string
  name: string
  role: string
  status: string
}

const STAGE_LABELS: Record<string, string> = {
  requirement_analysis: '需求分析',
  task_breakdown: '任务拆解',
  task_execution: '任务执行',
  review: '审核',
  completed: '完成'
}

const STATUS_COLORS: Record<string, string> = {
  idle: 'bg-gray-400',
  running: 'bg-green-500 animate-pulse',
  paused: 'bg-yellow-500',
  completed: 'bg-blue-500',
  failed: 'bg-red-500',
  backlog: 'bg-gray-500',
  todo: 'bg-blue-500',
  in_progress: 'bg-yellow-500',
  review: 'bg-purple-500',
  done: 'bg-green-500'
}

export default function PipelineView() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [pipeline, setPipeline] = useState<Pipeline | null>(null)
  const [interventionInput, setInterventionInput] = useState('')
  const [projectName, setProjectName] = useState('')
  const [projectReq, setProjectReq] = useState('')
  const [isSimulating, setIsSimulating] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const fetchAgents = async () => {
    try {
      const res = await fetch('/api/agents/')
      if (res.ok) {
        const data = await res.json()
        // API returns {agents: [...], total: N}
        const agentList = data.agents || data
        if (agentList.length > 0) {
          setAgents(agentList.map((a: any) => ({
            id: a.id,
            name: a.name,
            role: a.type || a.role || '开发',
            status: 'idle'
          })))
        }
      }
    } catch (err) { console.error(err) }
  }

  const fetchTasks = async () => {
    try {
      const res = await fetch('/api/tasks/')
      if (res.ok) {
        const data = await res.json()
        setTasks(data.map((t: any) => ({
          id: t.id,
          title: t.title,
          status: t.status,
          priority: t.priority
        })))
      }
    } catch (err) { console.error(err) }
  }

  const fetchPipeline = async () => {
    try {
      const res = await fetch('/api/pipelines/active')
      if (res.ok) {
        const data = await res.json()
        if (data.pipeline) setPipeline(data.pipeline)
      }
    } catch (err) { console.error(err) }
  }

  const fetchMessages = async () => {
    try {
      const res = await fetch('/api/messages/history?limit=50')
      if (res.ok) {
        const data = await res.json()
        if (data.length > 0) {
          setMessages(data.map((m: any) => ({
            id: m.id,
            sender: m.sender_id,
            senderName: m.sender_name,
            content: m.content,
            timestamp: m.timestamp,
            type: m.message_type
          })))
        }
      }
    } catch (err) { console.error(err) }
  }

  useEffect(() => {
    fetchAgents()
    fetchTasks()
    fetchPipeline()
    fetchMessages()
  }, [])

  useEffect(() => {
    if (isSimulating || pipeline) {
      const interval = setInterval(() => {
        fetchTasks()
        fetchPipeline()
      }, 3000)
      return () => clearInterval(interval)
    }
  }, [isSimulating, pipeline])

  const startSimulation = async () => {
    if (!projectName.trim()) return
    setIsSimulating(true)

    addMessage({ sender: 'system', senderName: '系统', content: `🚀 项目 "${projectName}" 已创建，开始需求分析...`, type: 'system' })
    await sleep(1500)

    addMessage({ sender: 'pm', senderName: '产品经理', content: `我来分析一下需求：${projectReq || '开发一个用户管理系统'}`,
      type: 'text' })
    await sleep(2000)

    addMessage({ sender: 'architect', senderName: '架构师', content: '根据需求，我建议采用前后端分离架构，使用 FastAPI + React，技术栈清晰。',
      type: 'text' })
    await sleep(2000)

    addMessage({ sender: 'pm', senderName: '产品经理', content: '同意，我来拆解任务...',
      type: 'action' })
    await sleep(1500)

    addMessage({ sender: 'system', senderName: '系统', content: '📋 已自动拆解3个任务：数据库设计、API开发、前端界面', type: 'system' })

    for (let i = 0; i < 3; i++) {
      await sleep(2000)
      const taskNames = ['设计数据库表结构', '开发RESTful API', '实现用户管理界面']
      addMessage({ sender: 'backend', senderName: '后端开发', content: `开始任务: ${taskNames[i]}`, type: 'action' })
      await sleep(2500)
      addMessage({ sender: 'backend', senderName: '后端开发', content: `✅ 任务完成: ${taskNames[i]}`, type: 'action' })
    }

    await sleep(1500)
    addMessage({ sender: 'tester', senderName: '测试工程师', content: '开始进行代码审查和测试...', type: 'text' })
    await sleep(2000)
    addMessage({ sender: 'system', senderName: '系统', content: '🎉 项目开发完成！所有任务已审核通过。', type: 'system' })

    setIsSimulating(false)
  }

  const addMessage = (msg: Omit<Message, 'id' | 'timestamp'>) => {
    setMessages(prev => [...prev, {
      ...msg,
      id: `msg-${Date.now()}-${Math.random()}`,
      timestamp: new Date().toLocaleTimeString()
    }])
  }

  const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

  const handleIntervention = () => {
    if (!interventionInput.trim()) return
    addMessage({ sender: 'human', senderName: '👤 你', content: interventionInput, type: 'text' })
    addMessage({ sender: 'system', senderName: '系统', content: `[收到人工干预] ${interventionInput}`, type: 'action' })
    setInterventionInput('')
  }

  const getTasksByStatus = (status: string) => tasks.filter(t => t.status === status)

  return (
    <div className="flex-1 flex flex-col h-full bg-gray-900 text-gray-100 overflow-hidden">
      {/* Top Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-bold text-primary-400">🚀 开发工作台</h2>
          {pipeline && (
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${STATUS_COLORS[pipeline.status] || 'bg-gray-400'}`} />
              <span className="text-sm text-gray-300">{STAGE_LABELS[pipeline.current_stage] || pipeline.current_stage}</span>
              <span className="text-sm text-gray-500">({Math.round(pipeline.progress * 100)}%)</span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isSimulating ? (
            <span className="text-sm text-green-400 animate-pulse">● 运行中</span>
          ) : pipeline ? (
            <span className="text-sm text-blue-400">流水线运行中</span>
          ) : (
            <span className="text-sm text-gray-500">空闲</span>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Agent Team */}
        <div className="w-64 bg-gray-800 border-r border-gray-700 flex flex-col">
          <div className="p-3 border-b border-gray-700">
            <h3 className="text-sm font-medium text-gray-300 mb-2">👥 Agent团队</h3>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-2">
            {agents.length > 0 ? agents.map(agent => (
              <div key={agent.id} className="bg-gray-700/50 rounded-lg p-2">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${STATUS_COLORS[agent.status] || 'bg-gray-400'}`} />
                  <span className="text-sm font-medium text-white">{agent.name}</span>
                </div>
                <div className="text-xs text-gray-400 mt-1">{agent.role}</div>
              </div>
            )) : (
              <>
                {['产品经理', '架构师', '后端开发', '前端开发', '测试工程师'].map(role => (
                  <div key={role} className="bg-gray-700/50 rounded-lg p-2">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-gray-400" />
                      <span className="text-sm font-medium text-white">{role}</span>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">就绪</div>
                  </div>
                ))}
              </>
            )}
          </div>
          <div className="p-3 border-t border-gray-700">
            <div className="text-xs text-gray-500 mb-2">发言顺序</div>
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <span className="w-5 h-5 bg-primary-600 rounded-full flex items-center justify-center text-white">1</span>
                <span>产品经理</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <span className="w-5 h-5 bg-gray-600 rounded-full flex items-center justify-center text-white">2</span>
                <span>架构师</span>
              </div>
            </div>
          </div>
        </div>

        {/* Center Panel - Discussion */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Project Setup */}
          {!pipeline && !isSimulating && (
            <div className="p-4 bg-gray-800/50 border-b border-gray-700">
              <h3 className="text-sm font-medium text-gray-300 mb-3">📝 创建项目</h3>
              <div className="flex gap-3">
                <input
                  type="text"
                  value={projectName}
                  onChange={e => setProjectName(e.target.value)}
                  placeholder="项目名称..."
                  className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:border-primary-500"
                />
                <input
                  type="text"
                  value={projectReq}
                  onChange={e => setProjectReq(e.target.value)}
                  placeholder="需求描述..."
                  className="flex-[2] bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:border-primary-500"
                />
                <button
                  onClick={startSimulation}
                  disabled={!projectName.trim() || isSimulating}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 rounded text-sm font-medium transition-colors"
                >
                  🚀 启动开发
                </button>
              </div>
            </div>
          )}

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 && !isSimulating && (
              <div className="flex items-center justify-center h-full">
                <div className="text-center text-gray-500">
                  <p className="text-lg mb-2">🎯 开始一个新项目</p>
                  <p className="text-sm">输入项目名称和需求，点击"启动开发"</p>
                </div>
              </div>
            )}
            {messages.map(msg => (
              <div key={msg.id} className={`flex ${msg.sender === 'human' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] rounded-lg px-4 py-2 ${
                  msg.sender === 'system' ? 'bg-gray-700/50 border border-gray-600' :
                  msg.sender === 'human' ? 'bg-primary-600 text-white' :
                  'bg-gray-700 text-gray-100'
                }`}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium opacity-70">{msg.senderName}</span>
                    <span className="text-xs opacity-50">{msg.timestamp}</span>
                  </div>
                  <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                </div>
              </div>
            ))}
            {isSimulating && (
              <div className="flex justify-center">
                <div className="animate-pulse text-gray-500 text-sm">● ● ●</div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Intervention Input */}
          {(isSimulating || pipeline) && (
            <div className="p-3 bg-gray-800 border-t border-gray-700">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={interventionInput}
                  onChange={e => setInterventionInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleIntervention()}
                  placeholder="输入干预指令..."
                  className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:border-primary-500"
                />
                <button
                  onClick={handleIntervention}
                  className="px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded text-sm font-medium transition-colors"
                >
                  干预
                </button>
              </div>
              <div className="flex gap-4 mt-2 text-xs text-gray-500">
                <span>暂停: ⏸</span>
                <span>终止: ⏹</span>
                <span>发言: ⌨️</span>
              </div>
            </div>
          )}
        </div>

        {/* Right Panel - Tasks & Progress */}
        <div className="w-80 bg-gray-800 border-l border-gray-700 flex flex-col">
          {/* Pipeline Progress */}
          <div className="p-3 border-b border-gray-700">
            <h3 className="text-sm font-medium text-gray-300 mb-3">📊 开发进度</h3>
            <div className="space-y-3">
              {Object.entries(STAGE_LABELS).map(([key, label], idx) => {
                const stages = Object.keys(STAGE_LABELS)
                const currentIdx = pipeline ? stages.indexOf(pipeline.current_stage) : -1
                const thisIdx = stages.indexOf(key)
                const isActive = pipeline && key === pipeline.current_stage
                const isDone = thisIdx < currentIdx
                return (
                  <div key={key} className="flex items-center gap-2">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                      isActive ? 'bg-primary-500 text-white animate-pulse' :
                      isDone ? 'bg-green-500 text-white' :
                      'bg-gray-600 text-gray-300'
                    }`}>
                      {isDone ? '✓' : idx + 1}
                    </div>
                    <span className={`text-sm ${isActive ? 'text-white font-medium' : 'text-gray-400'}`}>{label}</span>
                    {isActive && <span className="text-xs text-primary-400 animate-pulse">进行中</span>}
                  </div>
                )
              })}
            </div>
            {pipeline && (
              <div className="mt-3">
                <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div className="h-full bg-primary-500 transition-all duration-500" style={{ width: `${pipeline.progress * 100}%` }} />
                </div>
              </div>
            )}
          </div>

          {/* Tasks */}
          <div className="flex-1 overflow-y-auto p-3">
            <h3 className="text-sm font-medium text-gray-300 mb-3">📋 任务列表 ({tasks.length})</h3>
            <div className="space-y-2">
              {['backlog', 'todo', 'in_progress', 'review', 'done'].map(status => {
                const statusTasks = getTasksByStatus(status)
                if (statusTasks.length === 0) return null
                const statusLabels: Record<string, string> = {
                  backlog: '待办', todo: '计划', in_progress: '进行', review: '审核', done: '完成'
                }
                return (
                  <div key={status} className="mb-3">
                    <div className="flex items-center gap-2 mb-1">
                      <div className={`w-2 h-2 rounded-full ${STATUS_COLORS[status]}`} />
                      <span className="text-xs text-gray-400">{statusLabels[status]} ({statusTasks.length})</span>
                    </div>
                    {statusTasks.map(task => (
                      <div key={task.id} className="bg-gray-700/50 rounded px-2 py-1.5 mb-1">
                        <span className="text-xs text-gray-200 truncate block">{task.title}</span>
                      </div>
                    ))}
                  </div>
                )
              })}
              {tasks.length === 0 && !isSimulating && (
                <div className="text-center text-gray-500 text-sm py-4">暂无任务</div>
              )}
            </div>
          </div>

          {/* Logs */}
          {pipeline && pipeline.logs.length > 0 && (
            <div className="p-3 border-t border-gray-700 max-h-40 overflow-y-auto">
              <h3 className="text-xs font-medium text-gray-400 mb-2">📜 最近日志</h3>
              <div className="space-y-1">
                {pipeline.logs.slice(-5).reverse().map((log, idx) => (
                  <div key={idx} className="text-xs">
                    <span className="text-gray-500">{new Date(log.timestamp).toLocaleTimeString()}</span>
                    <span className={`ml-2 ${log.level === 'error' ? 'text-red-400' : 'text-gray-400'}`}>
                      {log.message}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
