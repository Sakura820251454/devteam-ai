import { useStore, type ProjectSummary } from '../lib/store'

interface ProjectSwitcherProps {
  onNewProject: () => void
}

export default function ProjectSwitcher({ onNewProject }: ProjectSwitcherProps) {
  const projects = useStore((s) => s.projects)
  const activeProjectId = useStore((s) => s.activeProjectId)
  const switchProject = useStore((s) => s.switchProject)
  const closeProject = useStore((s) => s.closeProject)

  if (projects.length === 0) {
    return (
      <div className="flex items-center gap-2 px-3">
        <span className="text-sm text-slate-500">暂无项目</span>
        <button
          onClick={onNewProject}
          className="px-3 py-1 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
        >
          + 新项目
        </button>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-1 overflow-x-auto px-2 scrollbar-thin">
      {projects.map((project: ProjectSummary) => {
        const isActive = project.id === activeProjectId
        const statusDot = project.status === 'running'
          ? 'bg-green-500'
          : project.status === 'paused'
            ? 'bg-yellow-500'
            : project.status === 'completed'
              ? 'bg-blue-500'
              : 'bg-slate-500'

        return (
          <button
            key={project.id}
            onClick={() => switchProject(project.id)}
            className={`
              group flex items-center gap-1.5 px-3 py-1.5 rounded-t-md text-sm whitespace-nowrap transition-colors
              ${isActive
                ? 'bg-slate-800 text-slate-100 border-t border-x border-slate-700'
                : 'bg-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }
            `}
          >
            <span className={`w-2 h-2 rounded-full ${statusDot}`} />
            <span className="max-w-24 truncate">{project.name}</span>
            <span
              onClick={(e) => {
                e.stopPropagation()
                if (confirm(`关闭项目 "${project.name}"？`)) {
                  closeProject(project.id)
                }
              }}
              className="ml-1 opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 transition-opacity"
            >
              ×
            </span>
          </button>
        )
      })}
      <button
        onClick={onNewProject}
        className="px-2 py-1 text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 rounded transition-colors"
        title="新建项目"
      >
        +
      </button>
    </div>
  )
}
