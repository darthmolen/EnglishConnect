import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Play, SkipForward, MessageSquare, LogIn } from 'lucide-react'
import { CompactVocabulary } from './CompactVocabulary'
import { PatternsView } from './PatternsView'
import { useConversationStore } from '@/stores/conversationStore'
import { useAuthStore } from '@/stores/authStore'
import { cn } from '@/lib/utils'
import type { VocabularyItem, QAPattern } from '@/types'

interface PracticeViewProps {
  vocabulary: VocabularyItem[]
  patterns: QAPattern[]
  patternImages: string[]
  courseId?: string
  lessonNumber?: number
  onStartConversation?: () => void
}

export function PracticeView({
  vocabulary,
  patterns,
  patternImages,
  courseId = 'ec1',
  lessonNumber,
  onStartConversation,
}: PracticeViewProps) {
  const { t } = useTranslation()
  const { introPlayedKeys, markIntroPlayed, instructionLanguage } = useConversationStore()
  const { isAuthenticated, login } = useAuthStore()
  const [introUrl, setIntroUrl] = useState<string | null>(null)
  const [isPlayingIntro, setIsPlayingIntro] = useState(false)
  const audioRef = useRef<HTMLAudioElement>(null)

  const hasVocabulary = vocabulary.length > 0
  const hasPatterns = patterns.length > 0

  // Check if intro has been played for this lesson (per language)
  const introKey = lessonNumber ? `${lessonNumber}-${instructionLanguage}` : null
  const hasIntroPlayed = introKey ? introPlayedKeys.includes(introKey) : true

  // Fetch intro URL when lesson or language changes
  useEffect(() => {
    if (!lessonNumber) {
      setIntroUrl(null)
      return
    }

    fetch(`/api/audio/intros/${courseId}?lesson_number=${lessonNumber}&language=${instructionLanguage}&page_type=practice`)
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

  // Auto-play intro when entering practice section (if not already played)
  useEffect(() => {
    if (!introUrl || hasIntroPlayed || !lessonNumber) return

    const audio = audioRef.current
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
    const audio = audioRef.current
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
    const audio = audioRef.current
    if (audio) {
      audio.pause()
      audio.currentTime = 0
    }
    setIsPlayingIntro(false)
    if (introKey) {
      markIntroPlayed(introKey)
    }
  }

  if (!hasVocabulary && !hasPatterns) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <p>{t('practice.empty')}</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Hidden audio element for intro playback */}
      <audio ref={audioRef} />

      {/* Intro playing banner */}
      {isPlayingIntro && (
        <div className="px-4 py-2 border-b bg-primary/10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-primary animate-pulse" />
            <span className="text-sm font-medium">{t('practice.playingIntro')}</span>
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
            <span>{t('practice.skip')}</span>
          </button>
        </div>
      )}

      {/* Summary banner */}
      <div className="mx-4 mt-4 mb-2 rounded-lg border bg-green-50 dark:bg-green-950/30 p-4">
        <div className="flex items-start gap-3">
          <MessageSquare className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-green-900 dark:text-green-100 mb-1">
              {t('practice.summaryTitle')}
            </h3>
            <p className="text-sm text-green-800 dark:text-green-200">
              {t('practice.summary')}
            </p>
          </div>
        </div>
      </div>

      {/* Compact vocabulary bar at top */}
      {hasVocabulary && (
        <CompactVocabulary vocabulary={vocabulary} />
      )}

      {/* Start Conversation Button */}
      {onStartConversation && (
        <div className="px-4 py-3 border-b bg-muted/30">
          <button
            type="button"
            onClick={isAuthenticated ? onStartConversation : login}
            className={cn(
              'w-full flex items-center justify-center gap-2 rounded-lg px-4 py-3',
              'text-white font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2',
              isAuthenticated
                ? 'bg-green-600 hover:bg-green-700 focus:ring-green-500'
                : 'bg-gray-500 hover:bg-gray-600 focus:ring-gray-400'
            )}
          >
            {isAuthenticated ? (
              <>
                <Play className="h-5 w-5" />
                <span>{t('practice.startConversation')}</span>
              </>
            ) : (
              <>
                <LogIn className="h-5 w-5" />
                <span>{t('auth.signInToPractice')}</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* Patterns section fills remaining space */}
      {hasPatterns && (
        <div className="flex-1 overflow-y-auto">
          <PatternsView
            patterns={patterns}
            patternImages={patternImages}
            lessonNumber={lessonNumber}
          />
        </div>
      )}
    </div>
  )
}
