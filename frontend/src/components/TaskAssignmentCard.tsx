import { Agent, AgentAssignment } from '../types/agent-pool'

interface TaskAssignmentCardProps {
  agent: Agent
  assignment: AgentAssignment
  taskName: string
  taskStatus: 'planning' | 'executing' | 'completed'
  onRemove?: () => void
}

const TEMP_ROLE_LABELS: Record<string, { label: string; color: string }> = {
  requirement: { label: '需求分析', color: '#3B82F6' },
  design: { label: '架构设计', color: '#8B5CF6' },
  backend: { label: '后端开发', color: '#10B981' },
  frontend: { label: '前端开发', color: '#F59E0B' },
  testing: { label: '测试验证', color: '#EF4444' },
  review: { label: '代码评审', color: '#EC4899' },
  deploy: { label: '部署运维', color: '#06B6D4' },
  document: { label: '文档编写', color: '#6366F1' }
}

const STATUS_CONFIG = {
  planning: { label: '规划中', color: '#F59E0B', bg: 'bg-yellow-500/20' },
  executing: { label: '执行中', color: '#10B981', bg: 'bg-green-500/20' },
  completed: { label: '已完成', color: '#6B7280', bg: 'bg-gray-500/20' }
}

export default function TaskAssignmentCard({ 
  agent, 
  assignment, 
  taskName,
  taskStatus,
  onRemove 
}: TaskAssignmentCardProps) {
  const roleInfo = TEMP_ROLE_LABELS[assignment.tempRole] || { label: assignment.tempRole, color: '#6B7280' }
  const statusInfo = STATUS_CONFIG[taskStatus]

  return (
    <div className="bg-gray-700/50 rounded-lg p-4 border border-gray-600">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center text-xl"
            style={{ backgroundColor: `${agent.avatar_color}30` }}
          >
            {agent.avatar_emoji}
          </div>
          <div>
            <div className="font-medium text-white">{agent.name}</div>
            <div className="text-xs text-gray-400">原始: {agent.baseRole}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span 
            className={`text-xs px-2 py-1 rounded ${statusInfo.bg}`}
            style={{ color: statusInfo.color }}
          >
            {statusInfo.label}
          </span>
          {onRemove && (
            <button
              onClick={onRemove}
              className="text-gray-500 hover:text-red-400 text-sm"
            >
              ×
            </button>
          )}
        </div>
      </div>

      <div className="mb-2">
        <span 
          className="text-sm px-3 py-1 rounded-full font-medium"
          style={{ backgroundColor: `${roleInfo.color}30`, color: roleInfo.color }}
        >
          {roleInfo.label}
        </span>
      </div>

      {assignment.tempDescription && (
        <p className="text-sm text-gray-300 mt-2">{assignment.tempDescription}</p>
      )}

      <div className="mt-3 pt-3 border-t border-gray-600">
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <span>项目:</span>
          <span className="text-gray-300">{taskName}</span>
        </div>
      </div>
    </div>
  )
}

interface TeamTaskOverviewProps {
  taskName: string
  assignments: AgentAssignment[]
  agents: Agent[]
  taskStatus: 'planning' | 'executing' | 'completed'
}

export function TeamTaskOverview({ 
  taskName, 
  assignments, 
  agents,
  taskStatus 
}: TeamTaskOverviewProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-white">当前项目团队</h3>
        <span className={`text-xs px-2 py-1 rounded ${
          taskStatus === 'executing' ? 'bg-green-500/20 text-green-400' :
          taskStatus === 'planning' ? 'bg-yellow-500/20 text-yellow-400' :
          'bg-gray-500/20 text-gray-400'
        }`}>
          {taskStatus === 'executing' ? '执行中' : taskStatus === 'planning' ? '规划中' : '已完成'}
        </span>
      </div>
      
      <p className="text-xs text-gray-400">{taskName}</p>

      <div className="grid grid-cols-2 gap-2">
        {assignments.map(assignment => {
          const agent = agents.find(a => a.id === assignment.agentId)
          if (!agent) return null
          return (
            <TaskAssignmentCard
              key={assignment.agentId}
              agent={agent}
              assignment={assignment}
              taskName={taskName}
              taskStatus={taskStatus}
            />
          )
        })}
      </div>
    </div>
  )
}
