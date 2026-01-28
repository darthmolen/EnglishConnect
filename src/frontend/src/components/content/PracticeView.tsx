import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Play, Pause, SkipForward, MessageSquare, LogIn } from 'lucide-react'
import { CompactVocabulary } from './CompactVocabulary'
import { HelpingPhrasesPanel } from './HelpingPhrasesPanel'
import { PatternsView, type PatternAction } from './PatternsView'
import { useConversationStore } from '@/stores/conversationStore'
import { useAuthStore } from '@/stores/authStore'
import { fetchHelpingPhrases } from '@/services/api'
import { cn } from '@/lib/utils'
import type { VocabularyItem, QAPattern, HelpingPhrase } from '@/types'

interface IntroClip {
  type: 'unique' | 'instructions'
  stream_url: string
}

interface IntroResponse {
  lesson_number: number
  language: string
  page_type: string
  mode?: 'split' | 'legacy'
  clips?: IntroClip[]
  stream_url?: string
  pause_ms?: number
}

interface PracticeViewProps {
  vocabulary: VocabularyItem[]
  patterns: QAPattern[]
  patternImages: string[]
  courseId?: string
  lessonNumber?: number
  onStartConversation?: () => void
  onPatternAction?: (action: PatternAction) => void
}

export function PracticeView({
  vocabulary,
  patterns,
  patternImages,
  courseId = 'ec1',
  lessonNumber,
  onStartConversation,
  onPatternAction,
}: PracticeViewProps) {
  const { t } = useTranslation()
  const { introPlayedKeys, markIntroPlayed, instructionLanguage } = useConversationStore()
  const { isAuthenticated, login } = useAuthStore()
  const [introData, setIntroData] = useState<IntroResponse | null>(null)
  const [isPlayingIntro, setIsPlayingIntro] = useState(false)
  const [currentClipIndex, setCurrentClipIndex] = useState(0)
  const [helpingPhrases, setHelpingPhrases] = useState<HelpingPhrase[]>([])
  const audioRef = useRef<HTMLAudioElement>(null)

  const hasVocabulary = vocabulary.length > 0
  const hasPatterns = patterns.length > 0

  // Check if intro has been played for this lesson (per language)
  const introKey = lessonNumber ? `${lessonNumber}-${instructionLanguage}` : null
  const hasIntroPlayed = introKey ? introPlayedKeys.includes(introKey) : true

  // Fetch intro data when lesson or language changes
  useEffect(() => {
    if (!lessonNumber) {
      setIntroData(null)
      return
    }

    fetch(`/api/audio/intros/${courseId}?lesson_number=${lessonNumber}&language=${instructionLanguage}&page_type=practice`)
      .then(r => r.ok ? r.json() : null)
      .then((data: IntroResponse | null) => {
        if (data && (data.clips || data.stream_url)) {
          setIntroData(data)
          setCurrentClipIndex(0)
        } else {
          setIntroData(null)
        }
      })
      .catch(() => setIntroData(null))
  }, [lessonNumber, courseId, instructionLanguage])

  // Fetch helping phrases when instruction language changes
  useEffect(() => {
    fetchHelpingPhrases(instructionLanguage)
      .then(setHelpingPhrases)
      .catch(() => setHelpingPhrases([]))
  }, [instructionLanguage])

  // Helper to get the current clip URL
  const getCurrentClipUrl = (): string | null => {
    if (!introData) return null
    if (introData.mode === 'split' && introData.clips) {
      return introData.clips[currentClipIndex]?.stream_url || null
    }
    return introData.stream_url || null
  }

  // Manual play intro function (no longer auto-plays)
  const handlePlayIntro = () => {
    if (!introData || isPlayingIntro) return

    const audio = audioRef.current
    if (!audio) return

    const clipUrl = getCurrentClipUrl()
    if (!clipUrl) return

    // Set source and play
    audio.src = clipUrl
    audio.play()
      .then(() => {
        setIsPlayingIntro(true)
      })
      .catch(() => {
        // User interaction required but failed
        setIsPlayingIntro(false)
      })
  }

  // Auto-advance to next clip when current clip index changes (for split mode)
  useEffect(() => {
    if (!isPlayingIntro || currentClipIndex === 0) return

    const audio = audioRef.current
    if (!audio) return

    const clipUrl = getCurrentClipUrl()
    if (!clipUrl) return

    audio.src = clipUrl
    audio.play().catch(() => {
      setIsPlayingIntro(false)
      setCurrentClipIndex(0)
    })
  }, [currentClipIndex])

  // Handle intro audio end (with sequential playback for split mode)
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const handleEnded = () => {
      // Check if we're in split mode and have more clips to play
      if (introData?.mode === 'split' && introData.clips) {
        const nextIndex = currentClipIndex + 1
        if (nextIndex < introData.clips.length) {
          // Wait for the breath pause, then play next clip
          const pauseMs = introData.pause_ms || 300
          setTimeout(() => {
            setCurrentClipIndex(nextIndex)
          }, pauseMs)
          return
        }
      }

      // All clips played (or legacy mode) - mark intro as complete
      setIsPlayingIntro(false)
      setCurrentClipIndex(0)
      if (introKey) {
        markIntroPlayed(introKey)
      }
    }

    audio.addEventListener('ended', handleEnded)
    return () => audio.removeEventListener('ended', handleEnded)
  }, [introKey, markIntroPlayed, introData, currentClipIndex])

  const handleSkipIntro = () => {
    const audio = audioRef.current
    if (audio) {
      audio.pause()
      audio.currentTime = 0
    }
    setIsPlayingIntro(false)
    setCurrentClipIndex(0)
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

      {/* Summary banner - compact with play button */}
      <div className="mx-3 mt-2 mb-1 rounded-lg border bg-blue-50 dark:bg-blue-950/30 px-3 py-2">
        <div className="flex items-start gap-2">
          {introData && !hasIntroPlayed ? (
            <button
              type="button"
              onClick={handlePlayIntro}
              disabled={isPlayingIntro}
              className={cn(
                'flex items-center justify-center rounded-full p-1 transition-colors flex-shrink-0 mt-0.5',
                isPlayingIntro
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white'
              )}
              aria-label={isPlayingIntro ? 'Playing intro' : 'Play intro'}
            >
              {isPlayingIntro ? (
                <Pause className="h-3 w-3" />
              ) : (
                <Play className="h-3 w-3 ml-0.5" />
              )}
            </button>
          ) : (
            <MessageSquare className="h-4 w-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          )}
          <div>
            <h3 className="font-semibold text-sm text-blue-900 dark:text-blue-100">
              {t('practice.summaryTitle')}
            </h3>
            <p className="text-xs text-blue-800 dark:text-blue-200">
              {t('practice.summary')}
            </p>
          </div>
        </div>
      </div>

      {/* Compact vocabulary bar at top */}
      {hasVocabulary && (
        <CompactVocabulary vocabulary={vocabulary} />
      )}

      {/* Helping phrases panel */}
      {helpingPhrases.length > 0 && (
        <HelpingPhrasesPanel
          phrases={helpingPhrases}
          instructionLanguage={instructionLanguage}
          className="mx-3 mt-2"
        />
      )}

      {/* Start Conversation Button - compact */}
      {onStartConversation && (
        <div className="px-3 py-2 border-b bg-muted/30">
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
            onPatternAction={onPatternAction}
          />
        </div>
      )}
    </div>
  )
}
