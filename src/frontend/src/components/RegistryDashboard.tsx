import { useTranslation } from 'react-i18next'
import { X, Check } from 'lucide-react'
import { Checkbox } from '@/components/ui/checkbox'
import { cn } from '@/lib/utils'
import type { LessonSummary, PersonalGoal, StudyRegistryStatus, StudyRegistryItem } from '@/types'

const STUDY_REGISTRY_ITEMS: StudyRegistryItem[] = [
  'studiedPrinciples',
  'memorizedVocabulary',
  'practicedPatterns',
  'dailyPractice',
]

interface RegistryDashboardProps {
  lessons: LessonSummary[]
  studyRegistry: Record<number, Record<StudyRegistryItem, StudyRegistryStatus>>
  personalGoals: PersonalGoal[]
  onToggleGoal: (goalId: string) => void
  onRemoveGoal: (goalId: string) => void
  className?: string
}

function StatusDot({ status, title }: { status: StudyRegistryStatus | undefined; title: string }) {
  return (
    <span
      className={cn(
        'inline-block w-3 h-3 rounded-full',
        status === 'green' && 'bg-green-500',
        status === 'yellow' && 'bg-yellow-400',
        status === 'red' && 'bg-red-500',
        !status && 'bg-gray-300 dark:bg-gray-600'  // Grey for unset status
      )}
      title={title}
    />
  )
}

function getStatusTitle(status: StudyRegistryStatus | undefined, t: (key: string) => string): string {
  if (!status) return t('status.none')
  return t(`status.${status}`)
}

export function RegistryDashboard({
  lessons,
  studyRegistry,
  personalGoals,
  onToggleGoal,
  onRemoveGoal,
  className,
}: RegistryDashboardProps) {
  const { t } = useTranslation()

  const openGoals = personalGoals.filter((g) => !g.completed)
  const completedGoals = personalGoals.filter((g) => g.completed)

  return (
    <div className={cn('overflow-y-auto bg-background p-4', className)}>
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Section 1: Lesson Progress */}
        <section className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold">
              {t('registry.lessonProgress')}
            </h2>
            <p className="text-sm text-muted-foreground">
              {t('registry.lessonProgressHint')}
            </p>
          </div>

          <div className="border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">#</th>
                  <th className="px-3 py-2 text-left font-medium">
                    {t('registry.lesson')}
                  </th>
                  <th className="px-3 py-2 text-center font-medium" colSpan={4}>
                    {t('registry.lessonProgress')}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {lessons.map((lesson) => {
                  const registry = studyRegistry[lesson.lesson_number] || {}
                  return (
                    <tr key={lesson.lesson_number} className="hover:bg-muted/30">
                      <td className="px-3 py-2 text-muted-foreground">
                        {lesson.lesson_number}
                      </td>
                      <td className="px-3 py-2">{lesson.title}</td>
                      <td className="px-2 py-2 text-center">
                        <StatusDot status={registry.studiedPrinciples} title={getStatusTitle(registry.studiedPrinciples, t)} />
                      </td>
                      <td className="px-2 py-2 text-center">
                        <StatusDot status={registry.memorizedVocabulary} title={getStatusTitle(registry.memorizedVocabulary, t)} />
                      </td>
                      <td className="px-2 py-2 text-center">
                        <StatusDot status={registry.practicedPatterns} title={getStatusTitle(registry.practicedPatterns, t)} />
                      </td>
                      <td className="px-2 py-2 text-center">
                        <StatusDot status={registry.dailyPractice} title={getStatusTitle(registry.dailyPractice, t)} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Legend */}
          <div className="flex gap-4 text-xs text-muted-foreground">
            {STUDY_REGISTRY_ITEMS.map((item, i) => (
              <span key={item} className="flex items-center gap-1">
                <span className="font-medium">{i + 1}.</span>
                {t(`evaluate.${item}`)}
              </span>
            ))}
          </div>
        </section>

        {/* Section 2: Goals */}
        <section className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold">{t('registry.goals')}</h2>
          </div>

          {/* Open Goals */}
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
              {t('registry.openGoals')}
            </h3>
            {openGoals.length === 0 ? (
              <p className="text-sm text-muted-foreground italic p-3 bg-muted/30 rounded-lg">
                {t('registry.noOpenGoals')}
              </p>
            ) : (
              <ul className="space-y-2">
                {openGoals.map((goal) => (
                  <li
                    key={goal.id}
                    className="flex items-center gap-3 p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                  >
                    <Checkbox
                      checked={false}
                      onCheckedChange={() => onToggleGoal(goal.id)}
                    />
                    <span className="flex-1 text-sm">{goal.text}</span>
                    <button
                      type="button"
                      onClick={() => onRemoveGoal(goal.id)}
                      className="p-1 rounded hover:bg-destructive/20 text-muted-foreground hover:text-destructive transition-colors"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Completed Goals */}
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
              {t('registry.completedGoals')}
            </h3>
            {completedGoals.length === 0 ? (
              <p className="text-sm text-muted-foreground italic p-3 bg-muted/30 rounded-lg">
                {t('registry.noCompletedGoals')}
              </p>
            ) : (
              <ul className="space-y-2">
                {completedGoals.map((goal) => (
                  <li
                    key={goal.id}
                    className="flex items-center gap-3 p-3 rounded-lg bg-green-50 dark:bg-green-950/20"
                  >
                    <Check className="h-4 w-4 text-green-600" />
                    <span className="flex-1 text-sm text-green-700 dark:text-green-400 line-through">
                      {goal.text}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
