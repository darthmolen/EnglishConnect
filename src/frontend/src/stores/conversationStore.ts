import { create } from 'zustand'
import type {
  LessonSummary,
  LessonDetail,
  ChatMessage,
  LessonPhase,
  PhaseState,
  PhaseProgress,
} from '@/types'

interface ConversationState {
  // Lesson state
  lessons: LessonSummary[]
  currentLesson: LessonDetail | null
  selectedLessonNumber: number | null

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

export const useConversationStore = create<ConversationState>((set) => ({
  // Initial state
  lessons: [],
  currentLesson: null,
  selectedLessonNumber: null,
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
      // Reset phase info when switching lessons
      currentPhase: null,
      phaseState: null,
      phaseProgress: null,
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
}))
