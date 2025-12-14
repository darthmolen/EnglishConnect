import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useAudioPlayer } from '../useAudioPlayer'

// Mock Audio element
let mockAudioInstance: {
  play: ReturnType<typeof vi.fn>
  pause: ReturnType<typeof vi.fn>
  src: string
  onended: (() => void) | null
  onerror: ((e: Event) => void) | null
}

class MockAudio {
  src = ''
  onended: (() => void) | null = null
  onerror: ((e: Event) => void) | null = null

  constructor(url?: string) {
    if (url) {
      this.src = url
    }
    mockAudioInstance = this as typeof mockAudioInstance
  }

  play = vi.fn(() => Promise.resolve())
  pause = vi.fn()
}

beforeEach(() => {
  vi.clearAllMocks()
  global.Audio = MockAudio as unknown as typeof Audio
})

describe('useAudioPlayer', () => {
  it('initializes with isPlaying false', () => {
    const { result } = renderHook(() => useAudioPlayer())
    expect(result.current.isPlaying).toBe(false)
  })

  it('sets isPlaying to true when playAudio is called', async () => {
    const { result } = renderHook(() => useAudioPlayer())
    const base64Audio = btoa('test audio')

    await act(async () => {
      await result.current.playAudio(base64Audio)
    })

    expect(result.current.isPlaying).toBe(true)
  })

  it('creates audio element with data URL', async () => {
    const { result } = renderHook(() => useAudioPlayer())
    const base64Audio = btoa('test audio')

    await act(async () => {
      await result.current.playAudio(base64Audio)
    })

    expect(mockAudioInstance.src).toContain('data:audio/wav;base64,')
  })

  it('sets isPlaying to false when audio ends', async () => {
    const { result } = renderHook(() => useAudioPlayer())
    const base64Audio = btoa('test audio')

    await act(async () => {
      await result.current.playAudio(base64Audio)
    })

    // Simulate audio ended
    act(() => {
      if (mockAudioInstance.onended) {
        mockAudioInstance.onended()
      }
    })

    expect(result.current.isPlaying).toBe(false)
  })

  it('stops playback when stopAudio is called', async () => {
    const { result } = renderHook(() => useAudioPlayer())
    const base64Audio = btoa('test audio')

    await act(async () => {
      await result.current.playAudio(base64Audio)
    })

    act(() => {
      result.current.stopAudio()
    })

    expect(result.current.isPlaying).toBe(false)
    expect(mockAudioInstance.pause).toHaveBeenCalled()
  })
})
