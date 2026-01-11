import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { EvaluationCriterion } from '@/types'

interface MobileEvaluateViewProps {
  evaluationCriteria: EvaluationCriterion[]
}

export function MobileEvaluateView({ evaluationCriteria }: MobileEvaluateViewProps) {
  const { t } = useTranslation()
  const [checkedItems, setCheckedItems] = useState<Set<number>>(new Set())

  if (evaluationCriteria.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground p-4">
        {t('mobile.evaluate.empty', 'No evaluation criteria available')}
      </div>
    )
  }

  const toggleItem = (index: number) => {
    setCheckedItems((prev) => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">
        {t('mobile.evaluate.selfAssessment', 'Self-Assessment')}
      </h3>
      <p className="text-sm text-muted-foreground">
        {t('mobile.evaluate.instructions', 'Check off each skill you feel confident with.')}
      </p>
      <ul className="space-y-3">
        {evaluationCriteria.map((item, index) => (
          <li key={index} className="flex items-start gap-3">
            <input
              type="checkbox"
              id={`criterion-${index}`}
              checked={checkedItems.has(index)}
              onChange={() => toggleItem(index)}
              className="mt-1 h-5 w-5 rounded border-2 border-primary text-primary focus:ring-primary"
            />
            <label
              htmlFor={`criterion-${index}`}
              className="flex-1 cursor-pointer"
            >
              <div className="text-sm">{item.criterion}</div>
              {item.criterion_es && (
                <div className="text-sm text-muted-foreground italic">({item.criterion_es})</div>
              )}
            </label>
          </li>
        ))}
      </ul>
      <div className="text-sm text-muted-foreground text-center pt-4">
        {checkedItems.size} / {evaluationCriteria.length} {t('mobile.evaluate.completed', 'completed')}
      </div>
    </div>
  )
}
