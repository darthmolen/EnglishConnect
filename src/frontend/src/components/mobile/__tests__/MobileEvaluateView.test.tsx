import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MobileEvaluateView } from '../content/MobileEvaluateView'

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback: string) => fallback,
  }),
}))

describe('MobileEvaluateView', () => {
  const mockEvaluationCriteria = [
    { criterion: 'I can greet someone in English', criterion_es: 'Puedo saludar a alguien en inglés' },
    { criterion: 'I can introduce myself', criterion_es: 'Puedo presentarme' },
    { criterion: 'I can ask for someone\'s name', criterion_es: 'Puedo preguntar el nombre de alguien' },
    { criterion: 'I can respond to a greeting', criterion_es: 'Puedo responder a un saludo' },
  ]

  it('renders evaluation criteria as checklist items with translations', () => {
    render(
      <MobileEvaluateView evaluationCriteria={mockEvaluationCriteria} />
    )

    // English text
    expect(screen.getByText('I can greet someone in English')).toBeInTheDocument()
    expect(screen.getByText('I can introduce myself')).toBeInTheDocument()
    expect(screen.getByText('I can ask for someone\'s name')).toBeInTheDocument()
    expect(screen.getByText('I can respond to a greeting')).toBeInTheDocument()
    // Spanish translations
    expect(screen.getByText('(Puedo saludar a alguien en inglés)')).toBeInTheDocument()
    expect(screen.getByText('(Puedo presentarme)')).toBeInTheDocument()

    // Should have checkboxes
    const checkboxes = screen.getAllByRole('checkbox')
    expect(checkboxes.length).toBe(4)
  })

  it('shows empty state when no criteria', () => {
    render(
      <MobileEvaluateView evaluationCriteria={[]} />
    )

    expect(screen.getByText(/no evaluation/i)).toBeInTheDocument()
  })
})
