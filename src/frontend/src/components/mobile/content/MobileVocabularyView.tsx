import { Play, Pause } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import type { VocabularyItem } from '@/types'

interface MobileVocabularyViewProps {
  vocabulary: VocabularyItem[]
  currentIndex: number
  playingWord?: string | null
  onPlayWord: (index: number) => void
  onSelectWord: (index: number) => void
}

export function MobileVocabularyView({
  vocabulary,
  currentIndex,
  playingWord,
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
      {vocabulary.map((item, index) => {
        const isPlaying = playingWord === item.english
        return (
          <button
            key={`${item.english}-${index}`}
            type="button"
            onClick={() => onPlayWord(index)}
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
                <div className="text-lg font-medium">{item.english}</div>
                <div className="text-sm text-muted-foreground">{item.spanish}</div>
                {item.category && (
                  <div className="text-xs text-muted-foreground/70 mt-1">{item.category}</div>
                )}
              </div>
              <button
                type="button"
                aria-label={isPlaying ? `Stop ${item.english}` : `Play ${item.english}`}
                onClick={(e) => {
                  e.stopPropagation()
                  onPlayWord(index)
                }}
                className={cn(
                  'flex items-center justify-center',
                  'h-12 w-12 rounded-full', // Large touch target
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
          </button>
        )
      })}
    </div>
  )
}
