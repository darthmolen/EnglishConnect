import { X, Mic, MicOff } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
}

interface PinnedCard {
  title: string
  content: string
}

interface MobileChatOverlayProps {
  isOpen: boolean
  onClose: () => void
  messages: Message[]
  pinnedCard: PinnedCard | null
  isRecording: boolean
  voiceMode: 'push-to-talk' | 'active'
  onToggleRecording: () => void
  onToggleVoiceMode: () => void
  isLoading?: boolean
}

export function MobileChatOverlay({
  isOpen,
  onClose,
  messages,
  pinnedCard,
  isRecording,
  voiceMode,
  onToggleRecording,
  onToggleVoiceMode,
  isLoading = false,
}: MobileChatOverlayProps) {
  const { t } = useTranslation()

  if (!isOpen) return null

  return (
    <div className="fixed inset-x-0 top-0 bottom-[112px] z-50 flex flex-col bg-background animate-in slide-in-from-bottom duration-300">
      {/* Header with close button */}
      <header className="flex items-center justify-between p-3 border-b shrink-0">
        <h2 className="font-semibold">{t('mobile.chat.title', 'Practice')}</h2>
        <button
          type="button"
          aria-label="Close"
          onClick={onClose}
          className="p-2 rounded-full hover:bg-accent transition-colors"
        >
          <X className="h-5 w-5" />
        </button>
      </header>

      {/* Pinned context card */}
      {pinnedCard && (
        <div className="mx-3 mt-3 p-3 rounded-lg bg-primary/5 border border-primary/20 shrink-0">
          <div className="text-xs font-medium text-primary mb-1">{pinnedCard.title}</div>
          <div className="text-sm">{pinnedCard.content}</div>
        </div>
      )}

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map((message) => (
          <div
            key={message.id}
            className={cn(
              'flex',
              message.role === 'user' ? 'justify-end' : 'justify-start'
            )}
          >
            <div
              className={cn(
                'max-w-[80%] px-4 py-2 rounded-2xl',
                message.role === 'user'
                  ? 'bg-primary text-primary-foreground rounded-br-md'
                  : 'bg-muted rounded-bl-md'
              )}
            >
              {message.content}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-muted px-4 py-2 rounded-2xl rounded-bl-md">
              <span className="animate-pulse">...</span>
            </div>
          </div>
        )}
      </div>

      {/* Mic bar */}
      <div className="p-3 border-t bg-card shrink-0">
        <div className="flex items-center justify-center gap-4">
          {/* Voice mode toggle */}
          <button
            type="button"
            onClick={onToggleVoiceMode}
            className={cn(
              'flex items-center gap-1.5 px-3 py-2 rounded-full text-sm',
              'border transition-colors',
              voiceMode === 'active'
                ? 'bg-primary/10 border-primary text-primary'
                : 'bg-muted border-transparent'
            )}
          >
            {voiceMode === 'push-to-talk' ? (
              <>
                <MicOff className="h-4 w-4" />
                <span>PTT</span>
              </>
            ) : (
              <>
                <Mic className="h-4 w-4" />
                <span>{t('voice.active', 'Active')}</span>
              </>
            )}
          </button>

          {/* Main mic button */}
          <button
            type="button"
            aria-label="Microphone"
            onClick={onToggleRecording}
            className={cn(
              'flex items-center justify-center',
              'h-16 w-16 rounded-full',
              'transition-all duration-200',
              isRecording
                ? 'bg-destructive text-destructive-foreground scale-110'
                : 'bg-primary text-primary-foreground hover:bg-primary/90'
            )}
          >
            <Mic className="h-7 w-7" />
          </button>

          {/* Spacer to balance layout */}
          <div className="w-[72px]" />
        </div>
      </div>
    </div>
  )
}
