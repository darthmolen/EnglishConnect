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
  answer_template: string
  examples: Record<string, string>[] | null
}

export interface LessonDetail {
  lesson_number: number
  title: string
  objective: string | null
  learning_principle_title: string | null
  learning_principle_content: string | null
  vocabulary: VocabularyItem[]
  patterns: QAPattern[]
  evaluation_criteria: string[]
}

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
}

export interface ConversationRequest {
  message: string
  lesson_number: number
  history: ChatMessage[]
}

export interface ConversationResponse {
  text: string
  lesson_number: number
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
