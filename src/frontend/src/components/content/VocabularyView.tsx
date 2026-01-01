import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Play, Pause, HelpCircle, SkipForward } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useConversationStore } from '@/stores/conversationStore'
import type { VocabularyItem } from '@/types'

interface VocabAudioMetadata {
  english_word: string
  spanish_translation: string
  category: string | null
  stream_url: string
}

interface VocabularyViewProps {
  vocabulary: VocabularyItem[]
  lessonNumber?: number
  courseId?: string
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
  courseId = 'ec1',
}: VocabularyViewProps) {
  const { t } = useTranslation()
  const { introPlayedKeys, markIntroPlayed, instructionLanguage } = useConversationStore()
  const [vocabAudio, setVocabAudio] = useState<VocabAudioMetadata[]>([])
  const [playingWord, setPlayingWord] = useState<string | null>(null)
  const [introUrl, setIntroUrl] = useState<string | null>(null)
  const [isPlayingIntro, setIsPlayingIntro] = useState(false)
  const audioRef = useRef<HTMLAudioElement>(null)
  const introAudioRef = useRef<HTMLAudioElement>(null)

  // Check if intro has been played for this lesson (per language, per page type)
  const introKey = lessonNumber ? `vocab-${lessonNumber}-${instructionLanguage}` : null
  const hasIntroPlayed = introKey ? introPlayedKeys.includes(introKey) : true

  // Fetch intro URL when lesson or language changes
  useEffect(() => {
    if (!lessonNumber) {
      setIntroUrl(null)
      return
    }

    fetch(`/api/audio/intros/${courseId}?lesson_number=${lessonNumber}&language=${instructionLanguage}&page_type=vocabulary`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.stream_url) {
          setIntroUrl(data.stream_url)
        } else {
          setIntroUrl(null)
        }
      })
      .catch(() => setIntroUrl(null))
  }, [lessonNumber, courseId, instructionLanguage])

  // Auto-play intro when entering vocabulary section (if not already played)
  useEffect(() => {
    if (!introUrl || hasIntroPlayed || !lessonNumber) return

    const audio = introAudioRef.current
    if (!audio) return

    // Set source and play
    audio.src = introUrl
    audio.play()
      .then(() => {
        setIsPlayingIntro(true)
      })
      .catch(() => {
        // User may not have interacted with page yet, skip auto-play
        setIsPlayingIntro(false)
      })
  }, [introUrl, hasIntroPlayed, lessonNumber])

  // Handle intro audio end
  useEffect(() => {
    const audio = introAudioRef.current
    if (!audio) return

    const handleEnded = () => {
      setIsPlayingIntro(false)
      if (introKey) {
        markIntroPlayed(introKey)
      }
    }

    audio.addEventListener('ended', handleEnded)
    return () => audio.removeEventListener('ended', handleEnded)
  }, [introKey, markIntroPlayed])

  const handleSkipIntro = () => {
    const audio = introAudioRef.current
    if (audio) {
      audio.pause()
      audio.currentTime = 0
    }
    setIsPlayingIntro(false)
    if (introKey) {
      markIntroPlayed(introKey)
    }
  }

  // Fetch vocab audio for this lesson
  useEffect(() => {
    if (!lessonNumber) return

    fetch(`/api/audio/vocab/${courseId}?lesson_number=${lessonNumber}`)
      .then(r => r.ok ? r.json() : [])
      .then(setVocabAudio)
      .catch(() => setVocabAudio([]))
  }, [lessonNumber, courseId])

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
    <div className="flex flex-col h-full">
      {/* Hidden audio element for intro playback */}
      <audio ref={introAudioRef} />

      {/* Intro playing banner */}
      {isPlayingIntro && (
        <div className="px-4 py-2 border-b bg-primary/10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-primary animate-pulse" />
            <span className="text-sm font-medium">{t('vocabulary.playingIntro', 'Playing intro...')}</span>
          </div>
          <button
            type="button"
            onClick={handleSkipIntro}
            className={cn(
              'flex items-center gap-1 rounded px-2 py-1 text-xs',
              'bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground',
              'transition-colors'
            )}
          >
            <SkipForward className="h-3 w-3" />
            <span>{t('practice.skip', 'Skip')}</span>
          </button>
        </div>
      )}

      <div className="p-4 flex-1 overflow-y-auto">
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
                const audioMeta = findAudio(item.english)
                const isPlaying = playingWord === item.english

                return (
                  <li
                    key={index}
                    className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm"
                  >
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
    </div>
  )
}
