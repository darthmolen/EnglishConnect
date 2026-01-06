/**
 * Hook for real-time voice conversation using Azure OpenAI Realtime API.
 *
 * This replaces the HTTP-based useConversation hook with WebSocket streaming,
 * providing lower latency by handling STT+LLM+TTS in a single connection.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useConversationStore } from '@/stores/conversationStore'
import type { AgentMode, RichContent, RichContentType } from '@/types'

interface RealtimeConfig {
  lessonNumber: number
  mode: AgentMode
  instructionLanguage?: string
}

interface TranscriptEvent {
  type: 'transcript'
  role: 'user' | 'assistant'
  text: string
}

interface RichContentEvent {
  type: 'rich_content'
  tool: string
  data: Record<string, unknown>
}

type RealtimeEvent =
  | { type: 'audio'; data: string }
  | TranscriptEvent
  | RichContentEvent
  | { type: 'speech_started' }
  | { type: 'speech_stopped' }
  | { type: 'response_done' }
  | { type: 'error'; message: string }

/**
 * Convert Float32Array to PCM16 Int16Array
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
 * Convert Int16Array to ArrayBuffer for WebSocket
 */
function int16ToArrayBuffer(int16: Int16Array): ArrayBuffer {
  // slice() returns ArrayBuffer | SharedArrayBuffer, cast to ArrayBuffer
  return int16.buffer.slice(
    int16.byteOffset,
    int16.byteOffset + int16.byteLength
  ) as ArrayBuffer
}

/**
 * Convert ArrayBuffer to Base64 string
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
 * Convert Base64 string to ArrayBuffer
 */
function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes.buffer
}

export function useRealtimeConversation(config: RealtimeConfig) {
  const { lessonNumber, mode, instructionLanguage = 'es' } = config

  const {
    messages,
    addMessage,
    clearMessages,
    setIsLoading,
    setIsRecording: setStoreIsRecording,
    setIsPlaying: setStoreIsPlaying,
  } = useConversationStore()

  const [isConnected, setIsConnected] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const playbackQueueRef = useRef<ArrayBuffer[]>([])
  const isPlayingRef = useRef(false)

  // Build WebSocket URL
  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    return `${protocol}//${host}/ws/conversation/${lessonNumber}?mode=${mode}&instruction_language=${instructionLanguage}`
  }, [lessonNumber, mode, instructionLanguage])

  // Play audio from queue
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

  // Handle incoming WebSocket messages
  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const data: RealtimeEvent = JSON.parse(event.data)

        switch (data.type) {
          case 'audio':
            // Queue audio for playback
            const audioBuffer = base64ToArrayBuffer(data.data)
            playbackQueueRef.current.push(audioBuffer)
            playNextAudio()
            break

          case 'transcript':
            // Update conversation with transcript
            if (data.text.trim()) {
              addMessage({
                role: data.role,
                content: data.text,
                agentMode: mode,
              })
            }
            break

          case 'rich_content': {
            // Handle rich content (vocabulary cards, patterns)
            // Map tool name to RichContentType
            const toolTypeMap: Record<string, RichContentType> = {
              render_vocabulary: 'vocabulary_card',
              render_pattern: 'pattern_card',
            }
            const contentType = toolTypeMap[data.tool] || 'vocabulary_card'
            const richContent: RichContent[] = [{
              type: contentType,
              data: data.data as unknown as RichContent['data'],
            }]
            addMessage({
              role: 'assistant',
              content: '',
              agentMode: mode,
              richContent,
            })
            break
          }

          case 'speech_started':
            setIsLoading(true)
            break

          case 'speech_stopped':
            // Speech ended, waiting for response
            break

          case 'response_done':
            setIsLoading(false)
            break

          case 'error':
            console.error('Realtime API error:', data.message)
            setError(data.message)
            setIsLoading(false)
            break
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err)
      }
    },
    [addMessage, mode, playNextAudio, setIsLoading]
  )

  // Connect to WebSocket
  const connect = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    const url = getWebSocketUrl()
    console.log('Connecting to Realtime API:', url)

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('WebSocket connected')
      setIsConnected(true)
      setError(null)
    }

    ws.onmessage = handleMessage

    ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason)
      setIsConnected(false)
      stopListening()
    }

    ws.onerror = (event) => {
      console.error('WebSocket error:', event)
      setError('Connection error')
      setIsConnected(false)
    }
  }, [getWebSocketUrl, handleMessage])

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
    stopListening()
  }, [])

  // Start listening (capture microphone and stream to WebSocket)
  const startListening = useCallback(async () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected')
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
      // (AudioWorklet would be better but requires more setup)
      const processor = audioContext.createScriptProcessor(4096, 1, 1)
      processorRef.current = processor

      processor.onaudioprocess = (e) => {
        if (wsRef.current?.readyState !== WebSocket.OPEN) {
          return
        }

        const inputData = e.inputBuffer.getChannelData(0)
        const pcm16 = float32ToPcm16(inputData)
        const buffer = int16ToArrayBuffer(pcm16)
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

      setIsListening(true)
      setStoreIsRecording(true)
      console.log('Started listening')
    } catch (err) {
      console.error('Failed to start listening:', err)
      setError('Microphone access denied')
    }
  }, [setStoreIsRecording])

  // Stop listening
  const stopListening = useCallback(() => {
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

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }

    setIsListening(false)
    setStoreIsRecording(false)
    console.log('Stopped listening')
  }, [setStoreIsRecording])

  // Toggle listening state
  const toggleListening = useCallback(async () => {
    if (isListening) {
      stopListening()
      // Optionally commit the audio buffer
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'commit' }))
      }
    } else {
      await startListening()
    }
  }, [isListening, startListening, stopListening])

  // Cancel current response
  const cancelResponse = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'cancel' }))
    }
    // Clear playback queue
    playbackQueueRef.current = []
    setStoreIsPlaying(false)
  }, [setStoreIsPlaying])

  // Auto-connect when config changes
  useEffect(() => {
    connect()
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    // State
    isConnected,
    isListening,
    isPlaying: isPlayingRef.current,
    messages,
    error,

    // Actions
    connect,
    disconnect,
    startListening,
    stopListening,
    toggleListening,
    cancelResponse,
    clearMessages,
  }
}
