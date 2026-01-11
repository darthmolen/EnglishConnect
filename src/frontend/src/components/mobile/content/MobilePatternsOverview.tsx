import { Play, Pause } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import type { QAPattern } from '@/types'

interface MobilePatternsOverviewProps {
  patterns: QAPattern[]
  playingPattern: number | null
  onPlayPattern: (patternNumber: number) => void
}

export function MobilePatternsOverview({
  patterns,
  playingPattern,
  onPlayPattern,
}: MobilePatternsOverviewProps) {
  const { t } = useTranslation()

  if (patterns.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground p-4">
        {t('mobile.patterns.empty', 'No patterns available')}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {patterns.map((pattern) => {
        const isPlaying = playingPattern === pattern.pattern_number
        return (
          <div
            key={pattern.pattern_number}
            className={cn(
              'rounded-xl border bg-card p-4 space-y-3',
              isPlaying && 'ring-2 ring-primary'
            )}
          >
            {/* Header with pattern number and play button */}
            <div className="flex items-center justify-between">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-bold">
                {pattern.pattern_number}
              </span>
              <button
                type="button"
                aria-label={isPlaying ? `Stop pattern ${pattern.pattern_number}` : `Play pattern ${pattern.pattern_number}`}
                onClick={() => onPlayPattern(pattern.pattern_number)}
                className={cn(
                  'flex items-center justify-center',
                  'h-12 w-12 rounded-full',
                  isPlaying
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-primary/10 text-primary hover:bg-primary/20 active:bg-primary/30',
                  'transition-colors'
                )}
              >
                {isPlaying ? (
                  <Pause className="h-5 w-5" />
                ) : (
                  <Play className="h-5 w-5 ml-0.5" />
                )}
              </button>
            </div>

            {/* Question template */}
            <div className="space-y-1">
              <div className="text-base font-medium">{pattern.question_template}</div>
              {pattern.question_translation && (
                <div className="text-sm text-muted-foreground">{pattern.question_translation}</div>
              )}
            </div>

            {/* Answer template */}
            <div className="space-y-1 border-t pt-3">
              <div className="text-base">{pattern.answer_template}</div>
              {pattern.answer_translation && (
                <div className="text-sm text-muted-foreground">{pattern.answer_translation}</div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
