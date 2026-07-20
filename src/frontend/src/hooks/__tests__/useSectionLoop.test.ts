import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { useSectionLoop, SHADOW_PAUSE_MS } from '../useSectionLoop'

// The MockAudio in useAudioPlayer.test.ts only supports the `onended` property
// style. useSectionLoop uses addEventListener (like useDemoAudio does), so it
// needs a mock that dispatches to registered listeners.
class MockAudio {
  src = ''
  currentTime = 0
  play = vi.fn(() => Promise.resolve())
  pause = vi.fn()

  private listeners: Record<string, Array<(e: Event) => void>> = {}

  constructor(url?: string) {
    if (url) this.src = url
    mockAudioInstance = this
  }

  addEventListener(type: string, fn: (e: Event) => void) {
    ;(this.listeners[type] ||= []).push(fn)
  }

  removeEventListener(type: string, fn: (e: Event) => void) {
    this.listeners[type] = (this.listeners[type] || []).filter(l => l !== fn)
  }

  dispatchEvent(event: Event) {
    for (const fn of this.listeners[event.type] || []) fn(event)
    return true
  }
}

let mockAudioInstance: MockAudio | null = null

const CLIPS = ['/api/audio/stream/a.wav', '/api/audio/stream/b.wav', '/api/audio/stream/c.wav']

/** Fire 'ended' on the current clip and run the shadowing pause to completion. */
async function finishClip(pauseMs: number) {
  await act(async () => {
    mockAudioInstance!.dispatchEvent(new Event('ended'))
  })
  await act(async () => {
    vi.advanceTimersByTime(pauseMs)
  })
}

describe('useSectionLoop', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    mockAudioInstance = null
    global.Audio = MockAudio as unknown as typeof Audio
    global.fetch = vi.fn(() => Promise.resolve({ ok: true } as Response))
  })

  afterEach(() => {
    vi.useRealTimers()
    mockAudioInstance = null
  })

  describe('mode toggling', () => {
    it('starts off', () => {
      const { result } = renderHook(() => useSectionLoop(CLIPS, 1000))
      expect(result.current.mode).toBe('off')
      expect(result.current.currentIndex).toBeNull()
    })

    // There is no intermediate "once" state anymore: one tap starts looping
    // everything, the next tap stops it.
    it('toggles off -> all -> off', async () => {
      const { result } = renderHook(() => useSectionLoop(CLIPS, 1000))

      await act(async () => { result.current.cycleMode() })
      expect(result.current.mode).toBe('all')

      await act(async () => { result.current.cycleMode() })
      expect(result.current.mode).toBe('off')
    })
  })

  describe('all mode', () => {
    it('starts at the first clip and advances on ended', async () => {
      const { result } = renderHook(() => useSectionLoop(CLIPS, 1000))

      await act(async () => { result.current.cycleMode() })
      expect(mockAudioInstance!.src).toBe(CLIPS[0])

      await finishClip(1000)
      expect(mockAudioInstance!.src).toBe(CLIPS[1])

      await finishClip(1000)
      expect(mockAudioInstance!.src).toBe(CLIPS[2])
    })

    it('wraps from the last clip back to the first and keeps going', async () => {
      const { result } = renderHook(() => useSectionLoop(CLIPS, 1000))

      await act(async () => { result.current.cycleMode() })
      expect(result.current.mode).toBe('all')
      expect(mockAudioInstance!.src).toBe(CLIPS[0])

      await finishClip(1000)
      await finishClip(1000)
      expect(mockAudioInstance!.src).toBe(CLIPS[2])

      await finishClip(1000)
      expect(mockAudioInstance!.src).toBe(CLIPS[0])
      expect(result.current.mode).toBe('all')
    })
  })

  describe('shadowing pause', () => {
    it('waits the full pause before the next clip (1000ms)', async () => {
      const { result } = renderHook(() => useSectionLoop(CLIPS, 1000))
      await act(async () => { result.current.cycleMode() })
      expect(mockAudioInstance!.play).toHaveBeenCalledTimes(1)

      await act(async () => { mockAudioInstance!.dispatchEvent(new Event('ended')) })
      await act(async () => { vi.advanceTimersByTime(999) })
      expect(mockAudioInstance!.play).toHaveBeenCalledTimes(1)

      await act(async () => { vi.advanceTimersByTime(1) })
      expect(mockAudioInstance!.play).toHaveBeenCalledTimes(2)
    })

    it('uses the pause it is given, not a hardcoded value (4000ms)', async () => {
      const { result } = renderHook(() => useSectionLoop(CLIPS, 4000))
      await act(async () => { result.current.cycleMode() })

      await act(async () => { mockAudioInstance!.dispatchEvent(new Event('ended')) })
      await act(async () => { vi.advanceTimersByTime(3999) })
      expect(mockAudioInstance!.play).toHaveBeenCalledTimes(1)

      await act(async () => { vi.advanceTimersByTime(1) })
      expect(mockAudioInstance!.play).toHaveBeenCalledTimes(2)
    })
  })

  describe('shadowing pause constants', () => {
    // Vocabulary clips are single words -- a short pause. Patterns and examples
    // are full Q&A sentences and need longer to shadow, but not as long as they
    // once did.
    it('gives vocabulary a 1500ms pause', () => {
      expect(SHADOW_PAUSE_MS.vocabulary).toBe(1500)
    })

    it('gives patterns and examples a 4000ms pause', () => {
      expect(SHADOW_PAUSE_MS.patterns).toBe(4000)
      expect(SHADOW_PAUSE_MS.examples).toBe(4000)
    })
  })

  describe('prefetch', () => {
    it('warms the next clip while the current one plays', async () => {
      const { result } = renderHook(() => useSectionLoop(CLIPS, 1000))
      await act(async () => { result.current.cycleMode() })

      expect(global.fetch).toHaveBeenCalledWith(CLIPS[1])
    })

    it('does not prefetch past the end of the list', async () => {
      const { result } = renderHook(() => useSectionLoop(CLIPS, 1000))
      await act(async () => { result.current.cycleMode() })

      await finishClip(1000)
      await finishClip(1000)
      expect(mockAudioInstance!.src).toBe(CLIPS[2])

      expect(global.fetch).not.toHaveBeenCalledWith(undefined)
      expect(vi.mocked(global.fetch).mock.calls.flat()).not.toContain(undefined)
    })
  })

  describe('stopping', () => {
    it('pauses immediately and cancels a pending shadowing pause', async () => {
      const { result } = renderHook(() => useSectionLoop(CLIPS, 1000))
      await act(async () => { result.current.cycleMode() })

      await act(async () => { mockAudioInstance!.dispatchEvent(new Event('ended')) })
      // Mid-pause: toggle all -> off
      await act(async () => { result.current.cycleMode() })
      expect(result.current.mode).toBe('off')

      const playsAtStop = mockAudioInstance!.play.mock.calls.length
      await act(async () => { vi.advanceTimersByTime(5000) })
      expect(mockAudioInstance!.play).toHaveBeenCalledTimes(playsAtStop)
      expect(mockAudioInstance!.pause).toHaveBeenCalled()
    })

    it('stop() halts playback and resets to off', async () => {
      const { result } = renderHook(() => useSectionLoop(CLIPS, 1000))
      await act(async () => { result.current.cycleMode() })

      await act(async () => { result.current.stop() })
      expect(result.current.mode).toBe('off')
      expect(result.current.currentIndex).toBeNull()
      expect(mockAudioInstance!.pause).toHaveBeenCalled()
    })
  })

  describe('failure handling', () => {
    it('resets to off when play() rejects', async () => {
      // e.g. iOS NotAllowedError when playback is not user-gesture-initiated
      global.Audio = class extends MockAudio {
        play = vi.fn(() => Promise.reject(new Error('NotAllowedError')))
      } as unknown as typeof Audio

      const { result } = renderHook(() => useSectionLoop(CLIPS, 1000))
      await act(async () => { result.current.cycleMode() })

      // Guard against a vacuous pass: the hook must have *tried* to play and
      // then fallen back to off, not simply never started.
      expect(mockAudioInstance!.play).toHaveBeenCalled()
      expect(result.current.mode).toBe('off')
      expect(result.current.currentIndex).toBeNull()
    })

    it('resets to off on an audio error event', async () => {
      const { result } = renderHook(() => useSectionLoop(CLIPS, 1000))
      await act(async () => { result.current.cycleMode() })
      expect(result.current.mode).toBe('all')

      await act(async () => { mockAudioInstance!.dispatchEvent(new Event('error')) })
      expect(result.current.mode).toBe('off')
    })
  })

  describe('cleanup', () => {
    it('clears a pending pause timer on unmount', async () => {
      const { result, unmount } = renderHook(() => useSectionLoop(CLIPS, 1000))
      await act(async () => { result.current.cycleMode() })
      await act(async () => { mockAudioInstance!.dispatchEvent(new Event('ended')) })

      const playsBefore = mockAudioInstance!.play.mock.calls.length
      unmount()
      await act(async () => { vi.advanceTimersByTime(5000) })

      expect(mockAudioInstance!.play).toHaveBeenCalledTimes(playsBefore)
    })

    it('stops the loop when clips change (section or lesson switch)', async () => {
      const { result, rerender } = renderHook(
        ({ clips, pause }) => useSectionLoop(clips, pause),
        { initialProps: { clips: CLIPS, pause: 1000 } }
      )
      await act(async () => { result.current.cycleMode() })
      expect(result.current.mode).toBe('all')

      await act(async () => {
        rerender({ clips: ['/api/audio/stream/other.wav'], pause: 5000 })
      })

      expect(result.current.mode).toBe('off')
      expect(mockAudioInstance!.pause).toHaveBeenCalled()
    })
  })

  describe('edge cases', () => {
    it('does nothing when there are no clips', async () => {
      const { result } = renderHook(() => useSectionLoop([], 1000))

      await act(async () => { result.current.cycleMode() })

      expect(result.current.mode).toBe('off')
      expect(mockAudioInstance!.play).not.toHaveBeenCalled()
    })

    it('replays a single clip in all mode', async () => {
      const single = ['/api/audio/stream/only.wav']
      const { result } = renderHook(() => useSectionLoop(single, 1000))

      await act(async () => { result.current.cycleMode() })
      expect(result.current.mode).toBe('all')
      expect(mockAudioInstance!.src).toBe(single[0])

      // index 0 is both first and last, so it replays the same src forever
      const playsBefore = mockAudioInstance!.play.mock.calls.length
      await finishClip(1000)
      expect(mockAudioInstance!.play.mock.calls.length).toBeGreaterThan(playsBefore)
      expect(mockAudioInstance!.src).toBe(single[0])
      expect(result.current.mode).toBe('all')
    })
  })
})
