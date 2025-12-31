import { useTranslation } from 'react-i18next'
import { ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { LessonSection } from '@/types'

interface LessonSectionsProps {
  activeSection: LessonSection | null
  onSelectSection: (section: LessonSection) => void
  hasLesson: boolean
}

interface SectionButtonProps {
  title: string
  section: LessonSection
  isActive: boolean
  onClick: () => void
}

function SectionButton({ title, isActive, onClick }: SectionButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex w-full items-center justify-between px-4 py-3 text-left transition-colors',
        'hover:bg-accent/50 border-b',
        isActive && 'bg-primary/10 border-l-4 border-l-primary'
      )}
    >
      <span className={cn('font-medium', isActive && 'text-primary')}>
        {title}
      </span>
      <ChevronRight
        className={cn(
          'h-4 w-4 transition-transform',
          isActive && 'text-primary'
        )}
      />
    </button>
  )
}

const SECTION_IDS: LessonSection[] = ['principle', 'goals', 'vocabulary', 'practice']

export function LessonSections({
  activeSection,
  onSelectSection,
  hasLesson,
}: LessonSectionsProps) {
  const { t } = useTranslation()

  if (!hasLesson) {
    return (
      <div className="flex h-full items-center justify-center p-4 text-center text-muted-foreground">
        <p>{t('lessons.selectToView')}</p>
      </div>
    )
  }

  const sectionTitles: Record<LessonSection, string> = {
    principle: t('sections.principle'),
    goals: t('sections.goals'),
    vocabulary: t('sections.vocabulary'),
    practice: t('sections.practice'),
  }

  return (
    <div className="flex flex-col">
      <div className="border-b p-3">
        <h3 className="font-semibold text-sm uppercase tracking-wide text-muted-foreground">
          {t('lessons.sections')}
        </h3>
      </div>
      <nav className="flex flex-col">
        {SECTION_IDS.map((sectionId) => (
          <SectionButton
            key={sectionId}
            title={sectionTitles[sectionId]}
            section={sectionId}
            isActive={activeSection === sectionId}
            onClick={() => onSelectSection(sectionId)}
          />
        ))}
      </nav>
    </div>
  )
}
