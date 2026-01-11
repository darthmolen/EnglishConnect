import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MobilePrincipleView } from '../content/MobilePrincipleView'

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallbackOrOptions?: string | { number?: number }) => {
      if (typeof fallbackOrOptions === 'string') return fallbackOrOptions
      if (typeof fallbackOrOptions === 'object' && fallbackOrOptions.number) {
        // Return Spanish translation for Alt keys
        if (key.endsWith('Alt')) {
          return `(Metas de Lección ${fallbackOrOptions.number})`
        }
        return `Goals for Lesson ${fallbackOrOptions.number}`
      }
      // Handle Alt keys without number param
      if (key === 'mobile.principle.ponderTitleAlt') return '(Reflexiona)'
      return key
    },
  }),
}))

describe('MobilePrincipleView', () => {
  const mockPrinciple = {
    title: 'Practice Makes Perfect',
    content: 'The more you practice, the better you become.',
    full: 'Learning a language requires consistent practice. The more you practice speaking, listening, reading, and writing, the more natural it becomes.',
  }

  const mockPonderQuestions = [
    'How can I practice English every day?',
    'What opportunities do I have to speak English?',
  ]

  const mockEvaluationCriteria = [
    { criterion: 'I can greet someone in English', criterion_es: 'Puedo saludar a alguien en inglés' },
    { criterion: 'I can introduce myself', criterion_es: 'Puedo presentarme' },
    { criterion: 'I can ask for someone\'s name', criterion_es: 'Puedo preguntar el nombre de alguien' },
  ]

  it('renders principle title and content', () => {
    render(
      <MobilePrincipleView
        lessonNumber={1}
        principleTitle={mockPrinciple.title}
        principleContent={mockPrinciple.content}
        principleFull={mockPrinciple.full}
        ponderQuestions={[]}
        evaluationCriteria={[]}
      />
    )

    expect(screen.getByText('Practice Makes Perfect')).toBeInTheDocument()
    // Should prefer full content over short content
    expect(screen.getByText(/Learning a language requires consistent practice/)).toBeInTheDocument()
  })

  it('falls back to content when full is not available', () => {
    render(
      <MobilePrincipleView
        lessonNumber={1}
        principleTitle={mockPrinciple.title}
        principleContent={mockPrinciple.content}
        principleFull={null}
        ponderQuestions={[]}
        evaluationCriteria={[]}
      />
    )

    expect(screen.getByText(/The more you practice, the better you become/)).toBeInTheDocument()
  })

  it('renders ponder questions in styled box', () => {
    render(
      <MobilePrincipleView
        lessonNumber={1}
        principleTitle={mockPrinciple.title}
        principleContent={mockPrinciple.content}
        principleFull={mockPrinciple.full}
        ponderQuestions={mockPonderQuestions}
        evaluationCriteria={[]}
      />
    )

    expect(screen.getByText('How can I practice English every day?')).toBeInTheDocument()
    expect(screen.getByText('What opportunities do I have to speak English?')).toBeInTheDocument()
  })

  it('renders metas section with lesson number header', () => {
    render(
      <MobilePrincipleView
        lessonNumber={3}
        principleTitle={mockPrinciple.title}
        principleContent={mockPrinciple.content}
        principleFull={mockPrinciple.full}
        ponderQuestions={[]}
        evaluationCriteria={mockEvaluationCriteria}
      />
    )

    // Header should include lesson number
    expect(screen.getByText('Goals for Lesson 3')).toBeInTheDocument()
  })

  it('renders evaluation criteria as list items with translations', () => {
    render(
      <MobilePrincipleView
        lessonNumber={1}
        principleTitle={mockPrinciple.title}
        principleContent={mockPrinciple.content}
        principleFull={mockPrinciple.full}
        ponderQuestions={[]}
        evaluationCriteria={mockEvaluationCriteria}
      />
    )

    // English text
    expect(screen.getByText('I can greet someone in English')).toBeInTheDocument()
    expect(screen.getByText('I can introduce myself')).toBeInTheDocument()
    expect(screen.getByText('I can ask for someone\'s name')).toBeInTheDocument()
    // Spanish translations
    expect(screen.getByText('(Puedo saludar a alguien en inglés)')).toBeInTheDocument()
    expect(screen.getByText('(Puedo presentarme)')).toBeInTheDocument()
    expect(screen.getByText('(Puedo preguntar el nombre de alguien)')).toBeInTheDocument()
  })

  it('shows empty state when no principle content', () => {
    render(
      <MobilePrincipleView
        lessonNumber={1}
        principleTitle={null}
        principleContent={null}
        principleFull={null}
        ponderQuestions={[]}
        evaluationCriteria={[]}
      />
    )

    expect(screen.getByText(/no principle/i)).toBeInTheDocument()
  })

  it('does not render metas section when no evaluation criteria', () => {
    render(
      <MobilePrincipleView
        lessonNumber={1}
        principleTitle={mockPrinciple.title}
        principleContent={mockPrinciple.content}
        principleFull={mockPrinciple.full}
        ponderQuestions={mockPonderQuestions}
        evaluationCriteria={[]}
      />
    )

    // Principle content should be there
    expect(screen.getByText('Practice Makes Perfect')).toBeInTheDocument()
    // But no metas header
    expect(screen.queryByText(/Goals for Lesson/)).not.toBeInTheDocument()
  })
})
