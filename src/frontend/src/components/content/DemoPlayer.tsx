import { useState, useRef, useEffect } from 'react'
import { Play, Pause, Volume2, RotateCcw, SkipForward, MessageCircle, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useConversationStore } from '@/stores/conversationStore'

interface DemoMetadata {
  lesson_number: number
  pattern_number: number
  example_index: number
  dialogue: Array<{ role: string; text: string }>
  stream_url: string
  duration_seconds: number
}

interface DemoPlayerProps {
  courseId: string
  lessonNumber: number
}

export function DemoPlayer({ courseId, lessonNumber }: DemoPlayerProps) {
  const { setAgentMode } = useConversationStore()
  const [demos, setDemos] = useState<DemoMetadata[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [showControls, setShowControls] = useState(false)  // Show controls after demo ends
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // Fetch demos for this lesson
  useEffect(() => {
    async function fetchDemos() {
      try {
        setIsLoading(true)
        const response = await fetch(
          `/api/audio/demos/${courseId}?lesson_number=${lessonNumber}`
        )
        if (!response.ok) {
          throw new Error('Failed to fetch demos')
        }
        const data = await response.json()
        setDemos(data)
      } catch {
        setDemos([])
      } finally {
        setIsLoading(false)
      }
    }
    fetchDemos()
  }, [courseId, lessonNumber])

  // Handle audio end - show controls
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const handleEnded = () => {
      setIsPlaying(false)
      setShowControls(true)
    }

    audio.addEventListener('ended', handleEnded)
    return () => audio.removeEventListener('ended', handleEnded)
  }, [])

  // Play current demo when index changes
  useEffect(() => {
    if (isPlaying && demos[currentIndex]) {
      const audio = audioRef.current
      if (audio) {
        audio.src = demos[currentIndex].stream_url
        audio.play().catch(() => setIsPlaying(false))
      }
    }
  }, [currentIndex, isPlaying, demos])

  const handlePlayPause = () => {
    const audio = audioRef.current
    if (!audio || demos.length === 0) return

    if (isPlaying) {
      audio.pause()
      setIsPlaying(false)
    } else {
      audio.src = demos[currentIndex].stream_url
      audio.play().catch(() => setIsPlaying(false))
      setIsPlaying(true)
      setShowControls(false)  // Hide controls while playing
    }
  }

  const handleRepeat = () => {
    const audio = audioRef.current
    if (!audio || demos.length === 0) return
    audio.src = demos[currentIndex].stream_url
    audio.play().catch(() => setIsPlaying(false))
    setIsPlaying(true)
    setShowControls(false)
  }

  const handleNext = () => {
    if (currentIndex < demos.length - 1) {
      setCurrentIndex(prev => prev + 1)
      const audio = audioRef.current
      if (audio) {
        audio.src = demos[currentIndex + 1].stream_url
        audio.play().catch(() => setIsPlaying(false))
        setIsPlaying(true)
        setShowControls(false)
      }
    } else {
      // All demos done, just hide controls
      setShowControls(false)
    }
  }

  const handleQuestions = () => {
    setAgentMode('demo')
    setShowControls(false)
    // TODO: Could also open conversation drawer or focus input
  }

  const handleFinished = () => {
    setAgentMode('conversation')  // Always return to conversation partner
    setShowControls(false)
    setCurrentIndex(0)
  }

  // Don't render if no demos available
  if (!isLoading && demos.length === 0) {
    return null
  }

  const totalDuration = demos.reduce((sum, d) => sum + d.duration_seconds, 0)
  const formattedDuration = totalDuration > 0
    ? `${Math.floor(totalDuration / 60)}:${String(Math.floor(totalDuration % 60)).padStart(2, '0')}`
    : ''

  return (
    <div className="border-b bg-muted/30">
      <div className="flex items-center gap-3 p-3">
        {/* Play button */}
        <button
          type="button"
          onClick={handlePlayPause}
          disabled={isLoading || demos.length === 0}
          className={cn(
            'flex items-center justify-center rounded-full p-2.5 transition-colors',
            'bg-primary text-primary-foreground hover:bg-primary/90',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
          aria-label={isPlaying ? 'Pause demo' : 'Play demo'}
        >
          {isPlaying ? (
            <Pause className="h-4 w-4" />
          ) : (
            <Play className="h-4 w-4 ml-0.5" />
          )}
        </button>

        {/* Label and info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Volume2 className="h-4 w-4 text-muted-foreground flex-shrink-0" />
            <span className="text-sm font-medium truncate">
              Hear the conversation patterns
            </span>
          </div>
          <span className="text-xs text-muted-foreground">
            Escucha a las conversaciones en inglés
          </span>
        </div>

        {/* Demo count and duration */}
        {!isLoading && demos.length > 0 && (
          <div className="text-xs text-muted-foreground text-right flex-shrink-0">
            <div>{demos.length} example{demos.length !== 1 ? 's' : ''}</div>
            {formattedDuration && <div>{formattedDuration}</div>}
          </div>
        )}

        {/* Progress indicator when playing */}
        {isPlaying && (
          <div className="text-xs text-primary font-medium flex-shrink-0">
            {currentIndex + 1}/{demos.length}
          </div>
        )}
      </div>

      {/* Control buttons - shown after demo ends */}
      {showControls && (
        <div className="flex items-center gap-2 px-3 pb-3 pt-1">
          <button
            type="button"
            onClick={handleRepeat}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium',
              'bg-muted hover:bg-muted/80 transition-colors'
            )}
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Repeat
          </button>

          {currentIndex < demos.length - 1 && (
            <button
              type="button"
              onClick={handleNext}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium',
                'bg-muted hover:bg-muted/80 transition-colors'
              )}
            >
              <SkipForward className="h-3.5 w-3.5" />
              Next
            </button>
          )}

          <button
            type="button"
            onClick={handleQuestions}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium',
              'bg-purple-100 text-purple-700 hover:bg-purple-200 transition-colors',
              'dark:bg-purple-900/30 dark:text-purple-300 dark:hover:bg-purple-900/50'
            )}
          >
            <MessageCircle className="h-3.5 w-3.5" />
            Questions
          </button>

          <button
            type="button"
            onClick={handleFinished}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium',
              'bg-green-100 text-green-700 hover:bg-green-200 transition-colors',
              'dark:bg-green-900/30 dark:text-green-300 dark:hover:bg-green-900/50'
            )}
          >
            <Check className="h-3.5 w-3.5" />
            Finished
          </button>
        </div>
      )}

      {/* Hidden audio element */}
      <audio ref={audioRef} />
    </div>
  )
}
