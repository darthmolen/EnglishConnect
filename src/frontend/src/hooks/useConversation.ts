import { useCallback } from 'react'
import { useConversationStore } from '@/stores/conversationStore'
import { useAudioRecorder } from './useAudioRecorder'
import { useAudioPlayer } from './useAudioPlayer'
import { sendMessage } from '@/services/api'

export function useConversation() {
  const {
    messages,
    selectedLessonNumber,
    isLoading,
    addMessage,
    setIsLoading,
    setIsRecording: setStoreIsRecording,
    setIsPlaying: setStoreIsPlaying,
  } = useConversationStore()

  const {
    isRecording,
    audioBlob,
    startRecording,
    stopRecording,
  } = useAudioRecorder()
  const { isPlaying, playAudio } = useAudioPlayer()

  // Toggle recording with error handling
  const toggleRecording = useCallback(async () => {
    if (isRecording) {
      stopRecording()
      setStoreIsRecording(false)
      console.log('Recording stopped')
    } else {
      try {
        console.log('Starting recording...')
        await startRecording()
        setStoreIsRecording(true)
        console.log('Recording started')
      } catch (error) {
        console.error('Failed to start recording:', error)
        setStoreIsRecording(false)
        // Could show a toast/alert here
      }
    }
  }, [isRecording, startRecording, stopRecording, setStoreIsRecording])

  // Send text message and get AI response (agent provides audio via speak tool)
  const sendTextMessage = useCallback(
    async (text: string) => {
      if (!selectedLessonNumber || !text.trim()) return

      // Add user message
      addMessage({ role: 'user', content: text })
      setIsLoading(true)

      try {
        // Get AI response (agent may include audio from speak() tool)
        const response = await sendMessage(text, selectedLessonNumber, messages)
        addMessage({ role: 'assistant', content: response.text })

        // Play agent-generated audio if available
        if (response.audio_base64) {
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
      setStoreIsPlaying,
      playAudio,
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
  }
}
