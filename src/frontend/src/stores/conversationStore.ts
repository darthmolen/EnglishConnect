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

      // Phase tracking initial state
      currentPhase: null,
      phaseState: null,
      phaseProgress: null,

      // Actions
      setLessons: (lessons) => set({ lessons }),

      setCurrentLesson: (lesson) => set({ currentLesson: lesson }),

      selectLesson: (lessonNumber) =>
        set({
          selectedLessonNumber: lessonNumber,
          messages: [], // Clear conversation when switching lessons
          activeSection: 'principle',  // Reset to principle when switching lessons
          // Reset phase info when switching lessons
          currentPhase: null,
          phaseState: null,
          phaseProgress: null,
        }),

      setActiveSection: (section) => set({ activeSection: section }),

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
    }),
    {
      name: 'englishconnect-goals',
      // Only persist completedGoals to localStorage
      partialize: (state) => ({ completedGoals: state.completedGoals }),
    }
  )
)
