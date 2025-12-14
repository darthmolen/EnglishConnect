import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useAudioRecorder } from '../useAudioRecorder'

// Mock MediaRecorder instance
let mockMediaRecorderInstance: {
  start: ReturnType<typeof vi.fn>
  stop: ReturnType<typeof vi.fn>
  ondataavailable: ((event: { data: Blob }) => void) | null
  onstop: (() => void) | null
  state: 'inactive' | 'recording'
}

const mockStream = {
  getTracks: () => [{ stop: vi.fn() }],
}

// Mock MediaRecorder class
class MockMediaRecorder {
  ondataavailable: ((event: { data: Blob }) => void) | null = null
  onstop: (() => void) | null = null
  state: 'inactive' | 'recording' = 'inactive'

  constructor() {
    mockMediaRecorderInstance = this as typeof mockMediaRecorderInstance
  }

  start = vi.fn(() => {
    this.state = 'recording'
  })

  stop = vi.fn(() => {
    this.state = 'inactive'
    if (this.onstop) this.onstop()
  })
}

beforeEach(() => {
  vi.clearAllMocks()

  // Mock navigator.mediaDevices
  Object.defineProperty(global.navigator, 'mediaDevices', {
    value: {
      getUserMedia: vi.fn().mockResolvedValue(mockStream),
    },
    writable: true,
    configurable: true,
  })

  // Mock MediaRecorder constructor
  global.MediaRecorder = MockMediaRecorder as unknown as typeof MediaRecorder
})

describe('useAudioRecorder', () => {
  it('initializes with isRecording false', () => {
    const { result } = renderHook(() => useAudioRecorder())
    expect(result.current.isRecording).toBe(false)
  })

  it('sets isRecording to true when startRecording is called', async () => {
    const { result } = renderHook(() => useAudioRecorder())

    await act(async () => {
      await result.current.startRecording()
    })

    expect(result.current.isRecording).toBe(true)
  })

  it('requests microphone permission on startRecording', async () => {
    const { result } = renderHook(() => useAudioRecorder())

    await act(async () => {
      await result.current.startRecording()
    })

    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({
      audio: true,
    })
  })

  it('sets isRecording to false when stopRecording is called', async () => {
    const { result } = renderHook(() => useAudioRecorder())

    await act(async () => {
      await result.current.startRecording()
    })

    act(() => {
      result.current.stopRecording()
    })

    expect(result.current.isRecording).toBe(false)
  })

  it('returns audio blob after stopping', async () => {
    const mockBlob = new Blob(['audio'], { type: 'audio/webm' })
    const { result } = renderHook(() => useAudioRecorder())

    await act(async () => {
      await result.current.startRecording()
    })

    // Simulate data available and stop
    act(() => {
      if (mockMediaRecorderInstance.ondataavailable) {
        mockMediaRecorderInstance.ondataavailable({ data: mockBlob })
      }
      result.current.stopRecording()
    })

    expect(result.current.audioBlob).toBeInstanceOf(Blob)
  })

  it('has null audioBlob initially', () => {
    const { result } = renderHook(() => useAudioRecorder())
    expect(result.current.audioBlob).toBeNull()
  })
})
