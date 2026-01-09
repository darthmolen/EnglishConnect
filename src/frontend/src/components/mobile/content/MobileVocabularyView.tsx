import { Play } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'

interface VocabularyItem {
  id: number
  word: string
  translation: string
  category?: string
}

interface MobileVocabularyViewProps {
  vocabulary: VocabularyItem[]
  currentIndex: number
  onPlayWord: (index: number) => void
  onSelectWord: (index: number) => void
}

export function MobileVocabularyView({
  vocabulary,
  currentIndex,
  onPlayWord,
  onSelectWord,
}: MobileVocabularyViewProps) {
  const { t } = useTranslation()

  if (vocabulary.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        {t('mobile.vocabulary.empty', 'No vocabulary available')}
      </div>
    )
  }

  return (
    <div className="space-y-3 p-1">
      {vocabulary.map((item, index) => (
        <button
          key={item.id}
          type="button"
          onClick={() => onSelectWord(index)}
          className={cn(
            'w-full text-left p-4 rounded-xl border transition-all',
            'min-h-[72px]', // Touch-friendly
            'active:scale-[0.98]',
            index === currentIndex
              ? 'ring-2 ring-primary bg-primary/5 border-primary'
              : 'bg-card hover:bg-accent/50'
          )}
        >
          <div className="flex items-center justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="text-lg font-medium">{item.word}</div>
              <div className="text-sm text-muted-foreground">{item.translation}</div>
              {item.category && (
                <div className="text-xs text-muted-foreground/70 mt-1">{item.category}</div>
              )}
            </div>
            <button
              type="button"
              aria-label={`Play ${item.word}`}
              onClick={(e) => {
                e.stopPropagation()
                onPlayWord(index)
              }}
              className={cn(
                'flex items-center justify-center',
                'h-12 w-12 rounded-full', // Large touch target
                'bg-primary/10 text-primary',
                'hover:bg-primary/20 active:bg-primary/30',
                'transition-colors'
              )}
            >
              <Play className="h-5 w-5 ml-0.5" />
            </button>
          </div>
        </button>
      ))}
    </div>
  )
}
