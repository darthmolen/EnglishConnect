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

export interface EvaluationCriterion {
  criterion: string  // English
  criterion_es: string | null  // Spanish translation
}

export interface HelpingPhrase {
  phrase_key: string  // 'repeat', 'dont_understand', 'slower', 'example'
  phrase_text: string  // Native language phrase (e.g., "Repite, por favor")
  english_meaning: string  // English translation (e.g., "Please repeat")
  usage_context?: string  // When to use this phrase
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
  evaluation_criteria: EvaluationCriterion[]
}

export type LessonSection = 'principle' | 'goals' | 'vocabulary' | 'patterns' | 'examples' | 'practice' | 'evaluate'

// Personal goals with completion tracking
export interface PersonalGoal {
  id: string
  text: string
  completed: boolean
  createdAt: number
  completedAt?: number
}

// Study registry status (red/yellow/green)
export type StudyRegistryStatus = 'red' | 'yellow' | 'green'

// Study registry items
export type StudyRegistryItem =
  | 'studiedPrinciples'
  | 'memorizedVocabulary'
  | 'practicedPatterns'
  | 'dailyPractice'

// Unified agent modes (replaces old multi-agent: 'conversation' | 'lesson' | 'demo')
export type AgentMode = 'help' | 'practice'

// Voice interaction modes
export type VoiceMode = 'push-to-talk' | 'active'

export type InstructionLanguage = 'es' | 'en'

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
  agentMode?: AgentMode  // Track which agent generated this message
  richContent?: RichContent[] | null  // Inline cards to render after text
}

export interface ConversationRequest {
  message: string
  lesson_number: number
  mode: AgentMode  // 'help' for vocabulary page, 'practice' for practice page
  exchange_count: number  // Track exchanges for flip detection in practice mode
  instruction_language: InstructionLanguage  // Language for explanations
  history: ChatMessage[]
  focus_pattern?: number | null  // Optional: specific pattern to focus practice on
}

// Rich content types for inline rendering
export interface VocabularyCardData {
  english_word: string
  spanish_translation: string
  category: string
  lesson_number: number
  audio_url: string | null
}

export interface PatternCardData {
  pattern_number: number
  question_template: string
  answer_template: string
  lesson_number: number
  demo_audio_url: string | null
}

export interface LessonLinkData {
  lesson_number: number
  section?: string
  title: string
}

export type RichContentType = 'vocabulary_card' | 'pattern_card' | 'lesson_link'

export interface RichContent {
  type: RichContentType
  data: VocabularyCardData | PatternCardData | LessonLinkData
}

export interface ConversationResponse {
  text: string
  lesson_number: number
  audio_base64: string | null
  audio_format: string
  language: string
  rich_content?: RichContent[] | null
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
  // Rich content for inline rendering (vocabulary cards, etc.)
  rich_content?: RichContent[] | null
}
