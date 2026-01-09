import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MobilePracticeView } from '../content/MobilePracticeView'

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback: string) => fallback,
  }),
}))

describe('MobilePracticeView', () => {
  // Using actual QAPattern type from types/index.ts
  const mockPatterns = [
    {
      pattern_number: 1,
      question_template: 'What is your name?',
      question_translation: '¿Cómo te llamas?',
      answer_template: 'My name is _____.',
      answer_translation: 'Me llamo _____.',
      examples: null,
    },
    {
      pattern_number: 2,
      question_template: 'Where are you from?',
      question_translation: '¿De dónde eres?',
      answer_template: 'I am from _____.',
      answer_translation: 'Soy de _____.',
      examples: null,
    },
  ]

  const mockOnSelectPattern = vi.fn()
  const mockOnStartPractice = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders pattern cards', () => {
    render(
      <MobilePracticeView
        patterns={mockPatterns}
        currentIndex={0}
        onSelectPattern={mockOnSelectPattern}
        onStartPractice={mockOnStartPractice}
      />
    )

    expect(screen.getByText('What is your name?')).toBeInTheDocument()
    expect(screen.getByText('My name is _____.')).toBeInTheDocument()
  })

  it('highlights current pattern card', () => {
    render(
      <MobilePracticeView
        patterns={mockPatterns}
        currentIndex={1}
        onSelectPattern={mockOnSelectPattern}
        onStartPractice={mockOnStartPractice}
      />
    )

    // The card is a div with role="button"
    const patternCard = screen.getByText('Where are you from?').closest('[role="button"]')
    expect(patternCard).toHaveClass('ring-2')
  })

  it('calls onStartPractice when practice button is clicked', () => {
    render(
      <MobilePracticeView
        patterns={mockPatterns}
        currentIndex={0}
        onSelectPattern={mockOnSelectPattern}
        onStartPractice={mockOnStartPractice}
      />
    )

    // Find the first practice button by its text
    const practiceButton = screen.getAllByText('Practice')[0]
    fireEvent.click(practiceButton)
    expect(mockOnStartPractice).toHaveBeenCalledWith(1) // pattern_number 1
  })

  it('shows empty state when no patterns', () => {
    render(
      <MobilePracticeView
        patterns={[]}
        currentIndex={0}
        onSelectPattern={mockOnSelectPattern}
        onStartPractice={mockOnStartPractice}
      />
    )

    expect(screen.getByText(/no patterns/i)).toBeInTheDocument()
  })

  it('shows looping indicator when pattern is being played', () => {
    render(
      <MobilePracticeView
        patterns={mockPatterns}
        currentIndex={0}
        loopingPattern={1}
        onSelectPattern={mockOnSelectPattern}
        onStartPractice={mockOnStartPractice}
      />
    )

    // The looping pattern card should have animate-pulse class
    const firstPatternCard = screen.getByText('What is your name?').closest('[role="button"]')
    expect(firstPatternCard).toHaveClass('animate-pulse')
  })
})
