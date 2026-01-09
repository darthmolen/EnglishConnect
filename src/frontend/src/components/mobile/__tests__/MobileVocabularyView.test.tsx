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
  const mockVocabulary = [
    { id: 1, word: 'hello', translation: 'hola', category: 'greetings' },
    { id: 2, word: 'goodbye', translation: 'adiós', category: 'greetings' },
    { id: 3, word: 'book', translation: 'libro', category: 'objects' },
  ]

  const mockOnPlayWord = vi.fn()
  const mockOnSelectWord = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders vocabulary cards', () => {
    render(
      <MobileVocabularyView
        vocabulary={mockVocabulary}
        currentIndex={0}
        onPlayWord={mockOnPlayWord}
        onSelectWord={mockOnSelectWord}
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
        onSelectWord={mockOnSelectWord}
      />
    )

    // The second card (goodbye) should be highlighted
    const goodbyeCard = screen.getByText('goodbye').closest('button')
    expect(goodbyeCard).toHaveClass('ring-2')
  })

  it('calls onPlayWord when play button is clicked', () => {
    render(
      <MobileVocabularyView
        vocabulary={mockVocabulary}
        currentIndex={0}
        onPlayWord={mockOnPlayWord}
        onSelectWord={mockOnSelectWord}
      />
    )

    const playButtons = screen.getAllByRole('button', { name: /play/i })
    fireEvent.click(playButtons[0])
    expect(mockOnPlayWord).toHaveBeenCalledWith(0)
  })

  it('calls onSelectWord when card is tapped', () => {
    render(
      <MobileVocabularyView
        vocabulary={mockVocabulary}
        currentIndex={0}
        onPlayWord={mockOnPlayWord}
        onSelectWord={mockOnSelectWord}
      />
    )

    const bookCard = screen.getByText('book').closest('button')
    fireEvent.click(bookCard!)
    expect(mockOnSelectWord).toHaveBeenCalledWith(2)
  })

  it('shows empty state when no vocabulary', () => {
    render(
      <MobileVocabularyView
        vocabulary={[]}
        currentIndex={0}
        onPlayWord={mockOnPlayWord}
        onSelectWord={mockOnSelectWord}
      />
    )

    expect(screen.getByText(/no vocabulary/i)).toBeInTheDocument()
  })
})
