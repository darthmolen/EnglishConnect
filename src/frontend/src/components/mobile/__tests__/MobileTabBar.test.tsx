import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MobileTabBar } from '../MobileTabBar'

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback: string) => fallback,
  }),
}))

describe('MobileTabBar', () => {
  const mockOnTabChange = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders 3 tabs: Lessons, Learn, Me', () => {
    render(<MobileTabBar activeTab="lessons" onTabChange={mockOnTabChange} />)

    expect(screen.getByRole('tab', { name: /lessons/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /learn/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /me/i })).toBeInTheDocument()
  })

  it('highlights the active tab with aria-selected', () => {
    render(<MobileTabBar activeTab="learn" onTabChange={mockOnTabChange} />)

    const learnTab = screen.getByRole('tab', { name: /learn/i })
    expect(learnTab).toHaveAttribute('aria-selected', 'true')

    const lessonsTab = screen.getByRole('tab', { name: /lessons/i })
    expect(lessonsTab).toHaveAttribute('aria-selected', 'false')
  })

  it('calls onTabChange with "lessons" when Lessons tab is clicked', () => {
    render(<MobileTabBar activeTab="learn" onTabChange={mockOnTabChange} />)

    fireEvent.click(screen.getByRole('tab', { name: /lessons/i }))
    expect(mockOnTabChange).toHaveBeenCalledWith('lessons')
  })

  it('calls onTabChange with "learn" when Learn tab is clicked', () => {
    render(<MobileTabBar activeTab="lessons" onTabChange={mockOnTabChange} />)

    fireEvent.click(screen.getByRole('tab', { name: /learn/i }))
    expect(mockOnTabChange).toHaveBeenCalledWith('learn')
  })

  it('calls onTabChange with "me" when Me tab is clicked', () => {
    render(<MobileTabBar activeTab="lessons" onTabChange={mockOnTabChange} />)

    fireEvent.click(screen.getByRole('tab', { name: /me/i }))
    expect(mockOnTabChange).toHaveBeenCalledWith('me')
  })

  it('has touch-friendly tap targets (min 44px)', () => {
    render(<MobileTabBar activeTab="lessons" onTabChange={mockOnTabChange} />)

    const tabs = screen.getAllByRole('tab')
    tabs.forEach(tab => {
      // Check that min-h-[56px] class is applied (which is > 44px)
      expect(tab).toHaveClass('min-h-[56px]')
    })
  })
})
