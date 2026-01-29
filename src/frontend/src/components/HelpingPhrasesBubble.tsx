/**
 * Chat bubble displaying helping phrases at the start of a conversation.
 *
 * Shows phrases the student can use to request assistance during practice.
 * Rendered as a special system bubble that scrolls with the conversation.
 */

import { HelpCircle } from 'lucide-react'
import type { HelpingPhrase, InstructionLanguage } from '@/types'

interface HelpingPhrasesBubbleProps {
  phrases: HelpingPhrase[]
  instructionLanguage: InstructionLanguage
}

export function HelpingPhrasesBubble({
  phrases,
  instructionLanguage,
}: HelpingPhrasesBubbleProps) {
  if (!phrases.length) {
    return null
  }

  const title = instructionLanguage === 'es' ? 'Frases de ayuda' : 'Help Phrases'
  const subtitle =
    instructionLanguage === 'es'
      ? 'Di estas frases si necesitas ayuda:'
      : 'Say these phrases if you need help:'

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] rounded-2xl rounded-bl-md bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 px-4 py-3">
        <div className="flex items-center gap-2 mb-2">
          <HelpCircle className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0" />
          <span className="font-semibold text-sm text-amber-900 dark:text-amber-100">
            {title}
          </span>
        </div>
        <p className="text-xs text-amber-700 dark:text-amber-300 mb-2">
          {subtitle}
        </p>
        <ul className="space-y-1">
          {phrases.map((phrase) => (
            <li key={phrase.phrase_key} className="text-sm flex flex-wrap items-baseline gap-x-2">
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
    </div>
  )
}
