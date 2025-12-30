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

  // Agent mode (which agent handles conversation)
  agentMode: AgentMode

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

      // Agent mode - default to conversation partner
      agentMode: 'conversation' as AgentMode,

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
          agentMode: 'conversation',  // Reset to conversation agent when switching lessons
          // Reset phase info when switching lessons
          currentPhase: null,
          phaseState: null,
          phaseProgress: null,
        }),

      setActiveSection: (section) => {
        // Determine agent mode based on section
        let newAgentMode: AgentMode = 'conversation'
        if (section === 'vocabulary') {
          newAgentMode = 'lesson'
        }
        // Note: 'demo' mode is set explicitly via setAgentMode when user clicks Demo Play
        // Practice section uses 'conversation' mode (conversation partner)
        return set({ activeSection: section, agentMode: newAgentMode })
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
