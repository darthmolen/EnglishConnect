import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Play, Pause, RotateCcw, SkipForward, MessageCircle, LogIn } from 'lucide-react'
import { cn } from '@/lib/utils'
import { AuthenticatedImage } from '@/components/AuthenticatedImage'
import { useConversationStore } from '@/stores/conversationStore'
import { useAuthStore } from '@/stores/authStore'
import type { QAPattern } from '@/types'

interface DemoMetadata {
  pattern_number: number
  example_index: number
  stream_url: string
}

export interface PatternAction {
  type: 'questions' | 'practice'
  patternNumber: number
}

interface PatternsViewProps {
  patterns: QAPattern[]
  patternImages: string[]
  lessonNumber?: number
  onPatternAction?: (action: PatternAction) => void
}

export function PatternsView({
  patterns,
  patternImages,
  lessonNumber,
  onPatternAction,
}: PatternsViewProps) {
  const { t } = useTranslation()
  const { courseId, focusPattern, startPatternPractice, setAgentMode } = useConversationStore()
  const { isAuthenticated, login } = useAuthStore()
  const [demos, setDemos] = useState<DemoMetadata[]>([])
  const [playingId, setPlayingId] = useState<string | null>(null)
  // Track current example index per pattern (1-indexed to match example_index)
  const [currentExampleIndex, setCurrentExampleIndex] = useState<Record<number, number>>({})
  // Track which patterns have been played at least once (for Play vs Repeat label)
  const [playedPatterns, setPlayedPatterns] = useState<Set<number>>(new Set())
  const audioRef = useRef<HTMLAudioElement>(null)

  // Fetch demos for this lesson
  useEffect(() => {
    if (!lessonNumber) return

    fetch(`/api/audio/demos/${courseId}?lesson_number=${lessonNumber}`)
      .then(r => r.ok ? r.json() : [])
      .then(setDemos)
      .catch(() => setDemos([]))
  }, [lessonNumber, courseId])

  // Handle audio end
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const handleEnded = () => setPlayingId(null)
    audio.addEventListener('ended', handleEnded)
    return () => audio.removeEventListener('ended', handleEnded)
  }, [])

  const handlePlay = (demo: DemoMetadata) => {
    const audio = audioRef.current
    if (!audio) return

    const demoId = `${demo.pattern_number}-${demo.example_index}`

    if (playingId === demoId) {
      audio.pause()
      setPlayingId(null)
    } else {
      audio.src = demo.stream_url
      audio.play().catch(() => setPlayingId(null))
      setPlayingId(demoId)
    }
  }

  const findDemo = (patternNumber: number, exampleIndex: number) =>
    demos.find(d => d.pattern_number === patternNumber && d.example_index === exampleIndex)

  if (patterns.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <p>{t('patterns.empty')}</p>
      </div>
    )
  }

  return (
    <div className="p-2 space-y-3">
      {/* Pattern cards */}
      <div className="space-y-2">
        {patterns.map((pattern) => {
          const isFocused = focusPattern === pattern.pattern_number

          return (
            <div
              key={pattern.pattern_number}
              className={cn(
                'rounded-lg border p-3 transition-colors',
                isFocused && 'bg-primary/10 border-primary border-l-4'
              )}
            >
              <div className="flex items-stretch gap-4">
                {/* Content column */}
                <div className="flex-1 space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground bg-muted px-2 py-0.5 rounded inline-block">
                    {t('patterns.pattern', { number: pattern.pattern_number })}
                  </span>
                  <div className="space-y-2">
                    <div>
                      <p className="font-medium">
                        <span className="text-primary">Q:</span> {pattern.question_template}
                      </p>
                      {pattern.question_translation && (
                        <p className="text-sm text-muted-foreground/70 italic pl-6">
                          ({pattern.question_translation})
                        </p>
                      )}
                    </div>
                    <div>
                      <p className="text-muted-foreground">
                        <span className="text-primary">A:</span> {pattern.answer_template}
                      </p>
                      {pattern.answer_translation && (
                        <p className="text-sm text-muted-foreground/70 italic pl-6">
                          ({pattern.answer_translation})
                        </p>
                      )}
                    </div>
                  </div>
                  {/* Examples */}
                  {pattern.examples && pattern.examples.length > 0 && (
                    <div className="mt-3 pl-3 border-l-2 border-muted space-y-1.5">
                      <span className="text-xs font-medium text-muted-foreground uppercase">
                        {t('patterns.examples')}
                      </span>
                      {pattern.examples.slice(0, 3).map((ex, i) => {
                        const demo = findDemo(pattern.pattern_number, i + 1)
                        const demoId = `${pattern.pattern_number}-${i + 1}`
                        const isPlaying = playingId === demoId

                        return (
                          <div key={i} className="flex items-start gap-2">
                            {demo && (
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handlePlay(demo)
                                }}
                                className={cn(
                                  'flex items-center justify-center rounded-full p-1 transition-colors shrink-0 mt-0.5',
                                  isPlaying
                                    ? 'bg-primary text-primary-foreground'
                                    : 'bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground'
                                )}
                                aria-label={isPlaying ? 'Pause' : 'Play example'}
                              >
                                {isPlaying ? (
                                  <Pause className="h-3 w-3" />
                                ) : (
                                  <Play className="h-3 w-3 ml-0.5" />
                                )}
                              </button>
                            )}
                            <div className="space-y-0.5">
                              <p className="text-sm text-muted-foreground">
                                Q: {ex.q}
                              </p>
                              {ex.q_translation && (
                                <p className="text-xs text-muted-foreground/60 italic pl-4">
                                  ({ex.q_translation})
                                </p>
                              )}
                              <p className="text-sm text-muted-foreground">
                                A: {ex.a}
                              </p>
                              {ex.a_translation && (
                                <p className="text-xs text-muted-foreground/60 italic pl-4">
                                  ({ex.a_translation})
                                </p>
                              )}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
                {/* Button column - spans full height */}
                {(() => {
                  const patternDemos = demos.filter(d => d.pattern_number === pattern.pattern_number)
                  const hasDemos = patternDemos.length > 0
                  const currentIdx = currentExampleIndex[pattern.pattern_number] || 1
                  const currentDemo = patternDemos.find(d => d.example_index === currentIdx)
                  const hasNext = currentIdx < patternDemos.length
                  const isPlaying = playingId?.startsWith(`${pattern.pattern_number}-`)
                  const hasPlayed = playedPatterns.has(pattern.pattern_number)

                  const handleListenRepeat = () => {
                    if (!currentDemo) return
                    handlePlay(currentDemo)
                    // Mark this pattern as played
                    setPlayedPatterns(prev => new Set(prev).add(pattern.pattern_number))
                  }

                  const handleNext = () => {
                    if (!hasDemos) return
                    // Round-robin: wrap to first if at end
                    const nextIdx = hasNext ? currentIdx + 1 : 1
                    setCurrentExampleIndex(prev => ({ ...prev, [pattern.pattern_number]: nextIdx }))
                    const nextDemo = patternDemos.find(d => d.example_index === nextIdx)
                    if (nextDemo) handlePlay(nextDemo)
                    // Mark as played since we're playing audio
                    setPlayedPatterns(prev => new Set(prev).add(pattern.pattern_number))
                  }

                  const handleQuestions = () => {
                    if (!isAuthenticated) {
                      login()
                      return
                    }
                    setAgentMode('help')
                    onPatternAction?.({ type: 'questions', patternNumber: pattern.pattern_number })
                  }

                  return (
                    <div className="flex flex-col justify-center gap-2 shrink-0">
                      {/* Play / Repeat button */}
                      <button
                        type="button"
                        onClick={handleListenRepeat}
                        disabled={!hasDemos}
                        className={cn(
                          'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                          !hasDemos
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : isPlaying
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-gray-800 hover:bg-gray-900 text-white'
                        )}
                      >
                        {isPlaying ? (
                          <Pause className="h-3 w-3" />
                        ) : hasPlayed ? (
                          <RotateCcw className="h-3 w-3" />
                        ) : (
                          <Play className="h-3 w-3" />
                        )}
                        {hasPlayed ? t('demo.repeat') : t('patterns.listen')}
                      </button>

                      {/* Next button */}
                      <button
                        type="button"
                        onClick={handleNext}
                        disabled={!hasDemos}
                        className={cn(
                          'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                          !hasDemos
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : 'bg-muted hover:bg-muted/80 text-foreground'
                        )}
                      >
                        <SkipForward className="h-3 w-3" />
                        {t('demo.next')}
                      </button>

                      {/* Questions button - requires auth */}
                      <button
                        type="button"
                        onClick={handleQuestions}
                        disabled={!isAuthenticated}
                        className={cn(
                          'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                          !isAuthenticated
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : 'bg-purple-100 text-purple-700 hover:bg-purple-200 dark:bg-purple-900/30 dark:text-purple-300 dark:hover:bg-purple-900/50'
                        )}
                        title={!isAuthenticated ? t('auth.signInToChat') : undefined}
                      >
                        {!isAuthenticated ? (
                          <LogIn className="h-3 w-3" />
                        ) : (
                          <MessageCircle className="h-3 w-3" />
                        )}
                        {t('demo.questions')}
                      </button>

                      {/* Practice button - starts agent conversation (requires auth) */}
                      <button
                        type="button"
                        onClick={() => {
                          if (!isAuthenticated) {
                            login()
                            return
                          }
                          startPatternPractice(pattern.pattern_number)
                          onPatternAction?.({ type: 'practice', patternNumber: pattern.pattern_number })
                        }}
                        disabled={!isAuthenticated}
                        className={cn(
                          'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                          !isAuthenticated
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : isFocused
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-green-600 hover:bg-green-700 text-white'
                        )}
                        title={!isAuthenticated ? t('auth.signInToPractice') : undefined}
                      >
                        {!isAuthenticated ? (
                          <LogIn className="h-3 w-3" />
                        ) : (
                          <Play className="h-3 w-3" />
                        )}
                        {isFocused ? t('patterns.practicing') : t('patterns.practice')}
                      </button>
                    </div>
                  )
                })()}
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

      {/* Hidden audio element for playback */}
      <audio ref={audioRef} />
    </div>
  )
}
