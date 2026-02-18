import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MobileChatOverlay } from '../MobileChatOverlay'

// Mock i18next — return fallback if provided, otherwise the key
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: string) => fallback ?? key,
  }),
}))

describe('MobileChatOverlay', () => {
  const mockMessages = [
    { id: '1', role: 'assistant' as const, content: 'Hello! Ready to practice?' },
    { id: '2', role: 'user' as const, content: 'Yes, I am ready.' },
  ]

  const mockOnClose = vi.fn()
  const mockOnStartRecording = vi.fn()
  const mockOnStopRecording = vi.fn()
  const mockOnToggleVoiceMode = vi.fn()

  const defaultProps = {
    isOpen: true,
    onClose: mockOnClose,
    messages: mockMessages,
    pinnedCard: { title: 'Pattern 1', content: 'What is your name?' } as { title: string; content: string } | null,
    isRecording: false,
    isPlaying: false,
    voiceMode: 'push-to-talk' as const,
    onStartRecording: mockOnStartRecording,
    onStopRecording: mockOnStopRecording,
    onToggleVoiceMode: mockOnToggleVoiceMode,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders when isOpen is true', () => {
    render(<MobileChatOverlay {...defaultProps} />)

    expect(screen.getByText('Hello! Ready to practice?')).toBeInTheDocument()
    expect(screen.getByText('Yes, I am ready.')).toBeInTheDocument()
  })

  it('does not render when isOpen is false', () => {
    render(<MobileChatOverlay {...defaultProps} isOpen={false} />)

    expect(screen.queryByText('Hello! Ready to practice?')).not.toBeInTheDocument()
  })

  it('shows pinned context card', () => {
    render(<MobileChatOverlay {...defaultProps} />)

    expect(screen.getByText('Pattern 1')).toBeInTheDocument()
    expect(screen.getByText('What is your name?')).toBeInTheDocument()
  })

  it('calls onClose when close button is clicked', () => {
    render(<MobileChatOverlay {...defaultProps} />)

    const closeButton = screen.getByRole('button', { name: /end session/i })
    fireEvent.click(closeButton)
    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  // PTT behavior tests
  it('calls onStartRecording on mouseDown of mic button', () => {
    render(<MobileChatOverlay {...defaultProps} />)

    const micButton = screen.getByRole('button', { name: /voice\.holdToTalk/i })
    fireEvent.mouseDown(micButton)
    expect(mockOnStartRecording).toHaveBeenCalledTimes(1)
  })

  it('calls onStopRecording on mouseUp of mic button when recording', () => {
    render(<MobileChatOverlay {...defaultProps} isRecording={true} />)

    const micButton = screen.getByRole('button', { name: /voice\.recording/i })
    fireEvent.mouseUp(micButton)
    expect(mockOnStopRecording).toHaveBeenCalledTimes(1)
  })

  it('calls onStartRecording on touchStart of mic button', () => {
    render(<MobileChatOverlay {...defaultProps} />)

    const micButton = screen.getByRole('button', { name: /voice\.holdToTalk/i })
    fireEvent.touchStart(micButton)
    expect(mockOnStartRecording).toHaveBeenCalledTimes(1)
  })

  it('calls onStopRecording on touchEnd of mic button when recording', () => {
    render(<MobileChatOverlay {...defaultProps} isRecording={true} />)

    const micButton = screen.getByRole('button', { name: /voice\.recording/i })
    fireEvent.touchEnd(micButton)
    expect(mockOnStopRecording).toHaveBeenCalledTimes(1)
  })

  it('shows recording state when isRecording is true', () => {
    render(<MobileChatOverlay {...defaultProps} isRecording={true} />)

    const micButton = screen.getByRole('button', { name: /voice\.recording/i })
    expect(micButton).toHaveClass('bg-destructive')
  })
})
