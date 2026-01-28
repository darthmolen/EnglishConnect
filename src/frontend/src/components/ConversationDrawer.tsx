import { useTranslation } from 'react-i18next'
import { MessageSquare, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ConversationView } from './ConversationView'
import type { ChatMessage } from '@/types'

interface ConversationDrawerProps {
  isOpen: boolean
  onToggle: () => void
  onEndSession: () => void
  messages: ChatMessage[]
  isLoading: boolean
}

export function ConversationDrawer({
  isOpen,
  onToggle,
  onEndSession,
  messages,
  isLoading,
}: ConversationDrawerProps) {
  const { t } = useTranslation()

  return (
    <>
      {/* Toggle button - hidden on mobile */}
      <button
        type="button"
        onClick={onToggle}
        className={cn(
          'absolute bottom-4 right-4 z-10',
          'hidden md:flex items-center gap-2',
          'rounded-full px-3 py-2 shadow-lg',
          'bg-primary text-primary-foreground',
          'hover:bg-primary/90 transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-ring'
        )}
      >
        <MessageSquare className="h-4 w-4" />
        <span className="text-sm font-medium">
          {isOpen ? t('conversation.hide') : t('conversation.transcript')}
        </span>
        {messages.length > 0 && !isOpen && (
          <span className="ml-1 rounded-full bg-primary-foreground/20 px-1.5 py-0.5 text-xs">
            {messages.length}
          </span>
        )}
      </button>

      {/* Drawer panel - hidden on mobile */}
      <div
        className={cn(
          'absolute top-0 right-0 h-full w-72 z-20',
          'hidden md:flex flex-col',
          'bg-background border-l shadow-lg',
          'transform transition-transform duration-200 ease-in-out',
          isOpen ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        {/* Drawer header */}
        <div className="flex items-center justify-between border-b p-3 shrink-0">
          <h3 className="font-semibold text-sm">{t('conversation.title')}</h3>
          <button
            type="button"
            onClick={onEndSession}
            className={cn(
              'flex items-center gap-1 px-2 py-1 rounded-md text-xs',
              'text-destructive hover:bg-destructive/10',
              'focus:outline-none focus:ring-2 focus:ring-ring'
            )}
          >
            <X className="h-3 w-3" />
            <span>{t('conversation.endSession', 'End Session')}</span>
          </button>
        </div>

        {/* Drawer content */}
        <div className="flex-1 overflow-hidden">
          <ConversationView messages={messages} isLoading={isLoading} />
        </div>
      </div>

      {/* Backdrop when drawer is open */}
      {isOpen && (
        <div
          className="absolute inset-0 bg-black/20 z-10 hidden md:block"
          onClick={onToggle}
        />
      )}
    </>
  )
}
