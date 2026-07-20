import { useState, useRef, useEffect, useCallback } from 'react'

interface DemoMetadata {
  pattern_number: number
  example_index: number
  stream_url: string
}

export function useDemoAudio(lessonNumber: number | undefined, courseId = 'ec1') {
  const [demos, setDemos] = useState<DemoMetadata[]>([])
  const [playingId, setPlayingId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  // For sequential playback: track the pattern being looped and current example queue
  const [loopingPattern, setLoopingPattern] = useState<number | null>(null)
  const exampleQueueRef = useRef<DemoMetadata[]>([])
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // Handle audio ended - advance to next example if looping
  const handleAudioEnded = useCallback(() => {
    if (exampleQueueRef.current.length > 0) {
      // Play next example in queue
      const nextDemo = exampleQueueRef.current.shift()!
      const audio = audioRef.current
      if (audio) {
        audio.src = nextDemo.stream_url
        audio.play()
          .then(() => setPlayingId(`${nextDemo.pattern_number}-${nextDemo.example_index}`))
          .catch(() => {
            setPlayingId(null)
            setLoopingPattern(null)
          })
      }
    } else {
      // Queue empty, stop looping
      setPlayingId(null)
      setLoopingPattern(null)
    }
  }, [])

  // Create audio element on mount
  useEffect(() => {
    audioRef.current = new Audio()
    audioRef.current.addEventListener('ended', handleAudioEnded)
    audioRef.current.addEventListener('error', () => {
      setPlayingId(null)
      setLoopingPattern(null)
      exampleQueueRef.current = []
    })

    return () => {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
      }
    }
  }, [handleAudioEnded])

  // Fetch demo audio metadata when lesson changes
  useEffect(() => {
    if (!lessonNumber) {
      setDemos([])
      return
    }

    setIsLoading(true)
    fetch(`/api/audio/demos/${courseId}?lesson_number=${lessonNumber}`)
      .then(r => r.ok ? r.json() : [])
      .then(setDemos)
      .catch(() => setDemos([]))
      .finally(() => setIsLoading(false))
  }, [lessonNumber, courseId])

  // Get demos for a specific pattern
  const getDemosForPattern = useCallback(
    (patternNumber: number) => demos.filter(d => d.pattern_number === patternNumber),
    [demos]
  )

  // Play a specific demo (pattern + example index)
  const playDemo = useCallback((patternNumber: number, exampleIndex = 1) => {
    const audio = audioRef.current
    if (!audio) return

    const demo = demos.find(
      d => d.pattern_number === patternNumber && d.example_index === exampleIndex
    )
    if (!demo) {
      console.warn('No demo found for pattern:', patternNumber, 'example:', exampleIndex)
      return
    }

    const demoId = `${patternNumber}-${exampleIndex}`

    if (playingId === demoId) {
      // Toggle off
      audio.pause()
      setPlayingId(null)
    } else {
      // Play new demo
      audio.src = demo.stream_url
      audio.play()
        .then(() => setPlayingId(demoId))
        .catch(() => setPlayingId(null))
    }
  }, [demos, playingId])

  // Play first available demo for a pattern (single play)
  const playPattern = useCallback((patternNumber: number) => {
    const patternDemos = demos.filter(d => d.pattern_number === patternNumber)
    if (patternDemos.length > 0) {
      playDemo(patternNumber, patternDemos[0].example_index)
    } else {
      console.warn('No demos available for pattern:', patternNumber)
    }
  }, [demos, playDemo])

  // Play all examples for a pattern sequentially (loop mode)
  const playPatternLoop = useCallback((patternNumber: number) => {
    const audio = audioRef.current
    if (!audio) return

    const patternDemos = demos
      .filter(d => d.pattern_number === patternNumber)
      .sort((a, b) => a.example_index - b.example_index)

    if (patternDemos.length === 0) {
      console.warn('No demos available for pattern:', patternNumber)
      return
    }

    // If already looping this pattern, stop
    if (loopingPattern === patternNumber) {
      audio.pause()
      setPlayingId(null)
      setLoopingPattern(null)
      exampleQueueRef.current = []
      return
    }

    // Start looping: play first, queue the rest
    const [first, ...rest] = patternDemos
    exampleQueueRef.current = rest
    setLoopingPattern(patternNumber)

    audio.src = first.stream_url
    audio.play()
      .then(() => setPlayingId(`${first.pattern_number}-${first.example_index}`))
      .catch(() => {
        setPlayingId(null)
        setLoopingPattern(null)
        exampleQueueRef.current = []
      })
  }, [demos, loopingPattern])

  // Skip to next example in the queue
  const nextExample = useCallback(() => {
    const audio = audioRef.current
    if (!audio || !loopingPattern) return

    if (exampleQueueRef.current.length > 0) {
      // Skip current, play next
      const nextDemo = exampleQueueRef.current.shift()!
      audio.src = nextDemo.stream_url
      audio.play()
        .then(() => setPlayingId(`${nextDemo.pattern_number}-${nextDemo.example_index}`))
        .catch(() => {
          setPlayingId(null)
          setLoopingPattern(null)
        })
    } else {
      // No more examples, stop
      audio.pause()
      setPlayingId(null)
      setLoopingPattern(null)
    }
  }, [loopingPattern])

  // Check if a specific pattern/example is playing
  const isPatternPlaying = useCallback(
    (patternNumber: number) => playingId?.startsWith(`${patternNumber}-`) ?? false,
    [playingId]
  )

  // Fully halt: pause, and cancel any active pattern loop so callers that stop
  // demo audio (e.g. starting a section loop) don't leave loopingPattern and a
  // queued example stranded.
  const stop = useCallback(() => {
    audioRef.current?.pause()
    setPlayingId(null)
    setLoopingPattern(null)
    exampleQueueRef.current = []
  }, [])

  return {
    demos,
    playingId,
    isLoading,
    loopingPattern,
    playDemo,
    playPattern,
    playPatternLoop,
    nextExample,
    getDemosForPattern,
    isPatternPlaying,
    stop,
    hasAudio: demos.length > 0,
  }
}
