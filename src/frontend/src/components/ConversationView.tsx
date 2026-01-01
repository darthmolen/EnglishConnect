import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { MessageBubble } from './MessageBubble'
import type { ChatMessage, AgentMode } from '@/types'

interface ConversationViewProps {
  messages: ChatMessage[]
  isLoading?: boolean
}

// Agent mode separator component
function AgentSeparator({ mode }: { mode: AgentMode }) {
  const { t } = useTranslation()
  const labels: Record<AgentMode, string> = {
    help: t('agents.switchedToHelp'),
    practice: t('agents.switchedToPractice'),
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

  const currentMode = message.agentMode || 'practice'

  // Find the previous assistant message
  for (let i = index - 1; i >= 0; i--) {
    if (messages[i].role === 'assistant') {
      const prevMode = messages[i].agentMode || 'practice'
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
  const { t } = useTranslation()
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
        <p>{t('conversation.emptyState')}</p>
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
            <span className="animate-pulse">{t('conversation.thinking')}</span>
          </div>
        </div>
      )}
    </div>
  )
}
