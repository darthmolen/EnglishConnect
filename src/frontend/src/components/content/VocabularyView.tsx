import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Volume2, Check, Play, Pause, HelpCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { VocabularyItem, PhaseState } from '@/types'

interface VocabAudioMetadata {
  english_word: string
  spanish_translation: string
  category: string | null
  stream_url: string
}

interface VocabularyViewProps {
  vocabulary: VocabularyItem[]
  lessonNumber?: number
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
  lessonNumber,
  isVocabPhase = false,
  vocabIndex = 0,
  phaseState,
}: VocabularyViewProps) {
  const { t } = useTranslation()
  const [vocabAudio, setVocabAudio] = useState<VocabAudioMetadata[]>([])
  const [playingWord, setPlayingWord] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement>(null)

  // Fetch vocab audio for this lesson
  useEffect(() => {
    if (!lessonNumber) return

    fetch(`/api/audio/vocab/ec1?lesson_number=${lessonNumber}`)
      .then(r => r.ok ? r.json() : [])
      .then(setVocabAudio)
      .catch(() => setVocabAudio([]))
  }, [lessonNumber])

  // Handle audio end
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const handleEnded = () => setPlayingWord(null)
    audio.addEventListener('ended', handleEnded)
    return () => audio.removeEventListener('ended', handleEnded)
  }, [])

  const handlePlay = (meta: VocabAudioMetadata) => {
    const audio = audioRef.current
    if (!audio) return

    if (playingWord === meta.english_word) {
      audio.pause()
      setPlayingWord(null)
    } else {
      audio.src = meta.stream_url
      audio.play().catch(() => setPlayingWord(null))
      setPlayingWord(meta.english_word)
    }
  }

  const findAudio = (englishWord: string) =>
    vocabAudio.find(v => v.english_word === englishWord)

  if (vocabulary.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <p>{t('vocabulary.empty')}</p>
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
      {/* Summary banner */}
      <div className="mb-4 rounded-lg border bg-blue-50 dark:bg-blue-950/30 p-4">
        <div className="flex items-start gap-3">
          <HelpCircle className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
              {t('vocabulary.summaryTitle')}
            </h3>
            <p className="text-sm text-blue-800 dark:text-blue-200">
              {t('vocabulary.summary')}
            </p>
          </div>
        </div>
      </div>

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
                const audioMeta = findAudio(item.english)
                const isPlaying = playingWord === item.english

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
                    {audioMeta && (
                      <button
                        type="button"
                        onClick={() => handlePlay(audioMeta)}
                        className={cn(
                          'flex items-center justify-center rounded-full p-1 transition-colors shrink-0',
                          isPlaying
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground'
                        )}
                        aria-label={isPlaying ? 'Pause' : 'Play pronunciation'}
                      >
                        {isPlaying ? (
                          <Pause className="h-3 w-3" />
                        ) : (
                          <Play className="h-3 w-3 ml-0.5" />
                        )}
                      </button>
                    )}
                    <span className="font-medium">{item.english}</span>
                    <span className="text-muted-foreground">—</span>
                    <span className="text-muted-foreground text-xs">{item.spanish}</span>
                    {isCurrent && !audioMeta && (
                      <Volume2 className="h-3 w-3 ml-auto text-primary shrink-0" />
                    )}
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </div>

      {/* Hidden audio element for playback */}
      <audio ref={audioRef} />
    </div>
  )
}
