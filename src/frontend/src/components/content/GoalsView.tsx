import { Checkbox } from '@/components/ui/checkbox'
import { cn } from '@/lib/utils'

interface GoalsViewProps {
  lessonNumber: number
  criteria: string[]
  completedGoals: number[]
  onToggleGoal: (lessonNumber: number, goalIndex: number) => void
}

export function GoalsView({
  lessonNumber,
  criteria,
  completedGoals,
  onToggleGoal,
}: GoalsViewProps) {
  if (criteria.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <p>No learning goals available for this lesson</p>
      </div>
    )
  }

  const completedCount = completedGoals.length
  const totalCount = criteria.length
  const progressPercent = (completedCount / totalCount) * 100

  return (
    <div className="p-4 space-y-4">
      {/* Progress indicator */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium">Progress</span>
          <span className="text-muted-foreground">
            {completedCount} of {totalCount} completed
          </span>
        </div>
        <div className="h-2 rounded-full bg-muted overflow-hidden">
          <div
            className="h-full bg-primary transition-all duration-300"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Goals list */}
      <div className="space-y-2">
        <h4 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          I can:
        </h4>
        <ul className="space-y-1">
          {criteria.map((goal, index) => {
            const isCompleted = completedGoals.includes(index)
            return (
              <li key={index}>
                <label
                  className={cn(
                    'flex items-center gap-3 rounded-lg p-3 cursor-pointer transition-colors',
                    'hover:bg-accent/50',
                    isCompleted && 'bg-green-50 dark:bg-green-950/20'
                  )}
                >
                  <Checkbox
                    checked={isCompleted}
                    onCheckedChange={() => onToggleGoal(lessonNumber, index)}
                    className="shrink-0"
                  />
                  <span
                    className={cn(
                      'text-sm',
                      isCompleted && 'text-green-700 dark:text-green-400'
                    )}
                  >
                    {goal}
                  </span>
                </label>
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}
