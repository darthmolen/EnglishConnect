/**
 * API service for communicating with the backend.
 */

import type {
  LessonSummary,
  LessonDetail,
  ConversationRequest,
  TTSRequest,
  TTSResponse,
  STTResponse,
  ChatMessage,
  AgentMode,
  AgentResponse,
  InstructionLanguage,
} from '@/types'
import { useAuthStore } from '@/stores/authStore'
import {
  logTiming,
  logTimingDelta,
  timingState,
  generateRequestId,
} from '@/utils/timing'

const API_BASE = '/api'
const STT_BASE = 'http://localhost:8001'

/**
 * App configuration from backend.
 */
export interface AppConfig {
  use_realtime_api: boolean
  app_env: string
}

let cachedConfig: AppConfig | null = null

/**
 * Fetch app configuration (cached).
 */
export async function fetchConfig(): Promise<AppConfig> {
  if (cachedConfig) {
    return cachedConfig
  }

  try {
    const response = await fetch(`${API_BASE}/config`)
    if (!response.ok) {
      // Default to local mode if config fails
      return { use_realtime_api: false, app_env: 'development' }
    }
    cachedConfig = await response.json()
    return cachedConfig!
  } catch {
    // Default to local mode on error
    return { use_realtime_api: false, app_env: 'development' }
  }
}

/**
 * Fetch with authentication headers.
 */
async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const token = await useAuthStore.getState().getAccessToken()

  const headers = {
    ...options.headers,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }

  return fetch(url, { ...options, headers })
}

/**
 * Fetch all lessons for a course.
 */
export async function fetchLessons(courseId = 'ec1'): Promise<LessonSummary[]> {
  const response = await fetchWithAuth(`${API_BASE}/lessons?course_id=${courseId}`)
  if (!response.ok) {
    throw new Error('Failed to fetch lessons')
  }
  return response.json()
}

/**
 * Fetch detailed lesson data.
 *
 * @param lessonNumber - Lesson number to fetch
 * @param courseId - Course identifier (default: ec1)
 * @param instructionLanguage - Language for translations (default: es).
 *   Use 'en' to omit translations for English speakers.
 */
export async function fetchLessonDetail(
  lessonNumber: number,
  courseId = 'ec1',
  instructionLanguage = 'es'
): Promise<LessonDetail> {
  const params = new URLSearchParams({
    course_id: courseId,
    instruction_language: instructionLanguage,
  })
  const response = await fetchWithAuth(
    `${API_BASE}/lessons/${lessonNumber}?${params}`
  )
  if (!response.ok) {
    throw new Error(`Lesson ${lessonNumber} not found`)
  }
  return response.json()
}

/**
 * Send a conversation message and get AI response.
 * Uses unified endpoint with mode parameter.
 *
 * @param message - User's message
 * @param lessonNumber - Current lesson number
 * @param history - Conversation history
 * @param agentMode - 'help' for vocabulary page, 'practice' for practice page
 * @param exchangeCount - Number of exchanges (for flip detection in practice mode)
 * @param instructionLanguage - Language for explanations ('es' or 'en')
 * @param focusPattern - Optional pattern number to focus practice on
 */
export async function sendMessage(
  message: string,
  lessonNumber: number,
  history: ChatMessage[],
  agentMode: AgentMode = 'practice',
  exchangeCount: number = 0,
  instructionLanguage: InstructionLanguage = 'es',
  focusPattern: number | null = null
): Promise<AgentResponse> {
  // T0: Request sent - start timing
  const requestId = generateRequestId()
  timingState.setRequestId(requestId)
  const t0 = logTiming('T0', 'request_sent', { mode: agentMode, lesson: lessonNumber })
  timingState.setT0(t0)

  const request: ConversationRequest = {
    message,
    lesson_number: lessonNumber,
    mode: agentMode,
    exchange_count: exchangeCount,
    instruction_language: instructionLanguage,
    history,
    focus_pattern: focusPattern,
  }

  const response = await fetchWithAuth(`${API_BASE}/practice/conversation`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Request-ID': requestId, // Correlate with backend timing
    },
    body: JSON.stringify(request),
  })

  // T10: Response received (first byte)
  logTimingDelta('T10', 'response_received', t0)

  if (!response.ok) {
    throw new Error('Failed to send message')
  }
  return response.json()
}

/**
 * Request TTS synthesis for text.
 */
export async function synthesizeSpeech(
  text: string,
  voice = 'speaker_a'
): Promise<TTSResponse> {
  const request: TTSRequest = { text, voice }

  const response = await fetchWithAuth(`${API_BASE}/tts`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    throw new Error('Failed to synthesize speech')
  }
  return response.json()
}

/**
 * Transcribe audio using STT service.
 * Calls STT service directly (CORS enabled).
 */
export async function transcribeAudio(
  audioBlob: Blob,
  language?: string
): Promise<STTResponse> {
  console.log(`Sending audio to STT: ${audioBlob.size} bytes, type=${audioBlob.type}`)

  // S1: Audio sent to STT service (recording already stopped)
  const s1 = logTiming('S1', 'audio_sent', { audio_bytes: audioBlob.size })

  const formData = new FormData()
  formData.append('file', audioBlob, 'audio.webm')

  const url = new URL('/transcribe', STT_BASE)
  if (language) {
    url.searchParams.set('language', language)
  }

  const response = await fetch(url.toString(), {
    method: 'POST',
    headers: {
      'X-Request-ID': timingState.getRequestId(), // Correlate with STT service timing
    },
    body: formData,
  })

  // S5: STT result received
  logTimingDelta('S5', 'stt_result_received', s1)

  if (!response.ok) {
    throw new Error('Failed to transcribe audio')
  }
  return response.json()
}
