import { useCallback, useEffect, useRef, useState } from 'react'
import { useConversationStore } from '@/stores/conversationStore'
import { useAudioRecorder } from './useAudioRecorder'
import { useAudioPlayer } from './useAudioPlayer'
import { sendMessage, transcribeAudio, fetchConfig } from '@/services/api'
import type { AgentResponse, RichContent, RichContentType } from '@/types'

/**
 * Convert Float32Array to PCM16 Int16Array for WebSocket audio.
 */
function float32ToPcm16(float32: Float32Array): Int16Array {
  const pcm16 = new Int16Array(float32.length)
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]))
    pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff
  }
  return pcm16
}

/**
 * Convert ArrayBuffer to Base64 string.
 */
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}

/**
 * Convert Base64 string to ArrayBuffer.
 */
function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes.buffer
}

export function useConversation() {
  const {
    messages,
    selectedLessonNumber,
    isLoading,
    agentMode,
    exchangeCount,
    instructionLanguage,
    focusPattern,
    voiceMode,
    isRecording: storeIsRecording,
    addMessage,
    clearMessages,
    setIsLoading,
    setIsRecording: setStoreIsRecording,
    setIsPlaying: setStoreIsPlaying,
    setVoiceMode,
    updatePhaseInfo,
    incrementExchangeCount,
  } = useConversationStore()

  const {
    isRecording: audioRecorderIsRecording,
    audioBlob,
    startRecording,
    stopRecording,
  } = useAudioRecorder()

  // Unified recording state: true if either audio recorder or realtime (store) is recording
  const isRecording = audioRecorderIsRecording || storeIsRecording
  const { isPlaying, playAudio } = useAudioPlayer()

  // Realtime API state
  const [useRealtimeApi, setUseRealtimeApi] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const playbackQueueRef = useRef<ArrayBuffer[]>([])
  const isPlayingRef = useRef(false)
  const transcriptBufferRef = useRef('')

  // Track whether we should auto-send after recording stops (HTTP mode only)
  const shouldSendVoiceRef = useRef(false)

  // Load config on mount
  useEffect(() => {
    fetchConfig().then((config) => {
      console.log('App config loaded:', config)
      setUseRealtimeApi(config.use_realtime_api)
    })
  }, [])

  // Play audio from queue (for Realtime API responses)
  const playNextAudio = useCallback(async () => {
    if (isPlayingRef.current || playbackQueueRef.current.length === 0) {
      return
    }

    isPlayingRef.current = true
    setStoreIsPlaying(true)

    const audioData = playbackQueueRef.current.shift()!
    const audioContext =
      audioContextRef.current ||
      new AudioContext({ sampleRate: 24000 })
    audioContextRef.current = audioContext

    try {
      // Convert PCM16 to Float32
      const int16Array = new Int16Array(audioData)
      const float32Array = new Float32Array(int16Array.length)
      for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / 32768.0
      }

      // Create audio buffer and play
      const audioBuffer = audioContext.createBuffer(1, float32Array.length, 24000)
      audioBuffer.copyToChannel(float32Array, 0)

      const source = audioContext.createBufferSource()
      source.buffer = audioBuffer
      source.connect(audioContext.destination)

      source.onended = () => {
        isPlayingRef.current = false
        if (playbackQueueRef.current.length > 0) {
          playNextAudio()
        } else {
          setStoreIsPlaying(false)
        }
      }

      source.start()
    } catch (err) {
      console.error('Audio playback error:', err)
      isPlayingRef.current = false
      setStoreIsPlaying(false)
    }
  }, [setStoreIsPlaying])

  // Handle WebSocket messages (Realtime API)
  const handleWsMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data)

        switch (data.type) {
          case 'audio':
            // Queue audio for playback
            playbackQueueRef.current.push(base64ToArrayBuffer(data.data))
            playNextAudio()
            break

          case 'transcript':
            // Accumulate transcript text
            if (data.text) {
              if (data.role === 'user') {
                // User transcript - add as user message
                addMessage({
                  role: 'user',
                  content: data.text,
                  agentMode,
                })
              } else {
                // Assistant transcript - accumulate
                transcriptBufferRef.current += data.text
              }
            }
            break

          case 'rich_content': {
            // Handle vocabulary/pattern cards
            const toolTypeMap: Record<string, RichContentType> = {
              render_vocabulary: 'vocabulary_card',
              render_pattern: 'pattern_card',
            }
            const contentType = toolTypeMap[data.tool] || 'vocabulary_card'
            const richContent: RichContent[] = [{
              type: contentType,
              data: data.data,
            }]
            addMessage({
              role: 'assistant',
              content: '',
              agentMode,
              richContent,
            })
            break
          }

          case 'speech_started':
            setIsLoading(true)
            break

          case 'response_done':
            // Flush transcript buffer as assistant message
            if (transcriptBufferRef.current.trim()) {
              addMessage({
                role: 'assistant',
                content: transcriptBufferRef.current,
                agentMode,
              })
              transcriptBufferRef.current = ''
            }
            incrementExchangeCount()
            setIsLoading(false)
            break

          case 'error':
            console.error('Realtime API error:', data.message)
            setIsLoading(false)
            addMessage({
              role: 'assistant',
              content: `Error: ${data.message}`,
              agentMode,
            })
            break

          case 'content_filtered':
            // Response was blocked by content filter, retrying
            console.warn('Content filter triggered, retrying...', data.message)
            // Keep loading state - waiting for retry
            break

          case 'response_incomplete':
            // Response was incomplete for non-filter reasons
            console.warn('Response incomplete:', data.reason, data.message)
            setIsLoading(false)
            if (transcriptBufferRef.current.trim()) {
              // Flush partial transcript
              addMessage({
                role: 'assistant',
                content: transcriptBufferRef.current + ' [incomplete]',
                agentMode,
              })
              transcriptBufferRef.current = ''
            }
            break

          case 'empty_audio':
            // User pressed PTT but didn't speak
            console.log('Empty audio buffer:', data.message)
            setIsLoading(false)
            // Don't add a message, just reset state
            break
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err)
      }
    },
    [addMessage, agentMode, playNextAudio, setIsLoading, incrementExchangeCount]
  )

  // Connect to Realtime API WebSocket
  const connectRealtime = useCallback(() => {
    if (!selectedLessonNumber) return null

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/ws/conversation/${selectedLessonNumber}?mode=${agentMode}&instruction_language=${instructionLanguage}`

    console.log('Connecting to Realtime API:', url)

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('Realtime WebSocket connected')
    }

    ws.onmessage = handleWsMessage

    ws.onclose = (event) => {
      console.log('Realtime WebSocket closed:', event.code, event.reason)
      wsRef.current = null
    }

    ws.onerror = (event) => {
      console.error('Realtime WebSocket error:', event)
    }

    return ws
  }, [selectedLessonNumber, agentMode, instructionLanguage, handleWsMessage])

  // Start voice recording (Realtime API mode)
  const startRealtimeRecording = useCallback(async () => {
    // Connect WebSocket if not connected
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      connectRealtime()
      // Wait for connection
      await new Promise<void>((resolve) => {
        const checkConnection = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            clearInterval(checkConnection)
            resolve()
          }
        }, 100)
        // Timeout after 5 seconds
        setTimeout(() => {
          clearInterval(checkConnection)
          resolve()
        }, 5000)
      })
    }

    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('Failed to connect to Realtime API')
      return
    }

    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 24000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      })
      mediaStreamRef.current = stream

      // Create audio context for processing
      const audioContext = new AudioContext({ sampleRate: 24000 })
      audioContextRef.current = audioContext

      const source = audioContext.createMediaStreamSource(stream)

      // Use ScriptProcessorNode for audio processing
      const processor = audioContext.createScriptProcessor(4096, 1, 1)
      processorRef.current = processor

      processor.onaudioprocess = (e) => {
        if (wsRef.current?.readyState !== WebSocket.OPEN) {
          return
        }

        const inputData = e.inputBuffer.getChannelData(0)
        const pcm16 = float32ToPcm16(inputData)
        const buffer = pcm16.buffer.slice(
          pcm16.byteOffset,
          pcm16.byteOffset + pcm16.byteLength
        ) as ArrayBuffer
        const base64 = arrayBufferToBase64(buffer)

        // Send audio to WebSocket
        wsRef.current.send(
          JSON.stringify({
            type: 'audio',
            data: base64,
          })
        )
      }

      source.connect(processor)
      processor.connect(audioContext.destination)

      setStoreIsRecording(true)
      console.log('Realtime recording started')
    } catch (err) {
      console.error('Failed to start realtime recording:', err)
    }
  }, [connectRealtime, setStoreIsRecording])

  // Stop voice recording (Realtime API mode)
  const stopRealtimeRecording = useCallback(() => {
    // Stop audio processing
    if (processorRef.current) {
      processorRef.current.disconnect()
      processorRef.current = null
    }

    // Stop media stream
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop())
      mediaStreamRef.current = null
    }

    // Commit audio buffer
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'commit' }))
    }

    setStoreIsRecording(false)
    console.log('Realtime recording stopped')
  }, [setStoreIsRecording])

  // Send text message via WebSocket (Realtime API mode)
  const sendRealtimeText = useCallback(
    async (text: string) => {
      if (!selectedLessonNumber || !text.trim()) return

      // Connect WebSocket if not connected
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        connectRealtime()
        // Wait for connection
        await new Promise<void>((resolve) => {
          const checkConnection = setInterval(() => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
              clearInterval(checkConnection)
              resolve()
            }
          }, 100)
          // Timeout after 5 seconds
          setTimeout(() => {
            clearInterval(checkConnection)
            resolve()
          }, 5000)
        })
      }

      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        console.error('Failed to connect to Realtime API')
        addMessage({
          role: 'assistant',
          content: 'Failed to connect to voice service. Please try again.',
          agentMode,
        })
        return
      }

      // Add user message to UI
      addMessage({ role: 'user', content: text, agentMode })
      setIsLoading(true)

      // Send text via WebSocket
      wsRef.current.send(JSON.stringify({ type: 'text', text }))
      console.log('Sent text via WebSocket:', text)
    },
    [selectedLessonNumber, agentMode, connectRealtime, addMessage, setIsLoading]
  )

  // Play audio chunks sequentially (for HTTP responses)
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

  // Send voice message via HTTP (transcribe audio then send)
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

  // Auto-send voice message when audioBlob becomes available after recording (HTTP mode)
  useEffect(() => {
    if (!useRealtimeApi && audioBlob && shouldSendVoiceRef.current && !isRecording) {
      shouldSendVoiceRef.current = false
      sendVoiceMessage(audioBlob)
    }
  }, [useRealtimeApi, audioBlob, isRecording, sendVoiceMessage])

  // Start recording - uses Realtime API or HTTP based on config (for PTT)
  const handleStartRecording = useCallback(async () => {
    if (isRecording) return // Already recording

    try {
      console.log('Starting recording...')
      if (useRealtimeApi) {
        await startRealtimeRecording()
      } else {
        shouldSendVoiceRef.current = false
        await startRecording()
        setStoreIsRecording(true)
        console.log('Recording started')
      }
    } catch (error) {
      console.error('Failed to start recording:', error)
      setStoreIsRecording(false)
    }
  }, [isRecording, useRealtimeApi, startRecording, startRealtimeRecording, setStoreIsRecording])

  // Stop recording - uses Realtime API or HTTP based on config (for PTT)
  const handleStopRecording = useCallback(() => {
    if (!isRecording) return // Not recording

    console.log('Stopping recording...')
    if (useRealtimeApi) {
      stopRealtimeRecording()
    } else {
      shouldSendVoiceRef.current = true // Flag to auto-send when blob is ready
      stopRecording()
      setStoreIsRecording(false)
      console.log('Recording stopped, will transcribe...')
    }
  }, [isRecording, useRealtimeApi, stopRecording, stopRealtimeRecording, setStoreIsRecording])

  // Toggle recording - kept for backward compatibility
  const toggleRecording = useCallback(async () => {
    if (isRecording) {
      handleStopRecording()
    } else {
      await handleStartRecording()
    }
  }, [isRecording, handleStartRecording, handleStopRecording])

  // Send text message - routes through WebSocket (Realtime) or HTTP based on config
  const sendTextMessage = useCallback(
    async (text: string) => {
      if (!selectedLessonNumber || !text.trim()) return

      // Route through WebSocket if Realtime API is enabled
      if (useRealtimeApi) {
        await sendRealtimeText(text)
        return
      }

      // HTTP fallback
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
      useRealtimeApi,
      sendRealtimeText,
      addMessage,
      setIsLoading,
      playAudioChunks,
      updatePhaseInfo,
      incrementExchangeCount,
    ]
  )

  // Disconnect WebSocket and cleanup resources
  const disconnect = useCallback(() => {
    console.log('Disconnecting realtime session...')

    // Stop any ongoing recording
    if (processorRef.current) {
      processorRef.current.disconnect()
      processorRef.current = null
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop())
      mediaStreamRef.current = null
    }

    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }

    // Clear playback queue
    playbackQueueRef.current = []
    isPlayingRef.current = false
    transcriptBufferRef.current = ''

    // Reset store state
    setStoreIsRecording(false)
    setStoreIsPlaying(false)
    setIsLoading(false)

    console.log('Realtime session disconnected')
  }, [setStoreIsRecording, setStoreIsPlaying, setIsLoading])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return {
    messages,
    isRecording,
    isPlaying,
    isLoading,
    audioBlob,
    voiceMode,
    setVoiceMode,
    toggleRecording,
    startRecording: handleStartRecording,
    stopRecording: handleStopRecording,
    sendTextMessage,
    sendVoiceMessage,
    clearMessages,
    disconnect,
  }
}
