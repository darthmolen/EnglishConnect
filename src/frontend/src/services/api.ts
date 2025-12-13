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
  ChatMessage,
} from '@/types'

const API_BASE = '/api'

/**
 * Fetch all lessons for a course.
 */
export async function fetchLessons(courseId = 'ec1'): Promise<LessonSummary[]> {
  const response = await fetch(`${API_BASE}/lessons?course_id=${courseId}`)
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
  const response = await fetch(
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

  const response = await fetch(`${API_BASE}/conversation`, {
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

  const response = await fetch(`${API_BASE}/tts`, {
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
