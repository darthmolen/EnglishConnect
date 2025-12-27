import { useState } from 'react'
import { ChevronDown, ChevronRight, Check, Volume2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { LessonDetail, LessonPhase, PhaseState } from '@/types'

interface LessonMaterialPanelProps {
  lesson: LessonDetail
  currentPhase: LessonPhase | null
  phaseState: PhaseState | null
}

interface CollapsibleSectionProps {
  title: string
  defaultOpen?: boolean
  children: React.ReactNode
}

function CollapsibleSection({
  title,
  defaultOpen = true,
  children,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className="border-b last:border-b-0">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center gap-2 p-3 text-left font-medium hover:bg-accent/50 transition-colors"
      >
        {isOpen ? (
          <ChevronDown className="h-4 w-4 shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0" />
        )}
        {title}
      </button>
      {isOpen && <div className="px-3 pb-3">{children}</div>}
    </div>
  )
}

export function LessonMaterialPanel({
  lesson,
  currentPhase,
  phaseState,
}: LessonMaterialPanelProps) {
  const vocabIndex = phaseState?.vocab_index ?? 0
  const patternIndex = phaseState?.pattern_index ?? 0
  const isVocabPhase = currentPhase?.phase_type === 'vocabulary'
  const isPatternPhase = currentPhase?.phase_type === 'patterns'

  return (
    <div className="flex flex-col h-full">
      {/* Phase indicator */}
      {currentPhase && (
        <div className="border-b p-3 bg-primary/5">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-primary">
              {currentPhase.phase_name}
            </span>
            {phaseState && (isVocabPhase || isPatternPhase) && (
              <span className="text-xs text-muted-foreground">
                {isVocabPhase
                  ? `${vocabIndex + 1} of ${lesson.vocabulary.length}`
                  : `${patternIndex + 1} of ${lesson.patterns.length}`}
              </span>
            )}
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {/* Learning Principle */}
        {lesson.learning_principle_title && (
          <CollapsibleSection
            title={lesson.learning_principle_title}
            defaultOpen={false}
          >
            <p className="text-sm text-muted-foreground leading-relaxed">
              {lesson.learning_principle_content}
            </p>
          </CollapsibleSection>
        )}

        {/* Vocabulary */}
        <CollapsibleSection title="Vocabulary" defaultOpen={true}>
          <div className="space-y-3">
            {/* Group vocabulary by category */}
            {(() => {
              // Group items by category, maintaining original order for indexing
              const grouped = lesson.vocabulary.reduce(
                (acc, item, index) => {
                  const category = item.category || 'Other'
                  if (!acc[category]) {
                    acc[category] = []
                  }
                  acc[category].push({ item, index })
                  return acc
                },
                {} as Record<string, { item: typeof lesson.vocabulary[0]; index: number }[]>
              )

              // Define category display order
              const categoryOrder = [
                'pronoun', 'verb', 'noun', 'adjective', 'adverb',
                'preposition', 'phrase', 'question_word', 'time', 'day',
                'number', 'price', 'symbol', 'Other'
              ]

              // Sort categories
              const sortedCategories = Object.keys(grouped).sort((a, b) => {
                const aIndex = categoryOrder.indexOf(a)
                const bIndex = categoryOrder.indexOf(b)
                if (aIndex === -1 && bIndex === -1) return a.localeCompare(b)
                if (aIndex === -1) return 1
                if (bIndex === -1) return -1
                return aIndex - bIndex
              })

              // Format category name for display
              const formatCategory = (cat: string) => {
                if (cat === 'Other') return 'Other'
                // Capitalize and pluralize
                const formatted = cat.charAt(0).toUpperCase() + cat.slice(1)
                // Add 's' for plural unless already ends in 's'
                return formatted.endsWith('s') ? formatted : formatted + 's'
              }

              return sortedCategories.map((category) => (
                <div key={category}>
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1 pb-0.5 border-b border-muted-foreground/30">
                    {formatCategory(category)}
                  </h4>
                  <ul className="space-y-0.5 pl-1">
                    {grouped[category].map(({ item, index }) => {
                      const isCurrent = isVocabPhase && index === vocabIndex
                      const isCompleted =
                        phaseState?.items_completed?.includes(`vocab_${index}`) ?? false

                      return (
                        <li
                          key={index}
                          className={cn(
                            'flex items-center gap-2 rounded-md px-2 py-1 text-sm transition-colors',
                            isCurrent && 'bg-primary/20 border-l-4 border-primary',
                            isCompleted && !isCurrent && 'text-muted-foreground'
                          )}
                        >
                          <span className="text-primary shrink-0">•</span>
                          {isCompleted && (
                            <Check className="h-3 w-3 text-green-600 shrink-0" />
                          )}
                          <span className="font-medium">{item.english}</span>
                          <span className="text-muted-foreground">—</span>
                          <span className="text-muted-foreground">{item.spanish}</span>
                          {isCurrent && (
                            <Volume2 className="h-3 w-3 ml-auto text-primary shrink-0" />
                          )}
                        </li>
                      )
                    })}
                  </ul>
                </div>
              ))
            })()}
          </div>
        </CollapsibleSection>

        {/* Q&A Patterns */}
        <CollapsibleSection title="Patterns" defaultOpen={true}>
          <div className="space-y-3">
            {lesson.patterns.map((pattern, index) => {
              const isCurrent = isPatternPhase && index === patternIndex
              const isCompleted =
                phaseState?.items_completed?.includes(`pattern_${index}`) ??
                false

              return (
                <div
                  key={pattern.pattern_number}
                  className={cn(
                    'rounded-md p-2 text-sm transition-colors',
                    isCurrent && 'bg-primary/20 border-l-4 border-primary',
                    isCompleted && !isCurrent && 'text-muted-foreground'
                  )}
                >
                  <div className="flex items-start gap-2">
                    {isCompleted && (
                      <Check className="h-3 w-3 text-green-600 shrink-0 mt-0.5" />
                    )}
                    <div className="flex-1">
                      <p className="font-medium">
                        Q: {pattern.question_template}
                      </p>
                      <p className="text-muted-foreground">
                        A: {pattern.answer_template}
                      </p>
                      {pattern.examples && pattern.examples.length > 0 && (
                        <div className="mt-1 pl-2 border-l-2 border-muted text-xs">
                          {pattern.examples.slice(0, 2).map((ex, i) => (
                            <p key={i} className="text-muted-foreground">
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
        </CollapsibleSection>

        {/* Evaluation Criteria */}
        {lesson.evaluation_criteria.length > 0 && (
          <CollapsibleSection title="Learning Goals" defaultOpen={false}>
            <ul className="space-y-1">
              {lesson.evaluation_criteria.map((criterion, index) => (
                <li
                  key={index}
                  className="flex items-start gap-2 text-sm text-muted-foreground"
                >
                  <span className="text-primary">•</span>
                  {criterion}
                </li>
              ))}
            </ul>
          </CollapsibleSection>
        )}
      </div>
    </div>
  )
}
