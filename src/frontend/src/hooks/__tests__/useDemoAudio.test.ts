import { renderHook, act, waitFor } from '@testing-library/react'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { useDemoAudio } from '../useDemoAudio'

// Dispatch-based mock so we can fire 'ended' the way useDemoAudio listens for it.
class MockAudio {
  src = ''
  currentTime = 0
  play = vi.fn(() => Promise.resolve())
  pause = vi.fn()

  private listeners: Record<string, Array<(e: Event) => void>> = {}

  constructor() {
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

// Two examples in the same pattern, so a pattern loop leaves a non-empty queue.
const DEMOS = [
  { pattern_number: 1, example_index: 1, stream_url: '/audio/1-1.wav' },
  { pattern_number: 1, example_index: 2, stream_url: '/audio/1-2.wav' },
]

describe('useDemoAudio', () => {
  let originalAudio: typeof global.Audio
  let originalFetch: typeof global.fetch

  beforeEach(() => {
    vi.clearAllMocks()
    mockAudioInstance = null
    originalAudio = global.Audio
    originalFetch = global.fetch
    global.Audio = MockAudio as unknown as typeof Audio
    global.fetch = vi.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve(DEMOS) } as Response)
    )
  })

  afterEach(() => {
    global.Audio = originalAudio
    global.fetch = originalFetch
    mockAudioInstance = null
  })

  it('stop() cancels an active pattern loop and clears its queue', async () => {
    const { result } = renderHook(() => useDemoAudio(1, 'ec1'))
    await waitFor(() => expect(result.current.demos).toHaveLength(2))

    await act(async () => { result.current.playPatternLoop(1) })
    expect(result.current.loopingPattern).toBe(1)

    await act(async () => { result.current.stop() })

    // stop() means stop: the loop state resets so the Practice UI isn't left
    // showing a pattern as "looping" while nothing is playing.
    expect(result.current.loopingPattern).toBeNull()

    // The queued next example must be gone too -- an 'ended' event should not
    // resurrect playback from a stale queue.
    const playsBeforeEnded = mockAudioInstance!.play.mock.calls.length
    await act(async () => { mockAudioInstance!.dispatchEvent(new Event('ended')) })
    expect(mockAudioInstance!.play.mock.calls.length).toBe(playsBeforeEnded)
  })
})
