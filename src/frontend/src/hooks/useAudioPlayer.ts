import { useState, useRef, useCallback } from 'react'

interface UseAudioPlayerReturn {
  isPlaying: boolean
  playAudio: (base64Audio: string, format?: string) => Promise<void>
  stopAudio: () => void
}

export function useAudioPlayer(): UseAudioPlayerReturn {
  const [isPlaying, setIsPlaying] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const playAudio = useCallback(
    async (base64Audio: string, format = 'wav') => {
      // Stop any existing playback
      if (audioRef.current) {
        audioRef.current.pause()
      }

      // Create audio element with data URL
      const dataUrl = `data:audio/${format};base64,${base64Audio}`
      const audio = new Audio(dataUrl)
      audioRef.current = audio

      // Handle playback end
      audio.onended = () => {
        setIsPlaying(false)
      }

      // Handle errors
      audio.onerror = () => {
        setIsPlaying(false)
        console.error('Audio playback error')
      }

      setIsPlaying(true)
      await audio.play()
    },
    []
  )

  const stopAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
    }
    setIsPlaying(false)
  }, [])

  return {
    isPlaying,
    playAudio,
    stopAudio,
  }
}
