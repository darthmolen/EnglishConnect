/**
 * API service for communicating with the backend.
 */

import type {
  LessonSummary,
  LessonDetail,
  ConversationRequest,
  ConversationResponse,
  TTSRequest,
  TTSResponse,
  STTResponse,
  ChatMessage,
} from '@/types'
import { useAuthStore } from '@/stores/authStore'

const API_BASE = '/api'
const STT_BASE = 'http://localhost:8001'

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
 */
export async function fetchLessonDetail(
  lessonNumber: number,
  courseId = 'ec1'
): Promise<LessonDetail> {
  const response = await fetchWithAuth(
    `${API_BASE}/lessons/${lessonNumber}?course_id=${courseId}`
  )
  if (!response.ok) {
    throw new Error(`Lesson ${lessonNumber} not found`)
  }
  return response.json()
}

/**
 * Send a conversation message and get AI response.
 */
export async function sendMessage(
  message: string,
  lessonNumber: number,
  history: ChatMessage[]
): Promise<ConversationResponse> {
  const request: ConversationRequest = {
    message,
    lesson_number: lessonNumber,
    history,
  }

  const response = await fetchWithAuth(`${API_BASE}/conversation`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

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

  const formData = new FormData()
  formData.append('file', audioBlob, 'audio.webm')

  const url = new URL('/transcribe', STT_BASE)
  if (language) {
    url.searchParams.set('language', language)
  }

  const response = await fetch(url.toString(), {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error('Failed to transcribe audio')
  }
  return response.json()
}
