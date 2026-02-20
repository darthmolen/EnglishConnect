import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ConversationDrawer } from '../ConversationDrawer'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: string) => fallback || key,
  }),
}))

describe('ConversationDrawer', () => {
  const defaultProps = {
    isOpen: false,
    onToggle: vi.fn(),
    onEndSession: vi.fn(),
    messages: [] as { role: 'user' | 'assistant'; content: string }[],
    isLoading: false,
  }

  it('renders transcript toggle button when authenticated', () => {
    render(<ConversationDrawer {...defaultProps} isAuthenticated={true} />)
    expect(screen.getByText('conversation.transcript')).toBeInTheDocument()
  })

  it('hides transcript toggle button when not authenticated', () => {
    render(<ConversationDrawer {...defaultProps} isAuthenticated={false} />)
    expect(screen.queryByText('conversation.transcript')).not.toBeInTheDocument()
  })
})
