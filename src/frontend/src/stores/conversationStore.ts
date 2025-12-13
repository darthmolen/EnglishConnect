import { create } from 'zustand'
import type { LessonSummary, LessonDetail, ChatMessage } from '@/types'

interface ConversationState {
  // Lesson state
  lessons: LessonSummary[]
  currentLesson: LessonDetail | null
  selectedLessonNumber: number | null

  // Conversation state
  messages: ChatMessage[]
  isLoading: boolean

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

  // Actions
  setLessons: (lessons) => set({ lessons }),

  setCurrentLesson: (lesson) => set({ currentLesson: lesson }),

  selectLesson: (lessonNumber) =>
    set({
      selectedLessonNumber: lessonNumber,
      messages: [], // Clear conversation when switching lessons
    }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  clearMessages: () => set({ messages: [] }),

  setIsLoading: (isLoading) => set({ isLoading }),

  setIsRecording: (isRecording) => set({ isRecording }),

  setIsPlaying: (isPlaying) => set({ isPlaying }),
}))
