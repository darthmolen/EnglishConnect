import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import type { LessonDetail, LessonSection, PersonalGoal, StudyRegistryStatus, StudyRegistryItem } from '@/types'
import { PrincipleView } from './content/PrincipleView'
import { GoalsView } from './content/GoalsView'
import { PracticeView } from './content/PracticeView'
import type { PatternAction } from './content/PatternsView'
import { VocabularyView } from './content/VocabularyView'
import { EvaluateView } from './content/EvaluateView'

interface ContentWindowProps {
  lesson: LessonDetail | null
  activeSection: LessonSection | null
  completedGoals: number[]
  onToggleGoal: (lessonNumber: number, goalIndex: number) => void
  onStartConversation?: () => void
  onPatternAction?: (action: PatternAction) => void
  className?: string
  // Evaluation props
  evaluationRatings: Record<number, number>
  personalGoals: PersonalGoal[]
  studyRegistry: Partial<Record<StudyRegistryItem, StudyRegistryStatus>>
  onSetEvaluationRating: (criterionIndex: number, rating: number) => void
  onAddPersonalGoal: (text: string) => void
  onRemovePersonalGoal: (goalId: string) => void
  onSetStudyRegistryStatus: (item: StudyRegistryItem, status: StudyRegistryStatus) => void
}

export function ContentWindow({
  lesson,
  activeSection,
  completedGoals,
  onToggleGoal,
  onStartConversation,
  onPatternAction,
  className,
  evaluationRatings,
  personalGoals,
  studyRegistry,
  onSetEvaluationRating,
  onAddPersonalGoal,
  onRemovePersonalGoal,
  onSetStudyRegistryStatus,
}: ContentWindowProps) {
  const { t } = useTranslation()

  if (!lesson) {
    return (
      <div className={cn('flex items-center justify-center bg-muted/30', className)}>
        <div className="text-center text-muted-foreground">
          <p className="text-lg font-medium">{t('lessons.selectLesson')}</p>
          <p className="text-sm">{t('lessons.selectLessonHint')}</p>
        </div>
      </div>
    )
  }

  return (
    <div className={cn('overflow-y-auto bg-background', className)}>
      {activeSection === 'principle' && (
        <PrincipleView
          title={lesson.learning_principle_title}
          content={lesson.learning_principle_content}
          fullContent={lesson.learning_principle_full}
          ponderQuestions={lesson.ponder_questions}
        />
      )}
      {activeSection === 'goals' && (
        <GoalsView
          lessonNumber={lesson.lesson_number}
          criteria={lesson.evaluation_criteria}
          completedGoals={completedGoals}
          onToggleGoal={onToggleGoal}
        />
      )}
      {activeSection === 'practice' && (
        <PracticeView
          vocabulary={lesson.vocabulary}
          patterns={lesson.patterns}
          patternImages={lesson.pattern_images}
          lessonNumber={lesson.lesson_number}
          onStartConversation={onStartConversation}
          onPatternAction={onPatternAction}
        />
      )}
      {activeSection === 'vocabulary' && (
        <VocabularyView
          vocabulary={lesson.vocabulary}
          lessonNumber={lesson.lesson_number}
        />
      )}
      {activeSection === 'evaluate' && (
        <EvaluateView
          lessonNumber={lesson.lesson_number}
          criteria={lesson.evaluation_criteria}
          evaluationRatings={evaluationRatings}
          personalGoals={personalGoals}
          studyRegistry={studyRegistry}
          onSetRating={onSetEvaluationRating}
          onAddGoal={onAddPersonalGoal}
          onRemoveGoal={onRemovePersonalGoal}
          onSetStudyStatus={onSetStudyRegistryStatus}
        />
      )}
    </div>
  )
}
