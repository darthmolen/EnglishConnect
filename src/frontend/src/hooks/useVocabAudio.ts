import { useState, useRef, useEffect, useCallback } from 'react'

interface VocabAudioMetadata {
  english_word: string
  spanish_translation: string
  category: string | null
  stream_url: string
}

export function useVocabAudio(lessonNumber: number | undefined, courseId = 'ec1') {
  const [vocabAudio, setVocabAudio] = useState<VocabAudioMetadata[]>([])
  const [playingWord, setPlayingWord] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // Create audio element on mount
  useEffect(() => {
    audioRef.current = new Audio()
    audioRef.current.addEventListener('ended', () => setPlayingWord(null))
    audioRef.current.addEventListener('error', () => setPlayingWord(null))

    return () => {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
      }
    }
  }, [])

  // Fetch vocab audio metadata when lesson changes
  useEffect(() => {
    if (!lessonNumber) {
      setVocabAudio([])
      return
    }

    setIsLoading(true)
    fetch(`/api/audio/vocab/${courseId}?lesson_number=${lessonNumber}`)
      .then(r => r.ok ? r.json() : [])
      .then(setVocabAudio)
      .catch(() => setVocabAudio([]))
      .finally(() => setIsLoading(false))
  }, [lessonNumber, courseId])

  const findAudioForWord = useCallback(
    (englishWord: string) => vocabAudio.find(v => v.english_word === englishWord),
    [vocabAudio]
  )

  const playWord = useCallback((englishWord: string) => {
    const audio = audioRef.current
    if (!audio) return

    const meta = vocabAudio.find(v => v.english_word === englishWord)
    if (!meta) {
      console.warn('No audio found for word:', englishWord)
      return
    }

    if (playingWord === englishWord) {
      // Toggle off
      audio.pause()
      setPlayingWord(null)
    } else {
      // Play new word
      audio.src = meta.stream_url
      audio.play()
        .then(() => setPlayingWord(englishWord))
        .catch(() => setPlayingWord(null))
    }
  }, [vocabAudio, playingWord])

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      setPlayingWord(null)
    }
  }, [])

  return {
    vocabAudio,
    playingWord,
    isLoading,
    playWord,
    stop,
    findAudioForWord,
    hasAudio: vocabAudio.length > 0,
  }
}
