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
  HelpingPhrase,
} from '@/types'
import { useAuthStore } from '@/stores/authStore'
import {
  logTiming,
  logTimingDelta,
  timingState,
  generateRequestId,
} from '@/utils/timing'
import type { LocalUser, TokenResponse } from '@/auth/localAuth'

const API_BASE = '/api'
const STT_BASE = 'http://localhost:8001'

// =============================================================================
// Auth Types
// =============================================================================

export interface AuthConfig {
  auth_mode: 'local' | 'azure_ad' | 'both'
  azure_ad_client_id: string | null
  azure_ad_tenant_id: string | null
}

export interface SignupRequest {
  email: string
  password: string
  confirm_password: string
  first_name?: string
  last_name?: string
  native_language?: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface UserResponse {
  id: string
  email: string
  display_name: string | null
  first_name: string | null
  last_name: string | null
  auth_provider: string
  is_approved: boolean
  approval_status: string
  roles: string[]
}

// =============================================================================
// Auth API Functions
// =============================================================================

let cachedAuthConfig: AuthConfig | null = null

/**
 * Fetch auth configuration (cached).
 */
export async function fetchAuthConfig(): Promise<AuthConfig> {
  if (cachedAuthConfig) {
    return cachedAuthConfig
  }

  const response = await fetch(`${API_BASE}/auth/config`)
  if (!response.ok) {
    // Default to local mode if config fails
    return { auth_mode: 'local', azure_ad_client_id: null, azure_ad_tenant_id: null }
  }
  cachedAuthConfig = await response.json()
  return cachedAuthConfig!
}

/**
 * Sign up a new user.
 */
export async function authSignup(data: SignupRequest): Promise<UserResponse> {
  const response = await fetch(`${API_BASE}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Signup failed')
  }

  return response.json()
}

/**
 * Log in with email and password.
 */
export async function authLogin(data: LoginRequest): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Login failed')
  }

  return response.json()
}

/**
 * Refresh access token using refresh token.
 */
export async function authRefreshToken(refreshToken: string): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })

  if (!response.ok) {
    throw new Error('Token refresh failed')
  }

  return response.json()
}

/**
 * Get current user info.
 */
export async function fetchCurrentUser(accessToken: string): Promise<LocalUser> {
  const response = await fetch(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })

  if (!response.ok) {
    throw new Error('Failed to fetch user')
  }

  const data: UserResponse = await response.json()
  return {
    id: data.id,
    email: data.email,
    displayName: data.display_name,
    firstName: data.first_name,
    lastName: data.last_name,
    isApproved: data.is_approved,
    approvalStatus: data.approval_status as 'pending' | 'approved' | 'rejected',
    roles: data.roles,
  }
}

/**
 * Log out (revoke refresh token).
 */
export async function authLogout(accessToken: string, refreshToken: string): Promise<void> {
  await fetch(`${API_BASE}/auth/logout`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
}

/**
 * Request password reset email.
 */
export async function requestPasswordReset(email: string): Promise<void> {
  await fetch(`${API_BASE}/auth/password-reset/request`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  // Always succeeds (anti-enumeration)
}

/**
 * Confirm password reset with token.
 */
export async function confirmPasswordReset(
  token: string,
  newPassword: string,
  confirmPassword: string
): Promise<void> {
  const response = await fetch(`${API_BASE}/auth/password-reset/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      token,
      new_password: newPassword,
      confirm_password: confirmPassword,
    }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Password reset failed')
  }
}

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
 * Fetch helping phrases for a language.
 *
 * These phrases allow students to request assistance during practice
 * in their native language (e.g., "No entiendo" in Spanish).
 *
 * @param language - Language code (es, en)
 */
export async function fetchHelpingPhrases(
  language: InstructionLanguage = 'es'
): Promise<HelpingPhrase[]> {
  try {
    const response = await fetch(
      `${API_BASE}/lessons/helping-phrases?language=${language}`
    )
    if (!response.ok) {
      return []
    }
    return response.json()
  } catch {
    return []
  }
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

// =============================================================================
// Admin Types
// =============================================================================

export interface UserListItem {
  id: string
  email: string
  display_name: string | null
  first_name: string | null
  last_name: string | null
  auth_provider: string
  is_approved: boolean
  approval_status: string
  roles: string[]
  created_at: string
}

export interface ApproveUserRequest {
  user_id: string
  approved: boolean
}

export interface AssignRoleRequest {
  user_id: string
  role: string
}

// =============================================================================
// Admin API Functions
// =============================================================================

/**
 * List all users (admin only).
 */
export async function adminListUsers(status?: string): Promise<UserListItem[]> {
  const params = new URLSearchParams()
  if (status) {
    params.set('status', status)
  }

  const url = `${API_BASE}/auth/admin/users${params.toString() ? `?${params}` : ''}`
  const response = await fetchWithAuth(url)

  if (!response.ok) {
    if (response.status === 403) {
      throw new Error('Admin access required')
    }
    throw new Error('Failed to list users')
  }

  return response.json()
}

/**
 * Approve or reject a user (admin only).
 */
export async function adminApproveUser(
  userId: string,
  approved: boolean
): Promise<UserResponse> {
  const response = await fetchWithAuth(`${API_BASE}/auth/admin/users/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, approved }),
  })

  if (!response.ok) {
    if (response.status === 403) {
      throw new Error('Admin access required')
    }
    const error = await response.json()
    throw new Error(error.detail || 'Failed to update user')
  }

  return response.json()
}

/**
 * Assign a role to a user (admin only).
 */
export async function adminAssignRole(
  userId: string,
  role: string
): Promise<UserResponse> {
  const response = await fetchWithAuth(`${API_BASE}/auth/admin/users/role`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, role }),
  })

  if (!response.ok) {
    if (response.status === 403) {
      throw new Error('Admin access required')
    }
    const error = await response.json()
    throw new Error(error.detail || 'Failed to assign role')
  }

  return response.json()
}
