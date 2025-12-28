import { Volume2, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { VocabularyItem, PhaseState } from '@/types'

interface VocabularyViewProps {
  vocabulary: VocabularyItem[]
  isVocabPhase?: boolean
  vocabIndex?: number
  phaseState?: PhaseState | null
}

// Category display order
const CATEGORY_ORDER = [
  'pronoun', 'verb', 'noun', 'adjective', 'adverb',
  'preposition', 'phrase', 'question_word', 'time', 'day',
  'number', 'price', 'symbol', 'Other'
]

function formatCategory(cat: string): string {
  if (cat === 'Other') return 'Other'
  const formatted = cat.charAt(0).toUpperCase() + cat.slice(1)
  return formatted.endsWith('s') ? formatted : formatted + 's'
}

export function VocabularyView({
  vocabulary,
  isVocabPhase = false,
  vocabIndex = 0,
  phaseState,
}: VocabularyViewProps) {
  if (vocabulary.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <p>No vocabulary available for this lesson</p>
      </div>
    )
  }

  // Group vocabulary by category
  const grouped = vocabulary.reduce(
    (acc, item, index) => {
      const category = item.category || 'Other'
      if (!acc[category]) {
        acc[category] = []
      }
      acc[category].push({ item, index })
      return acc
    },
    {} as Record<string, { item: VocabularyItem; index: number }[]>
  )

  // Sort categories
  const sortedCategories = Object.keys(grouped).sort((a, b) => {
    const aIndex = CATEGORY_ORDER.indexOf(a)
    const bIndex = CATEGORY_ORDER.indexOf(b)
    if (aIndex === -1 && bIndex === -1) return a.localeCompare(b)
    if (aIndex === -1) return 1
    if (bIndex === -1) return -1
    return aIndex - bIndex
  })

  return (
    <div className="p-4">
      {/* Flex-wrap layout for categories */}
      <div className="flex flex-wrap gap-4">
        {sortedCategories.map((category) => (
          <div
            key={category}
            className="min-w-[200px] max-w-[300px] flex-1 rounded-lg border bg-card p-3"
          >
            <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2 pb-1 border-b">
              {formatCategory(category)}
            </h4>
            <ul className="space-y-1">
              {grouped[category].map(({ item, index }) => {
                const isCurrent = isVocabPhase && index === vocabIndex
                const isCompleted =
                  phaseState?.items_completed?.includes(`vocab_${index}`) ?? false

                return (
                  <li
                    key={index}
                    className={cn(
                      'flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                      isCurrent && 'bg-primary/20 border-l-4 border-primary -ml-0.5',
                      isCompleted && !isCurrent && 'text-muted-foreground'
                    )}
                  >
                    {isCompleted && (
                      <Check className="h-3 w-3 text-green-600 shrink-0" />
                    )}
                    <span className="font-medium">{item.english}</span>
                    <span className="text-muted-foreground">—</span>
                    <span className="text-muted-foreground text-xs">{item.spanish}</span>
                    {isCurrent && (
                      <Volume2 className="h-3 w-3 ml-auto text-primary shrink-0" />
                    )}
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </div>
    </div>
  )
}
