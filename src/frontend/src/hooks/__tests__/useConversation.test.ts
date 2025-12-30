import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useConversation } from '../useConversation'
import { useConversationStore } from '@/stores/conversationStore'
import * as api from '@/services/api'

// Mock the API module
vi.mock('@/services/api', () => ({
  sendMessage: vi.fn(),
  transcribeAudio: vi.fn(),
}))

// Mock useAudioRecorder
vi.mock('../useAudioRecorder', () => ({
  useAudioRecorder: () => ({
    isRecording: false,
    audioBlob: null,
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
  }),
}))

// Mock useAudioPlayer
vi.mock('../useAudioPlayer', () => ({
  useAudioPlayer: () => ({
    isPlaying: false,
    playAudio: vi.fn(),
    stopAudio: vi.fn(),
  }),
}))

describe('useConversation error handling', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset the store to initial state
    useConversationStore.setState({
      messages: [],
      selectedLessonNumber: 1,
      isLoading: false,
      agentMode: 'lesson', // Set to lesson mode (teacher)
      activeSection: 'vocabulary',
    })
  })

  it('should include agentMode in error messages when sendTextMessage fails', async () => {
    // Mock sendMessage to reject with an error
    vi.mocked(api.sendMessage).mockRejectedValue(new Error('500 Internal Server Error'))

    const { result } = renderHook(() => useConversation())

    // Trigger a text message that will fail
    await act(async () => {
      await result.current.sendTextMessage('test message')
    })

    // Wait for state updates
    await waitFor(() => {
      const messages = useConversationStore.getState().messages
      expect(messages.length).toBeGreaterThan(0)
    })

    // Get the error message (should be the assistant message)
    const messages = useConversationStore.getState().messages
    const errorMessage = messages.find(
      (m) => m.role === 'assistant' && m.content.includes('trouble understanding')
    )

    // Verify error message exists and has correct agentMode
    expect(errorMessage).toBeDefined()
    expect(errorMessage?.agentMode).toBe('lesson')
    expect(errorMessage?.content).toContain('Sorry, I had trouble understanding')
  })

  it('should preserve conversation mode agentMode in error messages', async () => {
    // Set store to conversation mode (partner)
    useConversationStore.setState({
      agentMode: 'conversation',
      selectedLessonNumber: 1,
    })

    // Mock sendMessage to reject with an error
    vi.mocked(api.sendMessage).mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useConversation())

    // Trigger a text message that will fail
    await act(async () => {
      await result.current.sendTextMessage('test message')
    })

    // Wait for state updates
    await waitFor(() => {
      const messages = useConversationStore.getState().messages
      expect(messages.length).toBeGreaterThan(0)
    })

    // Get the error message
    const messages = useConversationStore.getState().messages
    const errorMessage = messages.find(
      (m) => m.role === 'assistant' && m.content.includes('trouble understanding')
    )

    // Verify error message has conversation agentMode
    expect(errorMessage).toBeDefined()
    expect(errorMessage?.agentMode).toBe('conversation')
  })

  it('should include agentMode in error messages when voice message fails', async () => {
    // Set store to lesson mode
    useConversationStore.setState({
      agentMode: 'lesson',
      selectedLessonNumber: 1,
    })

    // Mock transcribeAudio to succeed
    vi.mocked(api.transcribeAudio).mockResolvedValue({ text: 'transcribed text' })

    // Mock sendMessage to fail
    vi.mocked(api.sendMessage).mockRejectedValue(new Error('Server error'))

    const { result } = renderHook(() => useConversation())

    // Create a mock audio blob
    const mockBlob = new Blob(['audio data'], { type: 'audio/webm' })

    // Trigger a voice message that will fail after transcription
    await act(async () => {
      await result.current.sendVoiceMessage(mockBlob)
    })

    // Wait for state updates
    await waitFor(() => {
      const messages = useConversationStore.getState().messages
      // Should have user message and error message
      expect(messages.length).toBeGreaterThanOrEqual(1)
    })

    // Get the error message
    const messages = useConversationStore.getState().messages
    const errorMessage = messages.find(
      (m) => m.role === 'assistant' && m.content.includes('trouble understanding')
    )

    // Verify error message has lesson agentMode
    expect(errorMessage).toBeDefined()
    expect(errorMessage?.agentMode).toBe('lesson')
  })
})
