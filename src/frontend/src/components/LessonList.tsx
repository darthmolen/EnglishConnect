import { useTranslation } from 'react-i18next'
import { LessonCard } from './LessonCard'
import type { LessonSummary } from '@/types'

interface LessonListProps {
  lessons: LessonSummary[]
  selectedLessonNumber: number | null
  onSelectLesson: (lessonNumber: number) => void
}

export function LessonList({
  lessons,
  selectedLessonNumber,
  onSelectLesson,
}: LessonListProps) {
  const { t } = useTranslation()

  if (lessons.length === 0) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        {t('lessons.loading')}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2 p-2">
      {lessons.map((lesson) => (
        <LessonCard
          key={lesson.lesson_number}
          lesson={lesson}
          isSelected={lesson.lesson_number === selectedLessonNumber}
          onClick={() => onSelectLesson(lesson.lesson_number)}
        />
      ))}
    </div>
  )
}
