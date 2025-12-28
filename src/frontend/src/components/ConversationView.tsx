import { useEffect, useRef } from 'react'
import { MessageBubble } from './MessageBubble'
import type { ChatMessage, AgentMode } from '@/types'

interface ConversationViewProps {
  messages: ChatMessage[]
  isLoading?: boolean
}

// Agent mode separator component
function AgentSeparator({ mode }: { mode: AgentMode }) {
  const labels: Record<AgentMode, string> = {
    lesson: 'Switched to Teacher',
    demo: 'Switched to Demo',
    conversation: 'Switched to Practice Partner',
  }

  return (
    <div className="flex items-center gap-2 py-2">
      <div className="flex-1 border-t border-dashed border-muted-foreground/30" />
      <span className="text-xs text-muted-foreground px-2">
        {labels[mode]}
      </span>
      <div className="flex-1 border-t border-dashed border-muted-foreground/30" />
    </div>
  )
}

// Check if we should show a separator before this message
function shouldShowSeparator(
  message: ChatMessage,
  index: number,
  messages: ChatMessage[]
): AgentMode | null {
  if (index === 0) return null
  if (message.role === 'user') return null

  const currentMode = message.agentMode || 'conversation'

  // Find the previous assistant message
  for (let i = index - 1; i >= 0; i--) {
    if (messages[i].role === 'assistant') {
      const prevMode = messages[i].agentMode || 'conversation'
      if (prevMode !== currentMode) {
        return currentMode
      }
      break
    }
  }

  return null
}

export function ConversationView({
  messages,
  isLoading = false,
}: ConversationViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <p>Select a lesson and start practicing!</p>
      </div>
    )
  }

  return (
    <div
      ref={scrollRef}
      className="flex h-full flex-col gap-4 overflow-y-auto p-4"
    >
      {messages.map((message, index) => {
        const separatorMode = shouldShowSeparator(message, index, messages)
        return (
          <div key={index}>
            {separatorMode && <AgentSeparator mode={separatorMode} />}
            <MessageBubble message={message} />
          </div>
        )
      })}
      {isLoading && (
        <div className="flex justify-start">
          <div className="bg-muted rounded-2xl px-4 py-2">
            <span className="animate-pulse">Thinking...</span>
          </div>
        </div>
      )}
    </div>
  )
}
