import { useState, useRef, useCallback } from 'react'
import { logTotalLatency } from '@/utils/timing'

interface UseAudioPlayerReturn {
  isPlaying: boolean
  playAudio: (base64Audio: string, format?: string) => Promise<void>
  stopAudio: () => void
}

export function useAudioPlayer(): UseAudioPlayerReturn {
  const [isPlaying, setIsPlaying] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const playAudio = useCallback(
    async (base64Audio: string, format = 'wav'): Promise<void> => {
      // Stop any existing playback
      if (audioRef.current) {
        audioRef.current.pause()
      }

      // Create audio element with data URL
      const dataUrl = `data:audio/${format};base64,${base64Audio}`
      const audio = new Audio(dataUrl)
      audioRef.current = audio

      setIsPlaying(true)

      // Return promise that resolves when audio FINISHES playing
      return new Promise((resolve, reject) => {
        audio.onended = () => {
          setIsPlaying(false)
          resolve()
        }

        audio.onerror = (e) => {
          setIsPlaying(false)
          console.error('Audio playback error:', e)
          reject(new Error('Audio playback failed'))
        }

        audio
          .play()
          .then(() => {
            // T11: Audio playback starts
            logTotalLatency('T11', 'audio_playback_start')
          })
          .catch((err) => {
            setIsPlaying(false)
            reject(err)
          })
      })
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
