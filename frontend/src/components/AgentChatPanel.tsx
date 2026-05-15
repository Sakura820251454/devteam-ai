import { useEffect, useRef } from 'react'
import { useStore } from '../lib/store'
import type { ChatMessage } from '../lib/store'

function ChatBubble({ msg, isConsecutive }: { msg: ChatMessage; isConsecutive: boolean }) {
  return (
    <div className={`flex gap-2.5 ${isConsecutive ? 'mt-0.5' : 'mt-3'}`}>
      {isConsecutive ? (
        <div className="w-8 shrink-0" />
      ) : (
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 mt-0.5"
          style={{ backgroundColor: `${msg.agentColor}30`, color: msg.agentColor }}
        >
          {msg.agentName.substring(0, 2)}
        </div>
      )}

      <div className="flex-1 min-w-0">
        {!isConsecutive && (
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="text-sm font-medium text-surface-200">{msg.agentName}</span>
            <span className="text-xs text-surface-500 font-mono">
              {new Date(msg.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          </div>
        )}
        <div
          className="text-sm text-surface-100 leading-relaxed rounded-lg px-3 py-2 inline-block max-w-full"
          style={{
            backgroundColor: isConsecutive ? 'transparent' : `${msg.agentColor}10`,
            borderLeft: isConsecutive ? 'none' : `2px solid ${msg.agentColor}40`,
            paddingLeft: isConsecutive ? '0' : undefined,
          }}
        >
          <p className="whitespace-pre-wrap break-words">{msg.content}</p>
        </div>
      </div>
    </div>
  )
}

export default function AgentChatPanel() {
  const { chatMessages, pipeline } = useStore()
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages.length])

  if (chatMessages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-surface-500 p-4">
        <div className="text-3xl mb-3">💬</div>
        <p className="text-sm text-center">
          {pipeline ? '等待 Agent 开始交流...' : '启动项目后，这里将展示 Agent 之间的讨论'}
        </p>
        <p className="text-xs mt-1.5 text-surface-600 text-center">
          Agent 会在 Pipeline 各阶段自动沟通协作
        </p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto p-3">
      {chatMessages.map((msg, i) => {
        const prev = i > 0 ? chatMessages[i - 1] : null
        const isConsecutive = prev !== null &&
          prev.agentId === msg.agentId &&
          new Date(msg.timestamp).getTime() - new Date(prev.timestamp).getTime() < 60000

        return <ChatBubble key={msg.id} msg={msg} isConsecutive={isConsecutive} />
      })}
      <div ref={endRef} />
    </div>
  )
}
