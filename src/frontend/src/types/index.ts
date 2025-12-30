/**
 * Frontend TypeScript types matching backend Pydantic schemas.
 */

export interface LessonSummary {
  lesson_number: number
  title: string
  objective: string | null
}

export interface VocabularyItem {
  english: string
  spanish: string
  category: string | null
}

export interface QAPattern {
  pattern_number: number
  question_template: string
  question_translation: string | null  // Native language translation (language-agnostic)
  answer_template: string
  answer_translation: string | null  // Native language translation (language-agnostic)
  examples: Record<string, string | null>[] | null  // Has q, a, optionally q_translation, a_translation
}

export interface LessonDetail {
  lesson_number: number
  title: string
  objective: string | null
  learning_principle_title: string | null
  learning_principle_content: string | null
  learning_principle_full: string | null
  ponder_questions: string[]
  pattern_images: string[]
  vocabulary: VocabularyItem[]
  patterns: QAPattern[]
  evaluation_criteria: string[]
}

export type LessonSection = 'principle' | 'goals' | 'practice' | 'vocabulary'

export type AgentMode = 'conversation' | 'lesson' | 'demo'

export type InstructionLanguage = 'es' | 'en'

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
  agentMode?: AgentMode  // Track which agent generated this message
}

export interface ConversationRequest {
  message: string
  lesson_number: number
  history: ChatMessage[]
}

export interface ConversationResponse {
  text: string
  lesson_number: number
  audio_base64: string | null
  audio_format: string
  language: string
}

export interface TTSRequest {
  text: string
  voice?: string
}

export interface TTSResponse {
  audio_base64: string
  format: string
  sample_rate: number
}

export interface STTResponse {
  text: string
  language: string
  confidence: number
}

// Lesson phase types for structured lessons
export interface LessonPhase {
  id: number
  phase_type: 'intro' | 'vocabulary' | 'patterns' | 'practice' | 'wrapup'
  phase_name: string
  sort_order: number
}

export interface PhaseState {
  vocab_index: number
  pattern_index: number
  items_completed: string[]
  can_skip_ahead: boolean
}

export interface PhaseProgress {
  current: number
  total: number
}

export interface LessonConversationRequest {
  message: string
  lesson_number: number
  history: ChatMessage[]
  section?: string  // Optional: 'vocabulary', 'practice', etc.
  instruction_language?: InstructionLanguage  // Language for agent explanations (default 'es')
}

// Single audio chunk from a speak() call
export interface AudioChunk {
  audio_base64: string
  format: string
  language: string
  text: string
}

export interface LessonConversationResponse {
  text: string
  lesson_number: number
  phase: LessonPhase
  phase_state: PhaseState
  phase_progress: PhaseProgress | null
  audio_base64: string | null  // Deprecated: use audio_chunks
  audio_format: string
  language: string
  audio_chunks: AudioChunk[] | null  // All speak() audio in order
}

export interface DemoConversationResponse {
  text: string
  lesson_number: number
  audio_base64: string | null
  audio_format: string
  language: string
  demo_played: number | null  // Index of demo that was played
}

// Unified response type that handles all agent responses
export type AgentResponse = ConversationResponse & {
  // Optional fields from lesson agent
  phase?: LessonPhase
  phase_state?: PhaseState
  phase_progress?: PhaseProgress | null
  // Optional fields from demo agent
  demo_played?: number | null
  // Multiple audio chunks (for bilingual responses)
  audio_chunks?: AudioChunk[] | null
}
