import { useEffect } from 'react'
import { useConversationStore } from '@/stores/conversationStore'
import { fetchLessons, fetchLessonDetail } from '@/services/api'

export function useLessons() {
  const {
    courseId,
    lessons,
    currentLesson,
    selectedLessonNumber,
    instructionLanguage,
    setLessons,
    setCurrentLesson,
    selectLesson,
  } = useConversationStore()

  // Fetch lessons when course changes
  useEffect(() => {
    fetchLessons(courseId)
      .then(setLessons)
      .catch((error) => console.error('Failed to fetch lessons:', error))
  }, [courseId, setLessons])

  // Fetch lesson details when selection, course, or instruction language changes
  useEffect(() => {
    if (selectedLessonNumber !== null) {
      fetchLessonDetail(selectedLessonNumber, courseId, instructionLanguage)
        .then(setCurrentLesson)
        .catch((error) =>
          console.error('Failed to fetch lesson detail:', error)
        )
    } else {
      setCurrentLesson(null)
    }
  }, [selectedLessonNumber, courseId, instructionLanguage, setCurrentLesson])

  return {
    lessons,
    currentLesson,
    selectedLessonNumber,
    selectLesson,
  }
}
