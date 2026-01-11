import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import type { EvaluationCriterion } from '@/types'

interface MobilePrincipleViewProps {
  lessonNumber: number
  principleTitle: string | null
  principleContent: string | null
  principleFull: string | null
  ponderQuestions: string[]
  evaluationCriteria: EvaluationCriterion[]
}

export function MobilePrincipleView({
  lessonNumber,
  principleTitle,
  principleContent,
  principleFull,
  ponderQuestions,
  evaluationCriteria,
}: MobilePrincipleViewProps) {
  const { t } = useTranslation()

  // No principle content at all
  const hasContent = principleTitle || principleContent || principleFull
  if (!hasContent) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground p-4">
        {t('mobile.principle.noContent', 'No principle content available')}
      </div>
    )
  }

  // Prefer full content over short content
  const displayContent = principleFull || principleContent

  return (
    <div className="space-y-6">
      {/* Principle Section */}
      <div>
        {principleTitle && (
          <h3 className="text-lg font-semibold text-primary border-b pb-2 mb-4">
            {principleTitle}
          </h3>
        )}
        {displayContent && (
          <div className="space-y-4">
            {displayContent.split('\n\n').map((paragraph, i) => (
              <p
                key={i}
                className={cn(
                  'text-sm leading-relaxed text-muted-foreground',
                  'first-letter:text-lg first-letter:font-medium first-letter:text-foreground'
                )}
              >
                {paragraph}
              </p>
            ))}
          </div>
        )}
      </div>

      {/* Ponder Questions */}
      {ponderQuestions.length > 0 && (
        <div className="rounded-lg bg-primary/5 p-4 border border-primary/20">
          <h4 className="text-sm font-semibold uppercase tracking-wide text-primary mb-3">
            {t('mobile.principle.ponderTitle', 'Reflect')}{' '}
            <span className="font-normal normal-case text-muted-foreground">
              {t('mobile.principle.ponderTitleAlt', '(Reflexiona)')}
            </span>
          </h4>
          <ul className="space-y-2">
            {ponderQuestions.map((question, index) => (
              <li key={index} className="flex items-start gap-2 text-sm text-muted-foreground">
                <span className="text-primary font-bold">?</span>
                <span>{question}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Metas Section (only if evaluation criteria exist) */}
      {evaluationCriteria.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-base font-semibold">
            {t('mobile.principle.metasTitle', { number: lessonNumber })}{' '}
            <span className="font-normal text-sm text-muted-foreground">
              {t('mobile.principle.metasTitleAlt', { number: lessonNumber })}
            </span>
          </h4>
          <ul className="space-y-3">
            {evaluationCriteria.map((item, index) => (
              <li key={index} className="flex items-start gap-2 text-sm">
                <span className="text-primary mt-0.5">•</span>
                <div>
                  <div>{item.criterion}</div>
                  {item.criterion_es && (
                    <div className="text-muted-foreground italic">({item.criterion_es})</div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
