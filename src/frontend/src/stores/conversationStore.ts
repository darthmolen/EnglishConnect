import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type {
  LessonSummary,
  LessonDetail,
  ChatMessage,
  LessonPhase,
  PhaseState,
  PhaseProgress,
  LessonSection,
  AgentMode,
  InstructionLanguage,
} from '@/types'

interface ConversationState {
  // Lesson state
  lessons: LessonSummary[]
  currentLesson: LessonDetail | null
  selectedLessonNumber: number | null

  // UI state for content sections
  activeSection: LessonSection | null

  // Learning goals completion state (persisted)
  completedGoals: Record<number, number[]>  // lessonNumber -> array of completed goal indices

  // Conversation state
  messages: ChatMessage[]
  isLoading: boolean

  // Phase tracking state (for structured lessons)
  currentPhase: LessonPhase | null
  phaseState: PhaseState | null
  phaseProgress: PhaseProgress | null

  // Voice state
  isRecording: boolean
  isPlaying: boolean

  // Intro playback tracking (not persisted - fresh each session)
  // Keys are "lessonNumber-language" (e.g., "5-es", "5-en")
  introPlayedKeys: string[]

  // Agent mode ('help' for vocabulary page, 'practice' for practice page)
  agentMode: AgentMode

  // Exchange count for flip detection in practice mode
  exchangeCount: number

  // Instruction language for agent explanations (persisted)
  instructionLanguage: InstructionLanguage

  // Actions
  setLessons: (lessons: LessonSummary[]) => void
  setCurrentLesson: (lesson: LessonDetail | null) => void
  selectLesson: (lessonNumber: number) => void
  setActiveSection: (section: LessonSection | null) => void
  toggleGoal: (lessonNumber: number, goalIndex: number) => void
  addMessage: (message: ChatMessage) => void
  clearMessages: () => void
  setIsLoading: (isLoading: boolean) => void
  setIsRecording: (isRecording: boolean) => void
  setIsPlaying: (isPlaying: boolean) => void
  updatePhaseInfo: (
    phase: LessonPhase | null,
    state: PhaseState | null,
    progress: PhaseProgress | null
  ) => void
  clearPhaseInfo: () => void
  setAgentMode: (mode: AgentMode) => void
  setInstructionLanguage: (language: InstructionLanguage) => void
  markIntroPlayed: (key: string) => void
  incrementExchangeCount: () => void
  resetExchangeCount: () => void
}

export const useConversationStore = create<ConversationState>()(
  persist(
    (set) => ({
      // Initial state
      lessons: [],
      currentLesson: null,
      selectedLessonNumber: null,
      activeSection: 'principle' as LessonSection,  // Default to principle (encouragement first)
      completedGoals: {},
      messages: [],
      isLoading: false,
      isRecording: false,
      isPlaying: false,

      // Intro playback tracking (not persisted)
      introPlayedKeys: [],

      // Phase tracking initial state
      currentPhase: null,
      phaseState: null,
      phaseProgress: null,

      // Agent mode - default to practice mode
      agentMode: 'practice' as AgentMode,

      // Exchange count for flip detection
      exchangeCount: 0,

      // Instruction language - default to Spanish
      instructionLanguage: 'es' as InstructionLanguage,

      // Actions
      setLessons: (lessons) => set({ lessons }),

      setCurrentLesson: (lesson) => set({ currentLesson: lesson }),

      selectLesson: (lessonNumber) =>
        set({
          selectedLessonNumber: lessonNumber,
          messages: [], // Clear conversation when switching lessons
          activeSection: 'principle',  // Reset to principle when switching lessons
          agentMode: 'practice',  // Reset to practice mode when switching lessons
          exchangeCount: 0,  // Reset exchange count when switching lessons
          // Reset phase info when switching lessons
          currentPhase: null,
          phaseState: null,
          phaseProgress: null,
        }),

      setActiveSection: (section) => {
        // Determine agent mode based on section
        // Vocabulary page → 'help' mode (answer questions only)
        // Practice page → 'practice' mode (lead conversation, flip roles)
        const newAgentMode: AgentMode = section === 'vocabulary' ? 'help' : 'practice'
        return set({
          activeSection: section,
          agentMode: newAgentMode,
          exchangeCount: 0,  // Reset exchange count when switching sections
        })
      },

      toggleGoal: (lessonNumber, goalIndex) =>
        set((state) => {
          const currentGoals = state.completedGoals[lessonNumber] || []
          const isCompleted = currentGoals.includes(goalIndex)
          const newGoals = isCompleted
            ? currentGoals.filter((i) => i !== goalIndex)
            : [...currentGoals, goalIndex]
          return {
            completedGoals: {
              ...state.completedGoals,
              [lessonNumber]: newGoals,
            },
          }
        }),

      addMessage: (message) =>
        set((state) => ({
          messages: [...state.messages, message],
        })),

      clearMessages: () =>
        set({
          messages: [],
          // Also reset phase info when clearing messages
          currentPhase: null,
          phaseState: null,
          phaseProgress: null,
        }),

      setIsLoading: (isLoading) => set({ isLoading }),

      setIsRecording: (isRecording) => set({ isRecording }),

      setIsPlaying: (isPlaying) => set({ isPlaying }),

      updatePhaseInfo: (phase, state, progress) =>
        set({
          currentPhase: phase,
          phaseState: state,
          phaseProgress: progress,
        }),

      clearPhaseInfo: () =>
        set({
          currentPhase: null,
          phaseState: null,
          phaseProgress: null,
        }),

      setAgentMode: (mode) => set({ agentMode: mode }),

      setInstructionLanguage: (language) => set({ instructionLanguage: language }),

      markIntroPlayed: (key) =>
        set((state) => ({
          introPlayedKeys: state.introPlayedKeys.includes(key)
            ? state.introPlayedKeys
            : [...state.introPlayedKeys, key],
        })),

      incrementExchangeCount: () =>
        set((state) => ({ exchangeCount: state.exchangeCount + 1 })),

      resetExchangeCount: () => set({ exchangeCount: 0 }),
    }),
    {
      name: 'englishconnect-settings',
      // Persist completedGoals and instructionLanguage to localStorage
      partialize: (state) => ({
        completedGoals: state.completedGoals,
        instructionLanguage: state.instructionLanguage,
      }),
    }
  )
)
