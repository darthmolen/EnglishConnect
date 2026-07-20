import { useState, useRef, useEffect, useCallback } from 'react'

export type LoopMode = 'off' | 'all'

/** Sections whose audio can be looped hands-free. */
export type LoopableSection = 'vocabulary' | 'patterns' | 'examples'

/**
 * How long to wait between clips so the learner can shadow -- repeat the clip
 * aloud before the next one starts. A single vocabulary word is quick; a full
 * Q&A sentence needs considerably longer.
 *
 * Keyed by section so adding a loopable section is a one-line change and
 * TypeScript flags a missing pause.
 */
export const SHADOW_PAUSE_MS: Record<LoopableSection, number> = {
  vocabulary: 1500,
  patterns: 4000,
  examples: 4000,
}

const NEXT_MODE: Record<LoopMode, LoopMode> = {
  off: 'all',
  all: 'off',
}

/**
 * Hands-free playback of a section's audio clips.
 *
 * Students practice on commutes and lunch breaks, where tapping each clip is
 * impractical. `cycleMode` toggles off -> all -> off: one tap loops the whole
 * section, the next tap stops it. Between clips the hook waits `pauseMs` so the
 * learner can shadow (repeat the clip aloud).
 *
 * Owns its own <audio> element, so callers must stop any other audio source
 * before starting a loop -- see MobileApp.
 */
export function useSectionLoop(clips: string[], pauseMs: number) {
  const [mode, setMode] = useState<LoopMode>('off')
  const [currentIndex, setCurrentIndex] = useState<number | null>(null)

  const audioRef = useRef<HTMLAudioElement | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // The 'ended' listener is registered once on mount, so it reads live values
  // through refs rather than closing over stale render state.
  const modeRef = useRef<LoopMode>('off')
  const indexRef = useRef<number | null>(null)
  const clipsRef = useRef(clips)
  const pauseMsRef = useRef(pauseMs)

  useEffect(() => {
    clipsRef.current = clips
    pauseMsRef.current = pauseMs
  })

  const clearPauseTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const halt = useCallback(() => {
    clearPauseTimer()
    audioRef.current?.pause()
    modeRef.current = 'off'
    indexRef.current = null
    setMode('off')
    setCurrentIndex(null)
  }, [clearPauseTimer])

  const playIndex = useCallback(
    (index: number) => {
      const audio = audioRef.current
      const list = clipsRef.current
      if (!audio || index < 0 || index >= list.length) return

      audio.src = list[index]
      audio.currentTime = 0
      indexRef.current = index
      setCurrentIndex(index)

      // Warm the next clip's cache entry while this one plays. Only useful
      // because /api/audio/stream sends Cache-Control: immutable -- otherwise
      // this would just download the file a second time.
      const next = list[index + 1]
      if (next) {
        void fetch(next).catch(() => {})
      }

      audio.play().catch(() => halt())
    },
    [halt]
  )

  const handleEnded = useCallback(() => {
    const list = clipsRef.current
    const index = indexRef.current
    if (modeRef.current === 'off' || index === null) return

    const isLast = index >= list.length - 1
    const nextIndex = isLast ? 0 : index + 1
    clearPauseTimer()
    timerRef.current = setTimeout(() => {
      timerRef.current = null
      if (modeRef.current === 'off') return
      playIndex(nextIndex)
    }, pauseMsRef.current)
  }, [halt, clearPauseTimer, playIndex])

  useEffect(() => {
    const audio = new Audio()
    audioRef.current = audio

    const onEnded = () => handleEnded()
    const onError = () => halt()
    audio.addEventListener('ended', onEnded)
    audio.addEventListener('error', onError)

    return () => {
      clearPauseTimer()
      audio.removeEventListener('ended', onEnded)
      audio.removeEventListener('error', onError)
      audio.pause()
      audioRef.current = null
    }
  }, [handleEnded, halt, clearPauseTimer])

  // Stop the loop when the clip list changes (section or lesson switch).
  // pauseMs is in the deps so a pending timer can never fire holding a stale
  // pause value. Today pauseMs only ever changes alongside clips, but relying
  // on that would make it a hidden invariant a future change could break.
  useEffect(() => {
    return () => halt()
  }, [clips, pauseMs, halt])

  const cycleMode = useCallback(() => {
    const next = NEXT_MODE[modeRef.current]

    if (next === 'off') {
      halt()
      return
    }
    if (clipsRef.current.length === 0) return

    modeRef.current = next
    setMode(next)

    // Cold start begins at the first clip. (indexRef is only non-null while a
    // loop is already running, in which case `next` is 'off' and we halted above.)
    if (indexRef.current === null) {
      playIndex(0)
    }
  }, [halt, playIndex])

  return { mode, currentIndex, cycleMode, stop: halt }
}
