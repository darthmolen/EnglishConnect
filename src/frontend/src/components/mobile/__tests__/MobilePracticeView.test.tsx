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
  const mockPatterns = [
    {
      id: 1,
      pattern_number: 1,
      question_template: 'What is your name?',
      answer_template: 'My name is _____.',
    },
    {
      id: 2,
      pattern_number: 2,
      question_template: 'Where are you from?',
      answer_template: 'I am from _____.',
    },
  ]

  const mockOnPlayPattern = vi.fn()
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
        onPlayPattern={mockOnPlayPattern}
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
        onPlayPattern={mockOnPlayPattern}
        onSelectPattern={mockOnSelectPattern}
        onStartPractice={mockOnStartPractice}
      />
    )

    const patternCard = screen.getByText('Where are you from?').closest('button')
    expect(patternCard).toHaveClass('ring-2')
  })

  it('calls onPlayPattern when play button is clicked', () => {
    render(
      <MobilePracticeView
        patterns={mockPatterns}
        currentIndex={0}
        onPlayPattern={mockOnPlayPattern}
        onSelectPattern={mockOnSelectPattern}
        onStartPractice={mockOnStartPractice}
      />
    )

    const playButtons = screen.getAllByRole('button', { name: /play/i })
    fireEvent.click(playButtons[0])
    expect(mockOnPlayPattern).toHaveBeenCalledWith(0)
  })

  it('shows empty state when no patterns', () => {
    render(
      <MobilePracticeView
        patterns={[]}
        currentIndex={0}
        onPlayPattern={mockOnPlayPattern}
        onSelectPattern={mockOnSelectPattern}
        onStartPractice={mockOnStartPractice}
      />
    )

    expect(screen.getByText(/no patterns/i)).toBeInTheDocument()
  })
})
