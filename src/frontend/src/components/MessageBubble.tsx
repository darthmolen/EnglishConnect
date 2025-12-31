import { useTranslation } from 'react-i18next'
import { GraduationCap, MessageCircle, Volume2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ChatMessage, AgentMode } from '@/types'

interface MessageBubbleProps {
  message: ChatMessage
}

// Agent display configuration (icons and colors only - names are translated)
const AGENT_CONFIG: Record<AgentMode, { nameKey: string; icon: typeof GraduationCap; colors: string }> = {
  lesson: {
    nameKey: 'agents.teacher',
    icon: GraduationCap,
    colors: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200',
  },
  demo: {
    nameKey: 'agents.demo',
    icon: Volume2,
    colors: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-200',
  },
  conversation: {
    nameKey: 'agents.partner',
    icon: MessageCircle,
    colors: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200',
  },
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const { t } = useTranslation()
  const isUser = message.role === 'user'
  const agentMode = message.agentMode || 'conversation'
  const agentConfig = AGENT_CONFIG[agentMode]
  const Icon = agentConfig.icon

  return (
    <div
      className={cn(
        'flex w-full',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      <div className={cn('max-w-[80%]', !isUser && 'flex flex-col gap-1')}>
        {/* Agent label for assistant messages */}
        {!isUser && (
          <div className="flex items-center gap-1.5 px-1">
            <Icon className="h-3 w-3 text-muted-foreground" />
            <span className="text-xs font-medium text-muted-foreground">
              {t(agentConfig.nameKey)}
            </span>
          </div>
        )}
        <div
          className={cn(
            'rounded-2xl px-4 py-2',
            isUser
              ? 'bg-primary text-primary-foreground'
              : agentConfig.colors
          )}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    </div>
  )
}
