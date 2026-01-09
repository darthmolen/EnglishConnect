import { Play, Pause } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import type { QAPattern } from '@/types'

interface ExampleCard {
  patternNumber: number
  exampleIndex: number
  question: string
  questionTranslation?: string | null
  answer: string
  answerTranslation?: string | null
}

interface MobilePatternsViewProps {
  patterns: QAPattern[]
  playingId: string | null
  currentExampleId?: string | null
  onPlayExample: (patternNumber: number, exampleIndex: number) => void
}

export function MobilePatternsView({
  patterns,
  playingId,
  currentExampleId,
  onPlayExample,
}: MobilePatternsViewProps) {
  const { t } = useTranslation()

  // Flatten patterns into example cards
  const exampleCards: ExampleCard[] = []
  for (const pattern of patterns) {
    if (pattern.examples && pattern.examples.length > 0) {
      pattern.examples.forEach((ex, idx) => {
        if (ex.q && ex.a) {
          exampleCards.push({
            patternNumber: pattern.pattern_number,
            exampleIndex: idx + 1, // 1-indexed to match demo audio
            question: ex.q as string,
            questionTranslation: ex.q_translation as string | null,
            answer: ex.a as string,
            answerTranslation: ex.a_translation as string | null,
          })
        }
      })
    }
  }

  if (exampleCards.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        {t('mobile.patterns.empty', 'No pattern examples available')}
      </div>
    )
  }

  return (
    <div className="space-y-3 p-1">
      {exampleCards.map((card) => {
        const cardId = `${card.patternNumber}-${card.exampleIndex}`
        const isPlaying = playingId === cardId
        const isSelected = currentExampleId === cardId || isPlaying

        return (
          <button
            key={cardId}
            type="button"
            onClick={() => onPlayExample(card.patternNumber, card.exampleIndex)}
            className={cn(
              'w-full text-left p-4 rounded-xl border transition-all',
              'bg-card',
              'active:scale-[0.98]',
              isSelected && 'ring-2 ring-primary bg-primary/5 border-primary'
            )}
          >
            <div className="flex items-start gap-3">
              {/* Pattern number badge */}
              <span className={cn(
                'flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold',
                isPlaying ? 'bg-primary text-primary-foreground' : 'bg-primary/20'
              )}>
                P{card.patternNumber}
              </span>

              {/* Q&A content */}
              <div className="flex-1 min-w-0 space-y-1">
                <div>
                  <span className="text-xs text-muted-foreground">Q: </span>
                  <span className="font-medium">{card.question}</span>
                  {card.questionTranslation && (
                    <div className="text-sm text-muted-foreground italic ml-4">
                      ({card.questionTranslation})
                    </div>
                  )}
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">A: </span>
                  <span className="text-muted-foreground">{card.answer}</span>
                  {card.answerTranslation && (
                    <div className="text-sm text-muted-foreground/70 italic ml-4">
                      ({card.answerTranslation})
                    </div>
                  )}
                </div>
              </div>

              {/* Play indicator */}
              <span
                className={cn(
                  'flex items-center justify-center shrink-0',
                  'h-11 w-11 rounded-full',
                  isPlaying
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-primary/10 text-primary'
                )}
              >
                {isPlaying ? (
                  <Pause className="h-5 w-5" />
                ) : (
                  <Play className="h-5 w-5 ml-0.5" />
                )}
              </span>
            </div>
          </button>
        )
      })}
    </div>
  )
}
