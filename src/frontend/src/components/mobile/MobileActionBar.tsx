import { Play, SkipForward, MessageCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'

export type ContentSection = 'principle' | 'goals' | 'vocabulary' | 'practice' | 'evaluate'

interface MobileActionBarProps {
  section: ContentSection
  onPlay: () => void
  onNext: () => void
  onChat: () => void
  disabled?: boolean
}

export function MobileActionBar({ section, onPlay, onNext, onChat, disabled = false }: MobileActionBarProps) {
  const { t } = useTranslation()

  // Determine which buttons are enabled based on section
  const playEnabled = !disabled && ['vocabulary', 'practice', 'principle'].includes(section)
  const nextEnabled = !disabled && ['vocabulary', 'practice'].includes(section)
  const chatEnabled = !disabled && ['vocabulary', 'practice'].includes(section)

  const buttons = [
    {
      id: 'play',
      label: t('mobile.actions.play', 'Play'),
      icon: <Play className="h-5 w-5" />,
      onClick: onPlay,
      enabled: playEnabled,
    },
    {
      id: 'next',
      label: t('mobile.actions.next', 'Next'),
      icon: <SkipForward className="h-5 w-5" />,
      onClick: onNext,
      enabled: nextEnabled,
    },
    {
      id: 'chat',
      label: t('mobile.actions.chat', 'Chat'),
      icon: <MessageCircle className="h-5 w-5" />,
      onClick: onChat,
      enabled: chatEnabled,
    },
  ]

  return (
    <div className="flex border-t bg-card">
      {buttons.map((button) => (
        <button
          key={button.id}
          type="button"
          onClick={button.onClick}
          disabled={!button.enabled}
          className={cn(
            'flex flex-1 flex-col items-center justify-center gap-1 py-2',
            'min-h-[48px] transition-colors', // Touch-friendly
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset',
            button.enabled
              ? 'text-foreground hover:bg-accent/50 active:bg-accent'
              : 'text-muted-foreground/50 cursor-not-allowed'
          )}
        >
          {button.icon}
          <span className="text-xs font-medium">{button.label}</span>
        </button>
      ))}
    </div>
  )
}
