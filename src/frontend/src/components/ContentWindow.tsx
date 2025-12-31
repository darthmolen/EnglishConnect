import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import type { LessonDetail, LessonSection, LessonPhase, PhaseState } from '@/types'
import { PrincipleView } from './content/PrincipleView'
import { GoalsView } from './content/GoalsView'
import { PracticeView } from './content/PracticeView'
import { VocabularyView } from './content/VocabularyView'

interface ContentWindowProps {
  lesson: LessonDetail | null
  activeSection: LessonSection | null
  currentPhase: LessonPhase | null
  phaseState: PhaseState | null
  completedGoals: number[]
  onToggleGoal: (lessonNumber: number, goalIndex: number) => void
  onPatternClick?: (patternIndex: number) => void
  onStartConversation?: () => void
  className?: string
}

export function ContentWindow({
  lesson,
  activeSection,
  currentPhase,
  phaseState,
  completedGoals,
  onToggleGoal,
  onPatternClick,
  onStartConversation,
  className,
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

  const vocabIndex = phaseState?.vocab_index ?? 0
  const patternIndex = phaseState?.pattern_index ?? 0
  const isVocabPhase = currentPhase?.phase_type === 'vocabulary'
  const isPatternPhase = currentPhase?.phase_type === 'patterns'

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
          isPatternPhase={isPatternPhase}
          patternIndex={patternIndex}
          phaseState={phaseState}
          lessonNumber={lesson.lesson_number}
          onPatternClick={onPatternClick}
          onStartConversation={onStartConversation}
        />
      )}
      {activeSection === 'vocabulary' && (
        <VocabularyView
          vocabulary={lesson.vocabulary}
          lessonNumber={lesson.lesson_number}
          isVocabPhase={isVocabPhase}
          vocabIndex={vocabIndex}
          phaseState={phaseState}
        />
      )}
    </div>
  )
}
