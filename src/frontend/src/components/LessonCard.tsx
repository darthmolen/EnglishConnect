import { cn } from '@/lib/utils'
import type { LessonSummary } from '@/types'

interface LessonCardProps {
  lesson: LessonSummary
  isSelected?: boolean
  onClick?: () => void
}

export function LessonCard({
  lesson,
  isSelected = false,
  onClick,
}: LessonCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex w-full items-center gap-3 rounded-lg border p-3 text-left transition-colors',
        'hover:bg-accent hover:text-accent-foreground',
        isSelected
          ? 'border-primary bg-primary/5'
          : 'border-border bg-card'
      )}
    >
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-medium">
        {lesson.lesson_number}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium">{lesson.title}</p>
        {lesson.objective && (
          <p className="truncate text-sm text-muted-foreground">
            {lesson.objective}
          </p>
        )}
      </div>
    </button>
  )
}
