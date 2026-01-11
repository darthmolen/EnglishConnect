import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MobilePatternsOverview } from '../content/MobilePatternsOverview'
import type { QAPattern } from '@/types'

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback: string) => fallback,
  }),
}))

describe('MobilePatternsOverview', () => {
  const mockPatterns: QAPattern[] = [
    {
      pattern_number: 1,
      question_template: 'What is your name?',
      question_translation: '¿Cómo te llamas?',
      answer_template: 'My name is ___.',
      answer_translation: 'Me llamo ___.',
      examples: [{ q: 'What is your name?', a: 'My name is John.' }],
    },
    {
      pattern_number: 2,
      question_template: 'How are you?',
      question_translation: '¿Cómo estás?',
      answer_template: 'I am fine, thank you.',
      answer_translation: 'Estoy bien, gracias.',
      examples: [{ q: 'How are you?', a: 'I am fine.' }],
    },
  ]

  const mockOnPlayPattern = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders pattern cards with number badges', () => {
    render(
      <MobilePatternsOverview
        patterns={mockPatterns}
        playingPattern={null}
        onPlayPattern={mockOnPlayPattern}
      />
    )

    // Should show pattern numbers as badges
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('renders question/answer templates with translations', () => {
    render(
      <MobilePatternsOverview
        patterns={mockPatterns}
        playingPattern={null}
        onPlayPattern={mockOnPlayPattern}
      />
    )

    // Question templates
    expect(screen.getByText('What is your name?')).toBeInTheDocument()
    expect(screen.getByText('How are you?')).toBeInTheDocument()

    // Translations
    expect(screen.getByText('¿Cómo te llamas?')).toBeInTheDocument()
    expect(screen.getByText('¿Cómo estás?')).toBeInTheDocument()

    // Answer templates
    expect(screen.getByText('My name is ___.')).toBeInTheDocument()
    expect(screen.getByText('I am fine, thank you.')).toBeInTheDocument()
  })

  it('calls onPlayPattern with pattern number when play clicked', () => {
    render(
      <MobilePatternsOverview
        patterns={mockPatterns}
        playingPattern={null}
        onPlayPattern={mockOnPlayPattern}
      />
    )

    const playButtons = screen.getAllByRole('button', { name: /play/i })
    fireEvent.click(playButtons[0])
    expect(mockOnPlayPattern).toHaveBeenCalledWith(1)

    fireEvent.click(playButtons[1])
    expect(mockOnPlayPattern).toHaveBeenCalledWith(2)
  })

  it('shows playing state for currently playing pattern', () => {
    render(
      <MobilePatternsOverview
        patterns={mockPatterns}
        playingPattern={1}
        onPlayPattern={mockOnPlayPattern}
      />
    )

    // Pattern 1 should show pause/stop indicator
    const playButtons = screen.getAllByRole('button', { name: /stop|pause/i })
    expect(playButtons.length).toBeGreaterThan(0)
  })

  it('shows empty state when no patterns', () => {
    render(
      <MobilePatternsOverview
        patterns={[]}
        playingPattern={null}
        onPlayPattern={mockOnPlayPattern}
      />
    )

    expect(screen.getByText(/no patterns/i)).toBeInTheDocument()
  })
})
