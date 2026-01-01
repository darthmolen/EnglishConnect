import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Play, Pause } from 'lucide-react'
import { cn } from '@/lib/utils'
import { AuthenticatedImage } from '@/components/AuthenticatedImage'
import { useConversationStore } from '@/stores/conversationStore'
import type { QAPattern } from '@/types'

interface DemoMetadata {
  pattern_number: number
  example_index: number
  stream_url: string
}

interface PatternsViewProps {
  patterns: QAPattern[]
  patternImages: string[]
  lessonNumber?: number
}

export function PatternsView({
  patterns,
  patternImages,
  lessonNumber,
}: PatternsViewProps) {
  const { t } = useTranslation()
  const { focusPattern, startPatternPractice } = useConversationStore()
  const [demos, setDemos] = useState<DemoMetadata[]>([])
  const [playingId, setPlayingId] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement>(null)

  // Fetch demos for this lesson
  useEffect(() => {
    if (!lessonNumber) return

    fetch(`/api/audio/demos/ec1?lesson_number=${lessonNumber}`)
      .then(r => r.ok ? r.json() : [])
      .then(setDemos)
      .catch(() => setDemos([]))
  }, [lessonNumber])

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
    <div className="p-4 space-y-6">
      {/* Pattern cards */}
      <div className="space-y-4">
        {patterns.map((pattern) => {
          const isFocused = focusPattern === pattern.pattern_number

          return (
            <div
              key={pattern.pattern_number}
              className={cn(
                'rounded-lg border p-4 transition-colors',
                isFocused && 'bg-primary/10 border-primary border-l-4'
              )}
            >
              <div className="flex items-start gap-3">
                <div className="flex-1 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground bg-muted px-2 py-0.5 rounded">
                      {t('patterns.pattern', { number: pattern.pattern_number })}
                    </span>
                    <button
                      type="button"
                      onClick={() => startPatternPractice(pattern.pattern_number)}
                      className={cn(
                        'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                        isFocused
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-green-600 hover:bg-green-700 text-white'
                      )}
                    >
                      <Play className="h-3 w-3" />
                      {isFocused ? t('patterns.practicing') : t('patterns.practice')}
                    </button>
                  </div>
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
