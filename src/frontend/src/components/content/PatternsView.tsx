import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { AuthenticatedImage } from '@/components/AuthenticatedImage'
import type { QAPattern, PhaseState } from '@/types'

interface PatternsViewProps {
  patterns: QAPattern[]
  patternImages: string[]
  isPatternPhase?: boolean
  patternIndex?: number
  phaseState?: PhaseState | null
}

export function PatternsView({
  patterns,
  patternImages,
  isPatternPhase = false,
  patternIndex = 0,
  phaseState,
}: PatternsViewProps) {
  if (patterns.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <p>No patterns available for this lesson</p>
      </div>
    )
  }

  return (
    <div className="p-4 space-y-6">
      {/* Pattern cards */}
      <div className="space-y-4">
        {patterns.map((pattern, index) => {
          const isCurrent = isPatternPhase && index === patternIndex
          const isCompleted =
            phaseState?.items_completed?.includes(`pattern_${index}`) ?? false

          return (
            <div
              key={pattern.pattern_number}
              className={cn(
                'rounded-lg border p-4 transition-colors',
                isCurrent && 'bg-primary/10 border-primary border-l-4',
                isCompleted && !isCurrent && 'opacity-75'
              )}
            >
              <div className="flex items-start gap-3">
                {isCompleted && (
                  <Check className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                )}
                <div className="flex-1 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground bg-muted px-2 py-0.5 rounded">
                      Pattern {pattern.pattern_number}
                    </span>
                  </div>
                  <div className="space-y-1">
                    <p className="font-medium">
                      <span className="text-primary">Q:</span> {pattern.question_template}
                    </p>
                    <p className="text-muted-foreground">
                      <span className="text-primary">A:</span> {pattern.answer_template}
                    </p>
                  </div>
                  {/* Examples */}
                  {pattern.examples && pattern.examples.length > 0 && (
                    <div className="mt-3 pl-3 border-l-2 border-muted space-y-1">
                      <span className="text-xs font-medium text-muted-foreground uppercase">
                        Examples
                      </span>
                      {pattern.examples.slice(0, 3).map((ex, i) => (
                        <p key={i} className="text-sm text-muted-foreground">
                          {Object.values(ex)[0]}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Pattern diagram images */}
      {patternImages.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Pattern Diagrams
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {patternImages.map((imagePath, index) => (
              <div key={index} className="rounded-lg border overflow-hidden bg-white min-h-[100px]">
                <AuthenticatedImage
                  src={`/api/content/images/${imagePath}`}
                  alt={`Pattern diagram ${index + 1}`}
                  className="w-full h-auto object-contain"
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
