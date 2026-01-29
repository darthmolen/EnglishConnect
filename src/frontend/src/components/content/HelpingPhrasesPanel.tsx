/**
 * Panel displaying helping phrases that students can use during practice.
 *
 * These phrases allow students to request assistance in their native language
 * (e.g., "No entiendo" in Spanish) and trigger the help recovery flow.
 */

import { useTranslation } from 'react-i18next'
import { HelpCircle } from 'lucide-react'
import type { HelpingPhrase, InstructionLanguage } from '@/types'
import { cn } from '@/lib/utils'

interface HelpingPhrasesPanelProps {
  phrases: HelpingPhrase[]
  instructionLanguage: InstructionLanguage
  className?: string
}

export function HelpingPhrasesPanel({
  phrases,
  instructionLanguage,
  className,
}: HelpingPhrasesPanelProps) {
  const { t } = useTranslation()

  if (!phrases.length) {
    return null
  }

  return (
    <div
      className={cn(
        'rounded-lg border bg-amber-50 dark:bg-amber-950/30 p-3',
        className
      )}
    >
      <div className="flex items-center gap-2 mb-2">
        <HelpCircle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
        <h4 className="font-semibold text-sm text-amber-900 dark:text-amber-100">
          {t('practice.helpPhrases', {
            defaultValue:
              instructionLanguage === 'es' ? 'Frases de ayuda' : 'Help Phrases',
          })}
        </h4>
      </div>
      <p className="text-xs text-amber-700 dark:text-amber-300 mb-2">
        {instructionLanguage === 'es'
          ? 'Di estas frases si necesitas ayuda:'
          : 'Say these phrases if you need help:'}
      </p>
      <ul className="space-y-1">
        {phrases.map((phrase) => (
          <li key={phrase.phrase_key} className="text-sm flex items-baseline gap-2">
            <span className="font-medium text-amber-900 dark:text-amber-100">
              "{phrase.phrase_text}"
            </span>
            <span className="text-amber-600 dark:text-amber-400 text-xs">
              ({phrase.english_meaning})
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
