import { MessageCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import type { QAPattern } from '@/types'

interface MobilePracticeViewProps {
  patterns: QAPattern[]
  currentIndex: number
  loopingPattern?: number | null
  onSelectPattern: (index: number) => void
  onStartPractice: (patternNumber: number) => void
}

export function MobilePracticeView({
  patterns,
  currentIndex,
  loopingPattern,
  onSelectPattern,
  onStartPractice,
}: MobilePracticeViewProps) {
  const { t } = useTranslation()

  if (patterns.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        {t('mobile.practice.empty', 'No patterns available')}
      </div>
    )
  }

  return (
    <div className="space-y-4 p-1">
      {patterns.map((pattern, index) => {
        const isLooping = loopingPattern === pattern.pattern_number
        return (
          <div
            key={pattern.pattern_number}
            role="button"
            tabIndex={0}
            onClick={() => onSelectPattern(index)}
            onKeyDown={(e) => e.key === 'Enter' && onSelectPattern(index)}
            className={cn(
              'w-full text-left p-4 rounded-xl border transition-all cursor-pointer',
              'min-h-[100px]', // Touch-friendly
              'active:scale-[0.98]',
              index === currentIndex
                ? 'ring-2 ring-primary bg-primary/5 border-primary'
                : 'bg-card hover:bg-accent/50',
              isLooping && 'animate-pulse'
            )}
          >
            <div className="flex items-start gap-3">
              <span className={cn(
                'flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold',
                isLooping ? 'bg-primary text-primary-foreground' : 'bg-primary/20'
              )}>
                {pattern.pattern_number}
              </span>
              <div className="flex-1 min-w-0 space-y-2">
                <div>
                  <div className="text-xs text-muted-foreground mb-0.5">Q:</div>
                  <div className="font-medium">{pattern.question_template}</div>
                  {pattern.question_translation && (
                    <div className="text-sm text-muted-foreground italic">({pattern.question_translation})</div>
                  )}
                </div>
                <div>
                  <div className="text-xs text-muted-foreground mb-0.5">A:</div>
                  <div className="text-muted-foreground">{pattern.answer_template}</div>
                  {pattern.answer_translation && (
                    <div className="text-sm text-muted-foreground/70 italic">({pattern.answer_translation})</div>
                  )}
                </div>
              </div>
            </div>

            {/* Practice button */}
            <div className="flex gap-2 mt-3 pt-3 border-t">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  onStartPractice(pattern.pattern_number)
                }}
                className={cn(
                  'flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg',
                  'bg-primary text-primary-foreground',
                  'hover:bg-primary/90 active:bg-primary/80',
                  'text-sm transition-colors'
                )}
              >
                <MessageCircle className="h-4 w-4" />
                <span>{t('mobile.practice.practice', 'Practice')}</span>
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
