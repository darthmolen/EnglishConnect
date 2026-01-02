import { useState, useRef, useEffect } from 'react'
import { Play, Pause, MessageSquare } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { PatternCardData } from '@/types'

interface InlinePatternCardProps {
  data: PatternCardData
}

export function InlinePatternCard({ data }: InlinePatternCardProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const audioRef = useRef<HTMLAudioElement>(null)

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const handleEnded = () => setIsPlaying(false)
    const handleError = () => {
      setIsPlaying(false)
      setIsLoading(false)
    }

    audio.addEventListener('ended', handleEnded)
    audio.addEventListener('error', handleError)
    return () => {
      audio.removeEventListener('ended', handleEnded)
      audio.removeEventListener('error', handleError)
    }
  }, [])

  const handlePlayPause = async () => {
    const audio = audioRef.current
    if (!audio || !data.demo_audio_url) return

    if (isPlaying) {
      audio.pause()
      setIsPlaying(false)
    } else {
      setIsLoading(true)
      try {
        // Fetch demo metadata and play
        const response = await fetch(data.demo_audio_url)
        const demos = await response.json()
        // Filter demos by pattern_number to get the correct pattern's demo
        const patternDemo = demos.find(
          (d: { pattern_number: number }) => d.pattern_number === data.pattern_number
        )
        if (patternDemo) {
          audio.src = patternDemo.stream_url
          await audio.play()
          setIsPlaying(true)
        }
      } catch {
        setIsPlaying(false)
      } finally {
        setIsLoading(false)
      }
    }
  }

  return (
    <div className="mt-2 rounded-lg border bg-card p-4 shadow-sm max-w-md">
      {/* Header with pattern badge */}
      <div className="flex items-center gap-2 mb-3">
        <MessageSquare className="h-4 w-4 text-muted-foreground" />
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Pattern {data.pattern_number} • Lesson {data.lesson_number}
        </span>
      </div>

      {/* Question template */}
      <div className="mb-2">
        <span className="text-xs text-muted-foreground block mb-0.5">Question:</span>
        <p className="font-medium text-foreground">{data.question_template}</p>
      </div>

      {/* Answer template */}
      <div className="mb-3">
        <span className="text-xs text-muted-foreground block mb-0.5">Answer:</span>
        <p className="text-foreground">{data.answer_template}</p>
      </div>

      {/* Play button for demo */}
      {data.demo_audio_url && (
        <button
          type="button"
          onClick={handlePlayPause}
          disabled={isLoading}
          className={cn(
            'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm transition-colors',
            isPlaying
              ? 'bg-primary text-primary-foreground'
              : 'bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-800/40 text-blue-600 dark:text-blue-400',
            isLoading && 'opacity-50 cursor-wait'
          )}
        >
          {isPlaying ? (
            <Pause className="h-3 w-3" />
          ) : (
            <Play className="h-3 w-3" />
          )}
          {isLoading ? 'Loading...' : isPlaying ? 'Playing...' : 'Play Example'}
        </button>
      )}

      <audio ref={audioRef} />
    </div>
  )
}
