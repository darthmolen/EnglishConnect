import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MobileVocabularyView } from '../content/MobileVocabularyView'

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback: string) => fallback,
  }),
}))

describe('MobileVocabularyView', () => {
  // Using actual VocabularyItem type from types/index.ts
  const mockVocabulary = [
    { english: 'hello', spanish: 'hola', category: 'greetings' },
    { english: 'goodbye', spanish: 'adiós', category: 'greetings' },
    { english: 'book', spanish: 'libro', category: 'objects' },
  ]

  const mockOnPlayWord = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders vocabulary cards', () => {
    render(
      <MobileVocabularyView
        vocabulary={mockVocabulary}
        currentIndex={0}
        onPlayWord={mockOnPlayWord}
      />
    )

    expect(screen.getByText('hello')).toBeInTheDocument()
    expect(screen.getByText('hola')).toBeInTheDocument()
  })

  it('highlights current word card', () => {
    render(
      <MobileVocabularyView
        vocabulary={mockVocabulary}
        currentIndex={1}
        onPlayWord={mockOnPlayWord}
      />
    )

    // The second card (goodbye) should be highlighted
    const goodbyeCard = screen.getByText('goodbye').closest('[role="button"]')
    expect(goodbyeCard).toHaveClass('ring-2')
  })

  it('calls onPlayWord when play button is clicked', () => {
    render(
      <MobileVocabularyView
        vocabulary={mockVocabulary}
        currentIndex={0}
        onPlayWord={mockOnPlayWord}
      />
    )

    const playButtons = screen.getAllByRole('button', { name: /play/i })
    fireEvent.click(playButtons[0])
    expect(mockOnPlayWord).toHaveBeenCalledWith(0)
  })

  it('calls onPlayWord when card is tapped (selects and plays)', () => {
    render(
      <MobileVocabularyView
        vocabulary={mockVocabulary}
        currentIndex={0}
        onPlayWord={mockOnPlayWord}
      />
    )

    const bookCard = screen.getByText('book').closest('[role="button"]')
    fireEvent.click(bookCard!)
    // Card click now calls onPlayWord (which handles both select and play)
    expect(mockOnPlayWord).toHaveBeenCalledWith(2)
  })

  it('shows empty state when no vocabulary', () => {
    render(
      <MobileVocabularyView
        vocabulary={[]}
        currentIndex={0}
        onPlayWord={mockOnPlayWord}
      />
    )

    expect(screen.getByText(/no vocabulary/i)).toBeInTheDocument()
  })
})
