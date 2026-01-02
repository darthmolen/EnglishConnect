import { useCallback, useEffect, useRef } from 'react'
import { useConversationStore } from '@/stores/conversationStore'
import { useAudioRecorder } from './useAudioRecorder'
import { useAudioPlayer } from './useAudioPlayer'
import { sendMessage, transcribeAudio } from '@/services/api'
import type { AgentResponse } from '@/types'

export function useConversation() {
  const {
    messages,
    selectedLessonNumber,
    isLoading,
    agentMode,
    exchangeCount,
    instructionLanguage,
    focusPattern,
    addMessage,
    clearMessages,
    setIsLoading,
    setIsRecording: setStoreIsRecording,
    setIsPlaying: setStoreIsPlaying,
    updatePhaseInfo,
    incrementExchangeCount,
  } = useConversationStore()

  const {
    isRecording,
    audioBlob,
    startRecording,
    stopRecording,
  } = useAudioRecorder()
  const { isPlaying, playAudio } = useAudioPlayer()

  // Track whether we should auto-send after recording stops
  const shouldSendVoiceRef = useRef(false)

  // Play audio chunks sequentially (for bilingual responses)
  const playAudioChunks = useCallback(
    async (response: AgentResponse) => {
      // Prefer audio_chunks if available (new format)
      if (response.audio_chunks && response.audio_chunks.length > 0) {
        console.log(`Playing ${response.audio_chunks.length} audio chunk(s)`)
        setStoreIsPlaying(true)
        try {
          for (const chunk of response.audio_chunks) {
            console.log(`Playing chunk: ${chunk.language} - "${chunk.text.substring(0, 50)}..."`)
            await playAudio(chunk.audio_base64, chunk.format || 'wav')
          }
        } catch (err) {
          console.error('Audio playback failed:', err)
        } finally {
          setStoreIsPlaying(false)
        }
      } else if (response.audio_base64) {
        // Fallback to single audio (backward compat)
        setStoreIsPlaying(true)
        try {
          await playAudio(response.audio_base64, response.audio_format || 'wav')
          console.log(`Agent spoke in ${response.language}`)
        } catch (err) {
          console.error('Audio playback failed:', err)
        } finally {
          setStoreIsPlaying(false)
        }
      }
    },
    [playAudio, setStoreIsPlaying]
  )

  // Send voice message (transcribe audio then send)
  const sendVoiceMessage = useCallback(
    async (blob: Blob) => {
      if (!selectedLessonNumber || !blob) return

      setIsLoading(true)
      console.log('Transcribing audio...')

      try {
        // Step 1: Transcribe audio
        const sttResponse = await transcribeAudio(blob)
        const transcribedText = sttResponse.text.trim()
        console.log('Transcribed:', transcribedText)

        if (!transcribedText) {
          console.log('No speech detected')
          setIsLoading(false)
          return
        }

        // Step 2: Add user message with transcribed text
        addMessage({ role: 'user', content: transcribedText, agentMode })

        // Step 3: Get AI response (unified agent with mode)
        const response = await sendMessage(
          transcribedText,
          selectedLessonNumber,
          messages,
          agentMode,
          exchangeCount,
          instructionLanguage,
          focusPattern
        )
        addMessage({
          role: 'assistant',
          content: response.text,
          agentMode,
          richContent: response.rich_content,
        })

        // Increment exchange count for flip detection in practice mode
        incrementExchangeCount()

        // Update phase info if returned (backward compat)
        if (response.phase) {
          updatePhaseInfo(response.phase, response.phase_state ?? null, response.phase_progress ?? null)
        }

        // Step 4: Play all audio chunks sequentially
        await playAudioChunks(response)
      } catch (error) {
        console.error('Voice message error:', error)
        addMessage({
          role: 'assistant',
          content: 'Sorry, I had trouble understanding. Please try again.',
          agentMode,
        })
      } finally {
        setIsLoading(false)
      }
    },
    [
      selectedLessonNumber,
      messages,
      agentMode,
      exchangeCount,
      instructionLanguage,
      focusPattern,
      addMessage,
      setIsLoading,
      playAudioChunks,
      updatePhaseInfo,
      incrementExchangeCount,
    ]
  )

  // Auto-send voice message when audioBlob becomes available after recording
  useEffect(() => {
    if (audioBlob && shouldSendVoiceRef.current && !isRecording) {
      shouldSendVoiceRef.current = false
      sendVoiceMessage(audioBlob)
    }
  }, [audioBlob, isRecording, sendVoiceMessage])

  // Toggle recording - auto-sends when stopped
  const toggleRecording = useCallback(async () => {
    if (isRecording) {
      console.log('Stopping recording...')
      shouldSendVoiceRef.current = true // Flag to auto-send when blob is ready
      stopRecording()
      setStoreIsRecording(false)
      console.log('Recording stopped, will transcribe...')
    } else {
      try {
        console.log('Starting recording...')
        shouldSendVoiceRef.current = false
        await startRecording()
        setStoreIsRecording(true)
        console.log('Recording started')
      } catch (error) {
        console.error('Failed to start recording:', error)
        setStoreIsRecording(false)
      }
    }
  }, [isRecording, startRecording, stopRecording, setStoreIsRecording])

  // Send text message and get AI response (agent provides audio via speak tool)
  const sendTextMessage = useCallback(
    async (text: string) => {
      if (!selectedLessonNumber || !text.trim()) return

      // Add user message
      addMessage({ role: 'user', content: text, agentMode })
      setIsLoading(true)

      try {
        // Get AI response (unified agent with mode)
        const response = await sendMessage(
          text,
          selectedLessonNumber,
          messages,
          agentMode,
          exchangeCount,
          instructionLanguage,
          focusPattern
        )
        addMessage({
          role: 'assistant',
          content: response.text,
          agentMode,
          richContent: response.rich_content,
        })

        // Increment exchange count for flip detection in practice mode
        incrementExchangeCount()

        // Update phase info if returned (backward compat)
        if (response.phase) {
          updatePhaseInfo(response.phase, response.phase_state ?? null, response.phase_progress ?? null)
        }

        // Play all audio chunks sequentially
        await playAudioChunks(response)
      } catch (error) {
        console.error('Conversation error:', error)
        addMessage({
          role: 'assistant',
          content: 'Sorry, I had trouble understanding. Please try again.',
          agentMode,
        })
      } finally {
        setIsLoading(false)
      }
    },
    [
      selectedLessonNumber,
      messages,
      agentMode,
      exchangeCount,
      instructionLanguage,
      focusPattern,
      addMessage,
      setIsLoading,
      playAudioChunks,
      updatePhaseInfo,
      incrementExchangeCount,
    ]
  )

  return {
    messages,
    isRecording,
    isPlaying,
    isLoading,
    audioBlob,
    toggleRecording,
    sendTextMessage,
    sendVoiceMessage,
    clearMessages,
  }
}
