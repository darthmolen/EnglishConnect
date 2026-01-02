import { useState, useRef, useEffect } from 'react'
import { Play, Pause, Volume2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { VocabularyCardData } from '@/types'

interface InlineVocabularyCardProps {
  data: VocabularyCardData
}

function formatCategory(cat: string): string {
  if (cat === 'Other' || cat === 'word') return ''
  const formatted = cat.charAt(0).toUpperCase() + cat.slice(1)
  return formatted
}

export function InlineVocabularyCard({ data }: InlineVocabularyCardProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const audioRef = useRef<HTMLAudioElement>(null)

  // Handle audio end
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const handleEnded = () => setIsPlaying(false)
    const handleError = () => setIsPlaying(false)

    audio.addEventListener('ended', handleEnded)
    audio.addEventListener('error', handleError)
    return () => {
      audio.removeEventListener('ended', handleEnded)
      audio.removeEventListener('error', handleError)
    }
  }, [])

  const handlePlayPause = () => {
    const audio = audioRef.current
    if (!audio || !data.audio_url) return

    if (isPlaying) {
      audio.pause()
      setIsPlaying(false)
    } else {
      audio.src = data.audio_url
      audio.play()
        .then(() => setIsPlaying(true))
        .catch(() => setIsPlaying(false))
    }
  }

  const category = formatCategory(data.category)

  return (
    <div className="mt-2 inline-flex items-center gap-3 rounded-lg border bg-card p-3 shadow-sm">
      {/* Play button */}
      {data.audio_url ? (
        <button
          type="button"
          onClick={handlePlayPause}
          className={cn(
            'flex items-center justify-center rounded-full p-2 transition-colors shrink-0',
            isPlaying
              ? 'bg-primary text-primary-foreground'
              : 'bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-800/40 text-blue-600 dark:text-blue-400'
          )}
          aria-label={isPlaying ? 'Pause' : 'Play pronunciation'}
        >
          {isPlaying ? (
            <Pause className="h-4 w-4" />
          ) : (
            <Play className="h-4 w-4 ml-0.5" />
          )}
        </button>
      ) : (
        <div className="flex items-center justify-center rounded-full p-2 bg-muted text-muted-foreground shrink-0">
          <Volume2 className="h-4 w-4" />
        </div>
      )}

      {/* Content */}
      <div className="flex flex-col">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-foreground">{data.english_word}</span>
          {category && (
            <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
              {category}
            </span>
          )}
        </div>
        <span className="text-sm text-muted-foreground">{data.spanish_translation}</span>
      </div>

      {/* Hidden audio element */}
      <audio ref={audioRef} />
    </div>
  )
}
