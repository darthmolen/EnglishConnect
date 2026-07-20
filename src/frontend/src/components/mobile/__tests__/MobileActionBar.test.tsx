import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MobileActionBar } from '../MobileActionBar'
import type { ContentSection } from '../MobileActionBar'
import type { LoopMode } from '@/hooks/useSectionLoop'

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
  const mockOnLoop = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  function renderBar(
    props: {
      section?: ContentSection
      loopMode?: LoopMode
      chatDisabled?: boolean
      disabled?: boolean
    } = {}
  ) {
    const { section = 'vocabulary', loopMode = 'off', ...rest } = props
    return render(
      <MobileActionBar
        section={section}
        onPlay={mockOnPlay}
        onNext={mockOnNext}
        onChat={mockOnChat}
        onLoop={mockOnLoop}
        loopMode={loopMode}
        {...rest}
      />
    )
  }

  it('renders Play, Next, and Chat buttons', () => {
    renderBar()

    expect(screen.getByRole('button', { name: /play/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /chat/i })).toBeInTheDocument()
  })

  it('calls onPlay when Play button is clicked', () => {
    renderBar()

    fireEvent.click(screen.getByRole('button', { name: /play/i }))
    expect(mockOnPlay).toHaveBeenCalledTimes(1)
  })

  it('calls onNext when Next button is clicked', () => {
    renderBar()

    fireEvent.click(screen.getByRole('button', { name: /next/i }))
    expect(mockOnNext).toHaveBeenCalledTimes(1)
  })

  it('calls onChat when Chat button is clicked', () => {
    renderBar()

    fireEvent.click(screen.getByRole('button', { name: /chat/i }))
    expect(mockOnChat).toHaveBeenCalledTimes(1)
  })

  it('disables all buttons on Principle section', () => {
    renderBar({ section: 'principle' })

    // Principle section is for reading content - no audio playback
    expect(screen.getByRole('button', { name: /play/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /next/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /chat/i })).toBeDisabled()
  })

  it('disables chat button when chatDisabled is true', () => {
    renderBar({ chatDisabled: true })

    // Play and Next should work, Chat should be disabled (not authenticated)
    expect(screen.getByRole('button', { name: /play/i })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: /next/i })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: /chat/i })).toBeDisabled()
  })

  it('enables all buttons on Vocabulary section', () => {
    renderBar()

    expect(screen.getByRole('button', { name: /play/i })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: /next/i })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: /chat/i })).not.toBeDisabled()
  })

  it('enables all buttons on Practice section', () => {
    renderBar({ section: 'practice' })

    expect(screen.getByRole('button', { name: /play/i })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: /next/i })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: /chat/i })).not.toBeDisabled()
  })

  describe('loop button', () => {
    it('renders a fourth button for looping', () => {
      renderBar()

      expect(screen.getAllByRole('button')).toHaveLength(4)
      expect(screen.getByRole('button', { name: /loop/i })).toBeInTheDocument()
    })

    it('sits before Chat in the bar (Play, Next, Loop, Chat)', () => {
      renderBar()

      const labels = screen.getAllByRole('button').map(b => b.textContent)
      expect(labels).toEqual(['Play', 'Next', 'Loop', 'Chat'])
    })

    it('calls onLoop when clicked', () => {
      renderBar()

      fireEvent.click(screen.getByRole('button', { name: /loop/i }))
      expect(mockOnLoop).toHaveBeenCalledTimes(1)
    })

    it('shows "Loop" and is unpressed when off', () => {
      renderBar({ loopMode: 'off' })

      const button = screen.getByRole('button', { name: /loop/i })
      expect(button).toHaveTextContent('Loop')
      expect(button).toHaveAttribute('aria-pressed', 'false')
    })

    // "once" is gone: one tap loops everything, and the active control is a
    // Stop button so learners can end the loop without hunting for it.
    it('shows "Stop" and is pressed in all mode', () => {
      renderBar({ loopMode: 'all' })

      const button = screen.getByRole('button', { name: /stop/i })
      expect(button).toHaveTextContent('Stop')
      expect(button).toHaveAttribute('aria-pressed', 'true')
    })

    it('distinguishes looping from idle by icon, not colour alone', () => {
      // Colour-vision deficiency and bright sunlight both defeat colour-only
      // state. Idle uses the Repeat glyph; looping uses a Square (stop) glyph.
      const { container: offBar } = renderBar({ loopMode: 'off' })
      expect(offBar.querySelector('.lucide-repeat')).toBeInTheDocument()
      expect(offBar.querySelector('.lucide-square')).not.toBeInTheDocument()

      const { container: allBar } = renderBar({ loopMode: 'all' })
      expect(allBar.querySelector('.lucide-square')).toBeInTheDocument()
      expect(allBar.querySelector('.lucide-repeat')).not.toBeInTheDocument()
    })

    it('is enabled on the loopable sections', () => {
      for (const section of ['vocabulary', 'patterns', 'examples'] as ContentSection[]) {
        const { unmount } = renderBar({ section })
        expect(screen.getByRole('button', { name: /loop/i })).not.toBeDisabled()
        unmount()
      }
    })

    it('is disabled where there is no section audio to loop', () => {
      for (const section of ['principle', 'evaluate'] as ContentSection[]) {
        const { unmount } = renderBar({ section })
        expect(screen.getByRole('button', { name: /loop/i })).toBeDisabled()
        unmount()
      }
    })

    it('is disabled on Practice, which has its own per-pattern loop', () => {
      renderBar({ section: 'practice' })

      expect(screen.getByRole('button', { name: /loop/i })).toBeDisabled()
    })
  })
})
