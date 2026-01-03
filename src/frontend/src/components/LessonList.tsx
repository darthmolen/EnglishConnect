import { useTranslation } from 'react-i18next'
import { ClipboardList } from 'lucide-react'
import { LessonCard } from './LessonCard'
import { cn } from '@/lib/utils'
import type { LessonSummary } from '@/types'

interface LessonListProps {
  lessons: LessonSummary[]
  selectedLessonNumber: number | null
  isRegistrySelected: boolean
  onSelectLesson: (lessonNumber: number) => void
  onSelectRegistryPage: () => void
}

export function LessonList({
  lessons,
  selectedLessonNumber,
  isRegistrySelected,
  onSelectLesson,
  onSelectRegistryPage,
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
      {/* Personal Study Registry - special item at top */}
      <button
        type="button"
        onClick={onSelectRegistryPage}
        className={cn(
          'flex items-center gap-2 rounded-lg p-3 text-left transition-colors',
          'hover:bg-accent/50 border',
          isRegistrySelected && 'bg-primary/10 border-primary'
        )}
      >
        <ClipboardList className="h-5 w-5 shrink-0" />
        <span className="font-medium text-sm">{t('registry.title')}</span>
      </button>

      {/* Divider */}
      <div className="border-t my-1" />

      {/* Regular lessons */}
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
