import { useCallback } from 'react'
import { useConversationStore } from '@/stores/conversationStore'
import { useAudioRecorder } from './useAudioRecorder'
import { useAudioPlayer } from './useAudioPlayer'
import { sendMessage, synthesizeSpeech } from '@/services/api'

export function useConversation() {
  const {
    messages,
    selectedLessonNumber,
    isLoading,
    addMessage,
    setIsLoading,
    setIsRecording,
    setIsPlaying,
  } = useConversationStore()

  const { isRecording, audioBlob, startRecording, stopRecording } =
    useAudioRecorder()
  const { isPlaying, playAudio, stopAudio } = useAudioPlayer()

  // Sync recording state to store
  const handleStartRecording = useCallback(async () => {
    setIsRecording(true)
    await startRecording()
  }, [startRecording, setIsRecording])

  const handleStopRecording = useCallback(async () => {
    stopRecording()
    setIsRecording(false)

    // For now, use a text input approach until STT is integrated
    // The audioBlob can be sent to STT service later
  }, [stopRecording, setIsRecording])

  // Send text message and get AI response with TTS
  const sendTextMessage = useCallback(
    async (text: string) => {
      if (!selectedLessonNumber || !text.trim()) return

      // Add user message
      addMessage({ role: 'user', content: text })
      setIsLoading(true)

      try {
        // Get AI response
        const response = await sendMessage(text, selectedLessonNumber, messages)
        addMessage({ role: 'assistant', content: response.text })

        // Synthesize and play TTS
        setIsPlaying(true)
        try {
          const ttsResponse = await synthesizeSpeech(response.text)
          if (ttsResponse.audio_base64) {
            await playAudio(ttsResponse.audio_base64, ttsResponse.format)
          }
        } catch {
          console.error('TTS failed, continuing without audio')
        } finally {
          setIsPlaying(false)
        }
      } catch (error) {
        console.error('Conversation error:', error)
        addMessage({
          role: 'assistant',
          content: 'Sorry, I had trouble understanding. Please try again.',
        })
      } finally {
        setIsLoading(false)
      }
    },
    [
      selectedLessonNumber,
      messages,
      addMessage,
      setIsLoading,
      setIsPlaying,
      playAudio,
    ]
  )

  // Toggle recording
  const toggleRecording = useCallback(async () => {
    if (isRecording) {
      await handleStopRecording()
    } else {
      await handleStartRecording()
    }
  }, [isRecording, handleStartRecording, handleStopRecording])

  return {
    messages,
    isRecording,
    isPlaying,
    isLoading,
    audioBlob,
    toggleRecording,
    sendTextMessage,
    stopAudio,
  }
}
