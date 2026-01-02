import { useTranslation } from 'react-i18next'
import { GraduationCap, MessageCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ChatMessage, AgentMode, RichContent, VocabularyCardData, PatternCardData } from '@/types'
import { InlineVocabularyCard } from './inline/InlineVocabularyCard'
import { InlinePatternCard } from './inline/InlinePatternCard'

interface MessageBubbleProps {
  message: ChatMessage
}

// Rich content renderer
function RichContentRenderer({ content }: { content: RichContent }) {
  switch (content.type) {
    case 'vocabulary_card':
      return <InlineVocabularyCard data={content.data as VocabularyCardData} />
    case 'pattern_card':
      return <InlinePatternCard data={content.data as PatternCardData} />
    case 'lesson_link':
      // TODO: Implement LessonLink
      return null
    default:
      return null
  }
}

// Agent display configuration (icons and colors only - names are translated)
const AGENT_CONFIG: Record<AgentMode, { nameKey: string; icon: typeof GraduationCap; colors: string }> = {
  help: {
    nameKey: 'agents.helper',
    icon: GraduationCap,
    colors: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200',
  },
  practice: {
    nameKey: 'agents.partner',
    icon: MessageCircle,
    colors: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200',
  },
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const { t } = useTranslation()
  const isUser = message.role === 'user'
  const agentMode = message.agentMode || 'practice'
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

          {/* Rich content (vocabulary cards, etc.) */}
          {message.richContent?.map((content, idx) => (
            <RichContentRenderer key={idx} content={content} />
          ))}
        </div>
      </div>
    </div>
  )
}
