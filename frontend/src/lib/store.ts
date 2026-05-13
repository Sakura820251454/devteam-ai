import { create } from 'zustand'
import type { Agent, Session, Message } from './api'

interface AppState {
  agent: Agent | null
  sessions: Session[]
  currentSession: Session | null
  messages: Message[]
  isLoading: boolean
  isConnected: boolean
  error: string | null
  
  setAgent: (agent: Agent | null) => void
  setSessions: (sessions: Session[]) => void
  setCurrentSession: (session: Session | null) => void
  setMessages: (messages: Message[]) => void
  addMessage: (message: Message) => void
  appendMessageContent: (messageId: string, content: string) => void
  setLoading: (loading: boolean) => void
  setConnected: (connected: boolean) => void
  setError: (error: string | null) => void
}

export const useStore = create<AppState>((set) => ({
  agent: null,
  sessions: [],
  currentSession: null,
  messages: [],
  isLoading: false,
  isConnected: false,
  error: null,
  
  setAgent: (agent) => set({ agent }),
  setSessions: (sessions) => set({ sessions }),
  setCurrentSession: (session) => set({ currentSession: session }),
  setMessages: (messages) => set({ messages }),
  addMessage: (message) => set((state) => ({ 
    messages: [...state.messages, message] 
  })),
  appendMessageContent: (messageId, content) => set((state) => ({
    messages: state.messages.map((msg) =>
      msg.id === messageId 
        ? { ...msg, content: msg.content + content }
        : msg
    ),
  })),
  setLoading: (loading) => set({ isLoading: loading }),
  setConnected: (connected) => set({ isConnected: connected }),
  setError: (error) => set({ error }),
}))
