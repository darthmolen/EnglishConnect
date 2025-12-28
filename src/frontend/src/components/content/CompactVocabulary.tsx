import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { VocabularyItem } from '@/types'

interface CompactVocabularyProps {
  vocabulary: VocabularyItem[]
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

export function CompactVocabulary({ vocabulary }: CompactVocabularyProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())

  if (vocabulary.length === 0) {
    return null
  }

  // Group vocabulary by category
  const grouped = vocabulary.reduce(
    (acc, item) => {
      const category = item.category || 'Other'
      if (!acc[category]) {
        acc[category] = []
      }
      acc[category].push(item)
      return acc
    },
    {} as Record<string, VocabularyItem[]>
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

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev)
      if (next.has(category)) {
        next.delete(category)
      } else {
        next.add(category)
      }
      return next
    })
  }

  return (
    <div className="border-b bg-muted/30">
      {/* Category chips */}
      <div className="flex flex-wrap gap-2 p-3">
        {sortedCategories.map((category) => {
          const isExpanded = expandedCategories.has(category)
          const count = grouped[category].length

          return (
            <button
              key={category}
              type="button"
              onClick={() => toggleCategory(category)}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors',
                'border hover:bg-accent',
                isExpanded
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-background text-foreground border-border'
              )}
            >
              {isExpanded ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronRight className="h-3 w-3" />
              )}
              {formatCategory(category)}
              <span
                className={cn(
                  'rounded-full px-1.5 py-0.5 text-[10px]',
                  isExpanded
                    ? 'bg-primary-foreground/20 text-primary-foreground'
                    : 'bg-muted text-muted-foreground'
                )}
              >
                {count}
              </span>
            </button>
          )
        })}
      </div>

      {/* Expanded category content */}
      {sortedCategories
        .filter((cat) => expandedCategories.has(cat))
        .map((category) => (
          <div
            key={category}
            className="border-t px-3 py-2 bg-background"
          >
            <div className="flex flex-wrap gap-x-4 gap-y-1">
              {grouped[category].map((item, index) => (
                <span key={index} className="text-sm whitespace-nowrap">
                  <span className="font-medium">{item.english}</span>
                  <span className="text-muted-foreground"> — {item.spanish}</span>
                </span>
              ))}
            </div>
          </div>
        ))}
    </div>
  )
}
