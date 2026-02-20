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
  const mockOnLogin = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders pattern cards', () => {
    render(
      <MobilePracticeView
        patterns={mockPatterns}
        currentIndex={0}
        isAuthenticated={true}
        onLogin={mockOnLogin}
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
        isAuthenticated={true}
        onLogin={mockOnLogin}
        onSelectPattern={mockOnSelectPattern}
        onStartPractice={mockOnStartPractice}
      />
    )

    // The card is a div with role="button"
    const patternCard = screen.getByText('Where are you from?').closest('[role="button"]')
    expect(patternCard).toHaveClass('ring-2')
  })

  it('calls onStartPractice when practice button is clicked and authenticated', () => {
    render(
      <MobilePracticeView
        patterns={mockPatterns}
        currentIndex={0}
        isAuthenticated={true}
        onLogin={mockOnLogin}
        onSelectPattern={mockOnSelectPattern}
        onStartPractice={mockOnStartPractice}
      />
    )

    const practiceButton = screen.getAllByText('Practice')[0]
    fireEvent.click(practiceButton)
    expect(mockOnStartPractice).toHaveBeenCalledWith(1)
    expect(mockOnLogin).not.toHaveBeenCalled()
  })

  it('shows sign-in text when not authenticated', () => {
    render(
      <MobilePracticeView
        patterns={mockPatterns}
        currentIndex={0}
        isAuthenticated={false}
        onLogin={mockOnLogin}
        onSelectPattern={mockOnSelectPattern}
        onStartPractice={mockOnStartPractice}
      />
    )

    const signInButtons = screen.getAllByText('Sign in to Practice')
    expect(signInButtons.length).toBeGreaterThan(0)
  })

  it('calls onLogin instead of onStartPractice when not authenticated', () => {
    render(
      <MobilePracticeView
        patterns={mockPatterns}
        currentIndex={0}
        isAuthenticated={false}
        onLogin={mockOnLogin}
        onSelectPattern={mockOnSelectPattern}
        onStartPractice={mockOnStartPractice}
      />
    )

    const signInButton = screen.getAllByText('Sign in to Practice')[0]
    fireEvent.click(signInButton)
    expect(mockOnLogin).toHaveBeenCalled()
    expect(mockOnStartPractice).not.toHaveBeenCalled()
  })

  it('shows empty state when no patterns', () => {
    render(
      <MobilePracticeView
        patterns={[]}
        currentIndex={0}
        isAuthenticated={true}
        onLogin={mockOnLogin}
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
        isAuthenticated={true}
        onLogin={mockOnLogin}
        onSelectPattern={mockOnSelectPattern}
        onStartPractice={mockOnStartPractice}
      />
    )

    // The looping pattern card should have animate-pulse class
    const firstPatternCard = screen.getByText('What is your name?').closest('[role="button"]')
    expect(firstPatternCard).toHaveClass('animate-pulse')
  })
})
