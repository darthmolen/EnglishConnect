import type { ReactNode } from 'react'
import { Play, SkipForward, MessageCircle, Repeat, Square } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import type { LoopMode } from '@/hooks/useSectionLoop'

export type ContentSection = 'principle' | 'vocabulary' | 'patterns' | 'examples' | 'practice' | 'evaluate'

interface MobileActionBarProps {
  section: ContentSection
  onPlay: () => void
  onNext: () => void
  onChat: () => void
  onLoop: () => void
  loopMode: LoopMode
  disabled?: boolean
  chatDisabled?: boolean
}

// The loop control is a simple toggle: idle (off) starts looping the whole
// section, and while looping it becomes a Stop button. Each state is encoded
// three ways -- glyph, colour, and label -- so no single channel carries the
// meaning: the Repeat vs Square glyph survives colour-vision deficiency and
// direct sunlight where colour alone would not.
const LOOP_STATES: Record<LoopMode, { labelKey: string; fallback: string; className: string }> = {
  off: {
    labelKey: 'mobile.actionBar.loop',
    fallback: 'Loop',
    className: '',
  },
  all: {
    labelKey: 'mobile.actionBar.stop',
    fallback: 'Stop',
    className: 'bg-primary text-primary-foreground hover:bg-primary/90 active:bg-primary/80',
  },
}

export function MobileActionBar({ section, onPlay, onNext, onChat, onLoop, loopMode, disabled = false, chatDisabled = false }: MobileActionBarProps) {
  const { t } = useTranslation()

  // Determine which buttons are enabled based on section
  // patterns = new pattern overview with play buttons, examples = flat example cards
  const playEnabled = !disabled && ['vocabulary', 'patterns', 'examples', 'practice'].includes(section)
  const nextEnabled = !disabled && ['vocabulary', 'patterns', 'examples', 'practice'].includes(section)
  // Chat requires authentication (chatDisabled) AND is only available on certain sections
  const chatEnabled = !disabled && !chatDisabled && ['vocabulary', 'practice'].includes(section)
  // Practice is excluded: it already has its own per-pattern loop via
  // playPatternLoop, and two competing loop controls in one bar would confuse.
  const loopEnabled = !disabled && ['vocabulary', 'patterns', 'examples'].includes(section)

  const loopState = LOOP_STATES[loopMode]

  const buttons: Array<{
    id: string
    label: string
    icon: ReactNode
    onClick: () => void
    enabled: boolean
    pressed?: boolean
    className?: string
  }> = [
    {
      id: 'play',
      label: t('mobile.actionBar.play', 'Play'),
      icon: <Play className="h-5 w-5" />,
      onClick: onPlay,
      enabled: playEnabled,
    },
    {
      id: 'next',
      label: t('mobile.actionBar.next', 'Next'),
      icon: <SkipForward className="h-5 w-5" />,
      onClick: onNext,
      enabled: nextEnabled,
    },
    {
      id: 'loop',
      label: t(loopState.labelKey, loopState.fallback),
      icon: loopMode === 'all' ? <Square className="h-5 w-5" /> : <Repeat className="h-5 w-5" />,
      onClick: onLoop,
      enabled: loopEnabled,
      pressed: loopMode !== 'off',
      className: loopEnabled ? loopState.className : '',
    },
    {
      id: 'chat',
      label: t('mobile.actionBar.chat', 'Chat'),
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
          aria-pressed={button.pressed}
          className={cn(
            'flex flex-1 flex-col items-center justify-center gap-1 py-2',
            'min-h-[48px] transition-colors', // Touch-friendly
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset',
            button.enabled
              ? 'text-foreground hover:bg-accent/50 active:bg-accent'
              : 'text-muted-foreground/50 cursor-not-allowed',
            button.className
          )}
        >
          {button.icon}
          <span className="text-xs font-medium">{button.label}</span>
        </button>
      ))}
    </div>
  )
}
