import { useEffect } from 'react'
import { useConversationStore } from '@/stores/conversationStore'
import { fetchLessons, fetchLessonDetail } from '@/services/api'

export function useLessons() {
  const {
    lessons,
    currentLesson,
    selectedLessonNumber,
    setLessons,
    setCurrentLesson,
    selectLesson,
  } = useConversationStore()

  // Fetch lessons on mount
  useEffect(() => {
    fetchLessons()
      .then(setLessons)
      .catch((error) => console.error('Failed to fetch lessons:', error))
  }, [setLessons])

  // Fetch lesson details when selection changes
  useEffect(() => {
    if (selectedLessonNumber !== null) {
      fetchLessonDetail(selectedLessonNumber)
        .then(setCurrentLesson)
        .catch((error) =>
          console.error('Failed to fetch lesson detail:', error)
        )
    } else {
      setCurrentLesson(null)
    }
  }, [selectedLessonNumber, setCurrentLesson])

  return {
    lessons,
    currentLesson,
    selectedLessonNumber,
    selectLesson,
  }
}
