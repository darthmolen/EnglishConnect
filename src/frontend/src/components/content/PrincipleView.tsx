import { cn } from '@/lib/utils'

interface PrincipleViewProps {
  title: string | null
  content: string | null
  fullContent: string | null
  ponderQuestions: string[]
}

export function PrincipleView({
  title,
  content,
  fullContent,
  ponderQuestions,
}: PrincipleViewProps) {
  const displayContent = fullContent || content

  if (!title && !displayContent && ponderQuestions.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <p>No learning principle available for this lesson</p>
      </div>
    )
  }

  return (
    <div className="p-4 space-y-6">
      {/* Title */}
      {title && (
        <h3 className="text-lg font-semibold text-primary border-b pb-2">
          {title}
        </h3>
      )}

      {/* Content with CSS columns for wider screens */}
      {displayContent && (
        <div className="columns-1 md:columns-2 gap-6">
          {displayContent.split('\n\n').map((paragraph, i) => (
            <p
              key={i}
              className={cn(
                'mb-4 text-sm leading-relaxed break-inside-avoid',
                'first-letter:text-lg first-letter:font-medium'
              )}
            >
              {paragraph}
            </p>
          ))}
        </div>
      )}

      {/* Ponder Questions */}
      {ponderQuestions.length > 0 && (
        <div className="rounded-lg bg-primary/5 p-4 border border-primary/20">
          <h4 className="text-sm font-semibold uppercase tracking-wide text-primary mb-3">
            Ponder
          </h4>
          <ul className="space-y-2">
            {ponderQuestions.map((question, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-sm text-muted-foreground"
              >
                <span className="text-primary font-bold">?</span>
                <span>{question}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
