import { useState, useEffect } from 'react'
import CollaborationView from '../components/CollaborationView'

type Tab = 'collaboration' | 'tasks'

interface TaskResponse {
  id: string
  title: string
  description: string
  status: string
  priority: string
  assigned_agents: string[]
  created_by: string
  tags: string[]
  created_at: string
  updated_at: string
}

interface BoardResponse {
  total: number
  columns: Record<string, TaskResponse[]>
}

const STATUS_COLUMNS = [
  { key: 'backlog', label: '待办', color: 'bg-gray-600' },
  { key: 'todo', label: '计划中', color: 'bg-blue-600' },
  { key: 'in_progress', label: '进行中', color: 'bg-yellow-600' },
  { key: 'review', label: '审核', color: 'bg-purple-600' },
  { key: 'done', label: '完成', color: 'bg-green-600' },
]

const PRIORITY_COLORS: Record<string, string> = {
  low: 'bg-gray-400',
  medium: 'bg-blue-400',
  high: 'bg-orange-400',
  urgent: 'bg-red-400'
}

function TasksTab() {
  const [board, setBoard] = useState<BoardResponse | null>(null)
  const [newTaskTitle, setNewTaskTitle] = useState('')
  const [newTaskPriority, setNewTaskPriority] = useState('medium')
  const [isCreating, setIsCreating] = useState(false)

  const fetchBoard = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/tasks/board/all')
      if (res.ok) setBoard(await res.json())
    } catch (err) { console.error('Failed to fetch board:', err) }
  }

  const createTask = async () => {
    if (!newTaskTitle.trim()) return
    setIsCreating(true)
    try {
      await fetch('http://localhost:8000/api/tasks/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTaskTitle, priority: newTaskPriority, created_by: 'user' })
      })
      setNewTaskTitle('')
      fetchBoard()
    } catch (err) { console.error('Failed to create task:', err) }
    finally { setIsCreating(false) }
  }

  const updateTaskStatus = async (taskId: string, newStatus: string) => {
    try {
      await fetch(`http://localhost:8000/api/tasks/${taskId}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus, changed_by: 'user' })
      })
      fetchBoard()
    } catch (err) { console.error('Failed to update task:', err) }
  }

  useEffect(() => { fetchBoard() }, [])

  const totalTasks = board?.total || 0
  const completedTasks = board?.columns['done']?.length || 0
  const inProgressTasks = board?.columns['in_progress']?.length || 0

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-gray-900">
      <div className="flex-1 overflow-y-auto p-4">
        <div className="flex gap-4 mb-4">
          <div className="bg-gray-800 rounded-lg px-4 py-2 flex items-center gap-2">
            <span className="text-gray-400 text-sm">总任务</span>
            <span className="text-white font-bold text-lg">{totalTasks}</span>
          </div>
          <div className="bg-yellow-900/30 border border-yellow-700/50 rounded-lg px-4 py-2 flex items-center gap-2">
            <span className="text-yellow-400 text-sm">进行中</span>
            <span className="text-yellow-400 font-bold text-lg">{inProgressTasks}</span>
          </div>
          <div className="bg-green-900/30 border border-green-700/50 rounded-lg px-4 py-2 flex items-center gap-2">
            <span className="text-green-400 text-sm">已完成</span>
            <span className="text-green-400 font-bold text-lg">{completedTasks}</span>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-4 mb-4">
          <h3 className="text-sm font-medium text-gray-300 mb-3">快速创建任务</h3>
          <div className="flex gap-3">
            <input
              type="text"
              value={newTaskTitle}
              onChange={(e) => setNewTaskTitle(e.target.value)}
              placeholder="输入任务标题..."
              className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 focus:outline-none focus:border-primary-500"
              onKeyDown={(e) => e.key === 'Enter' && createTask()}
            />
            <select
              value={newTaskPriority}
              onChange={(e) => setNewTaskPriority(e.target.value)}
              className="bg-gray-700 border border-gray-600 rounded px-3 py-2 focus:outline-none focus:border-primary-500"
            >
              <option value="low">低</option>
              <option value="medium">中</option>
              <option value="high">高</option>
              <option value="urgent">紧急</option>
            </select>
            <button
              onClick={createTask}
              disabled={!newTaskTitle.trim() || isCreating}
              className="px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-600 rounded transition-colors"
            >
              {isCreating ? '创建中...' : '创建'}
            </button>
          </div>
        </div>

        <div className="flex gap-4 h-[calc(100%-180px)] overflow-x-auto">
          {STATUS_COLUMNS.map(({ key, label, color }) => (
            <div key={key} className="flex-shrink-0 w-72 flex flex-col bg-gray-800/50 rounded-lg">
              <div className={`${color} text-white px-4 py-2 rounded-t-lg font-medium flex items-center justify-between`}>
                <span>{label}</span>
                <span className="bg-white/20 px-2 py-0.5 rounded text-sm">{board?.columns[key]?.length || 0}</span>
              </div>
              <div className="flex-1 overflow-y-auto p-2 space-y-2">
                {board?.columns[key]?.map((task) => (
                  <div key={task.id} className="bg-gray-700 rounded p-3 hover:bg-gray-650 transition-colors">
                    <div className="flex items-start gap-2">
                      <div className={`w-2 h-2 mt-1.5 rounded-full flex-shrink-0 ${PRIORITY_COLORS[task.priority] || 'bg-gray-400'}`} />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm text-white truncate">{task.title}</div>
                        <div className="flex gap-1 mt-2 flex-wrap">
                          {key === 'backlog' && (
                            <button onClick={() => updateTaskStatus(task.id, 'todo')} className="text-xs text-blue-400 hover:text-blue-300 bg-blue-900/30 px-2 py-1 rounded">→ 开始</button>
                          )}
                          {key === 'todo' && (
                            <button onClick={() => updateTaskStatus(task.id, 'in_progress')} className="text-xs text-yellow-400 hover:text-yellow-300 bg-yellow-900/30 px-2 py-1 rounded">→ 进行</button>
                          )}
                          {key === 'in_progress' && (
                            <>
                              <button onClick={() => updateTaskStatus(task.id, 'review')} className="text-xs text-purple-400 hover:text-purple-300 bg-purple-900/30 px-2 py-1 rounded">→ 审核</button>
                              <button onClick={() => updateTaskStatus(task.id, 'todo')} className="text-xs text-gray-400 hover:text-gray-300 bg-gray-600/50 px-2 py-1 rounded">← 退回</button>
                            </>
                          )}
                          {key === 'review' && (
                            <>
                              <button onClick={() => updateTaskStatus(task.id, 'done')} className="text-xs text-green-400 hover:text-green-300 bg-green-900/30 px-2 py-1 rounded">✓ 完成</button>
                              <button onClick={() => updateTaskStatus(task.id, 'in_progress')} className="text-xs text-yellow-400 hover:text-yellow-300 bg-yellow-900/30 px-2 py-1 rounded">← 重做</button>
                            </>
                          )}
                          {key === 'done' && (
                            <button onClick={() => updateTaskStatus(task.id, 'review')} className="text-xs text-gray-400 hover:text-gray-300 bg-gray-600/50 px-2 py-1 rounded">← 重新审核</button>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                {(!board?.columns[key] || board.columns[key].length === 0) && (
                  <div className="text-center text-gray-500 py-8 text-sm">暂无任务</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>('collaboration')

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-gray-100">
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-primary-400">DevTeam-AI</h1>
          <div className="text-sm text-gray-500">
            多智能体协同开发平台
          </div>
        </div>
      </header>
      <div className="bg-gray-800 border-b border-gray-700 px-6">
        <div className="flex gap-1">
          <button
            onClick={() => setActiveTab('collaboration')}
            className={`px-4 py-3 font-medium transition-colors ${
              activeTab === 'collaboration'
                ? 'text-primary-400 border-b-2 border-primary-400'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            🤝 协作模式
          </button>
          <button
            onClick={() => setActiveTab('tasks')}
            className={`px-4 py-3 font-medium transition-colors ${
              activeTab === 'tasks'
                ? 'text-primary-400 border-b-2 border-primary-400'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            📋 任务看板
          </button>
        </div>
      </div>
      <main className="flex-1 flex flex-col overflow-hidden">
        {activeTab === 'collaboration' && <CollaborationView />}
        {activeTab === 'tasks' && <TasksTab />}
      </main>
    </div>
  )
}
