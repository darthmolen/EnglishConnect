import { CompactVocabulary } from './CompactVocabulary'
import { DemoPlayer } from './DemoPlayer'
import { PatternsView } from './PatternsView'
import type { VocabularyItem, QAPattern, PhaseState } from '@/types'

interface PracticeViewProps {
  vocabulary: VocabularyItem[]
  patterns: QAPattern[]
  patternImages: string[]
  isPatternPhase?: boolean
  patternIndex?: number
  phaseState?: PhaseState | null
  courseId?: string
  lessonNumber?: number
}

export function PracticeView({
  vocabulary,
  patterns,
  patternImages,
  isPatternPhase = false,
  patternIndex = 0,
  phaseState,
  courseId = 'ec1',
  lessonNumber,
}: PracticeViewProps) {
  const hasVocabulary = vocabulary.length > 0
  const hasPatterns = patterns.length > 0

  if (!hasVocabulary && !hasPatterns) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <p>No practice content available for this lesson</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Compact vocabulary bar at top */}
      {hasVocabulary && (
        <CompactVocabulary vocabulary={vocabulary} />
      )}

      {/* Demo player for pre-recorded audio examples */}
      {lessonNumber && (
        <DemoPlayer courseId={courseId} lessonNumber={lessonNumber} />
      )}

      {/* Patterns section fills remaining space */}
      {hasPatterns && (
        <div className="flex-1 overflow-y-auto">
          <PatternsView
            patterns={patterns}
            patternImages={patternImages}
            lessonNumber={lessonNumber}
            isPatternPhase={isPatternPhase}
            patternIndex={patternIndex}
            phaseState={phaseState}
          />
        </div>
      )}
    </div>
  )
}
