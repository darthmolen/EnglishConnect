import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Plus, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { PersonalGoal, StudyRegistryStatus, StudyRegistryItem, EvaluationCriterion } from '@/types'

const EMOJI_RATINGS = ['😢', '😕', '😐', '🙂', '😊', '🤩']

const STUDY_REGISTRY_ITEMS: StudyRegistryItem[] = [
  'studiedPrinciples',
  'memorizedVocabulary',
  'practicedPatterns',
  'dailyPractice',
]

interface EvaluateViewProps {
  lessonNumber: number
  criteria: EvaluationCriterion[]
  evaluationRatings: Record<number, number>
  personalGoals: PersonalGoal[]
  studyRegistry: Partial<Record<StudyRegistryItem, StudyRegistryStatus>>
  onSetRating: (criterionIndex: number, rating: number) => void
  onAddGoal: (text: string) => void
  onRemoveGoal: (goalId: string) => void
  onSetStudyStatus: (item: StudyRegistryItem, status: StudyRegistryStatus) => void
}

export function EvaluateView({
  criteria,
  evaluationRatings,
  personalGoals,
  studyRegistry,
  onSetRating,
  onAddGoal,
  onRemoveGoal,
  onSetStudyStatus,
}: EvaluateViewProps) {
  const { t } = useTranslation()
  const [newGoalText, setNewGoalText] = useState('')

  const handleAddGoal = () => {
    if (newGoalText.trim()) {
      onAddGoal(newGoalText.trim())
      setNewGoalText('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleAddGoal()
    }
  }

  return (
    <div className="p-4 space-y-6 overflow-y-auto">
      {/* Section 1: Self Assessment */}
      <section className="space-y-3">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            {t('evaluate.selfAssessment')}
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            {t('evaluate.selfAssessmentHint')}
          </p>
        </div>

        {criteria.length === 0 ? (
          <p className="text-sm text-muted-foreground italic">
            {t('goals.empty')}
          </p>
        ) : (
          <div className="space-y-3">
            {criteria.map((item, index) => (
              <div key={index} className="space-y-2 p-3 rounded-lg bg-muted/30">
                <div>
                  <p className="text-sm">{item.criterion}</p>
                  {item.criterion_es && (
                    <p className="text-sm text-muted-foreground italic">({item.criterion_es})</p>
                  )}
                </div>
                <div className="flex gap-1">
                  {EMOJI_RATINGS.map((emoji, rating) => (
                    <button
                      key={rating}
                      type="button"
                      onClick={() => onSetRating(index, rating)}
                      className={cn(
                        'w-10 h-10 text-xl rounded-lg transition-all',
                        'hover:bg-accent hover:scale-110',
                        evaluationRatings[index] === rating
                          ? 'bg-primary/20 ring-2 ring-primary scale-110'
                          : 'bg-muted/50'
                      )}
                      title={`${rating}/5`}
                    >
                      {emoji}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Section 2: Personal Goals */}
      <section className="space-y-3">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            {t('evaluate.personalGoals')}
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            {t('evaluate.personalGoalsHint')}
          </p>
        </div>

        {/* Add goal input */}
        <div className="flex gap-2">
          <input
            type="text"
            value={newGoalText}
            onChange={(e) => setNewGoalText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t('evaluate.addGoalPlaceholder')}
            className="flex-1 px-3 py-2 text-sm rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <button
            type="button"
            onClick={handleAddGoal}
            disabled={!newGoalText.trim()}
            className={cn(
              'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
              'bg-primary text-primary-foreground hover:bg-primary/90',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>

        {/* Goals list */}
        {personalGoals.length === 0 ? (
          <p className="text-sm text-muted-foreground italic">
            {t('evaluate.noGoals')}
          </p>
        ) : (
          <ul className="space-y-2">
            {personalGoals.filter(g => !g.completed).map((goal) => (
              <li
                key={goal.id}
                className="flex items-center justify-between p-3 rounded-lg bg-muted/30"
              >
                <span className="text-sm">{goal.text}</span>
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
      </section>

      {/* Section 3: Study Registry */}
      <section className="space-y-3">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            {t('evaluate.studyRegistry')}
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            {t('evaluate.studyRegistryHint')}
          </p>
        </div>

        <div className="space-y-2">
          {STUDY_REGISTRY_ITEMS.map((item) => {
            const currentStatus = studyRegistry[item]
            return (
              <div
                key={item}
                className="flex items-center justify-between p-3 rounded-lg bg-muted/30"
              >
                <span className="text-sm">{t(`evaluate.${item}`)}</span>
                <div className="flex gap-1">
                  {(['red', 'yellow', 'green'] as StudyRegistryStatus[]).map(
                    (status) => (
                      <button
                        key={status}
                        type="button"
                        onClick={() => onSetStudyStatus(item, status)}
                        className={cn(
                          'w-8 h-8 rounded-full text-lg transition-all',
                          'hover:scale-110',
                          currentStatus === status && 'ring-2 ring-offset-2',
                          status === 'red' && 'bg-red-500',
                          status === 'yellow' && 'bg-yellow-400',
                          status === 'green' && 'bg-green-500',
                          currentStatus === status && status === 'red' && 'ring-red-500',
                          currentStatus === status && status === 'yellow' && 'ring-yellow-400',
                          currentStatus === status && status === 'green' && 'ring-green-500',
                          // Grey for unset status (none selected)
                          !currentStatus && 'opacity-50'
                        )}
                        title={t(`status.${status}`)}
                      />
                    )
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </section>
    </div>
  )
}
