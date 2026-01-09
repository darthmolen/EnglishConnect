import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MobileActionBar } from '../MobileActionBar'

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback: string) => fallback,
  }),
}))

describe('MobileActionBar', () => {
  const mockOnPlay = vi.fn()
  const mockOnNext = vi.fn()
  const mockOnChat = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders Play, Next, and Chat buttons', () => {
    render(
      <MobileActionBar
        section="vocabulary"
        onPlay={mockOnPlay}
        onNext={mockOnNext}
        onChat={mockOnChat}
      />
    )

    expect(screen.getByRole('button', { name: /play/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /chat/i })).toBeInTheDocument()
  })

  it('calls onPlay when Play button is clicked', () => {
    render(
      <MobileActionBar
        section="vocabulary"
        onPlay={mockOnPlay}
        onNext={mockOnNext}
        onChat={mockOnChat}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: /play/i }))
    expect(mockOnPlay).toHaveBeenCalledTimes(1)
  })

  it('calls onNext when Next button is clicked', () => {
    render(
      <MobileActionBar
        section="vocabulary"
        onPlay={mockOnPlay}
        onNext={mockOnNext}
        onChat={mockOnChat}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: /next/i }))
    expect(mockOnNext).toHaveBeenCalledTimes(1)
  })

  it('calls onChat when Chat button is clicked', () => {
    render(
      <MobileActionBar
        section="vocabulary"
        onPlay={mockOnPlay}
        onNext={mockOnNext}
        onChat={mockOnChat}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: /chat/i }))
    expect(mockOnChat).toHaveBeenCalledTimes(1)
  })

  it('disables Next and Chat on Principle section', () => {
    render(
      <MobileActionBar
        section="principle"
        onPlay={mockOnPlay}
        onNext={mockOnNext}
        onChat={mockOnChat}
      />
    )

    // Play enabled for TTS reading of principle
    expect(screen.getByRole('button', { name: /play/i })).not.toBeDisabled()
    // Next and Chat disabled
    expect(screen.getByRole('button', { name: /next/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /chat/i })).toBeDisabled()
  })

  it('enables all buttons on Vocabulary section', () => {
    render(
      <MobileActionBar
        section="vocabulary"
        onPlay={mockOnPlay}
        onNext={mockOnNext}
        onChat={mockOnChat}
      />
    )

    expect(screen.getByRole('button', { name: /play/i })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: /next/i })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: /chat/i })).not.toBeDisabled()
  })

  it('enables all buttons on Practice section', () => {
    render(
      <MobileActionBar
        section="practice"
        onPlay={mockOnPlay}
        onNext={mockOnNext}
        onChat={mockOnChat}
      />
    )

    expect(screen.getByRole('button', { name: /play/i })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: /next/i })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: /chat/i })).not.toBeDisabled()
  })
})
