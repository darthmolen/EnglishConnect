import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MobileChatOverlay } from '../MobileChatOverlay'

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback: string) => fallback,
  }),
}))

describe('MobileChatOverlay', () => {
  const mockMessages = [
    { id: '1', role: 'assistant' as const, content: 'Hello! Ready to practice?' },
    { id: '2', role: 'user' as const, content: 'Yes, I am ready.' },
  ]

  const mockOnClose = vi.fn()
  const mockOnToggleRecording = vi.fn()
  const mockOnToggleVoiceMode = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders when isOpen is true', () => {
    render(
      <MobileChatOverlay
        isOpen={true}
        onClose={mockOnClose}
        messages={mockMessages}
        pinnedCard={{ title: 'Pattern 1', content: 'What is your name?' }}
        isRecording={false}
        voiceMode="push-to-talk"
        onToggleRecording={mockOnToggleRecording}
        onToggleVoiceMode={mockOnToggleVoiceMode}
      />
    )

    expect(screen.getByText('Hello! Ready to practice?')).toBeInTheDocument()
    expect(screen.getByText('Yes, I am ready.')).toBeInTheDocument()
  })

  it('does not render when isOpen is false', () => {
    render(
      <MobileChatOverlay
        isOpen={false}
        onClose={mockOnClose}
        messages={mockMessages}
        pinnedCard={{ title: 'Pattern 1', content: 'What is your name?' }}
        isRecording={false}
        voiceMode="push-to-talk"
        onToggleRecording={mockOnToggleRecording}
        onToggleVoiceMode={mockOnToggleVoiceMode}
      />
    )

    expect(screen.queryByText('Hello! Ready to practice?')).not.toBeInTheDocument()
  })

  it('shows pinned context card', () => {
    render(
      <MobileChatOverlay
        isOpen={true}
        onClose={mockOnClose}
        messages={mockMessages}
        pinnedCard={{ title: 'Pattern 1', content: 'What is your name?' }}
        isRecording={false}
        voiceMode="push-to-talk"
        onToggleRecording={mockOnToggleRecording}
        onToggleVoiceMode={mockOnToggleVoiceMode}
      />
    )

    expect(screen.getByText('Pattern 1')).toBeInTheDocument()
    expect(screen.getByText('What is your name?')).toBeInTheDocument()
  })

  it('calls onClose when close button is clicked', () => {
    render(
      <MobileChatOverlay
        isOpen={true}
        onClose={mockOnClose}
        messages={mockMessages}
        pinnedCard={{ title: 'Pattern 1', content: 'What is your name?' }}
        isRecording={false}
        voiceMode="push-to-talk"
        onToggleRecording={mockOnToggleRecording}
        onToggleVoiceMode={mockOnToggleVoiceMode}
      />
    )

    const closeButton = screen.getByRole('button', { name: /close/i })
    fireEvent.click(closeButton)
    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('calls onToggleRecording when mic button is clicked', () => {
    render(
      <MobileChatOverlay
        isOpen={true}
        onClose={mockOnClose}
        messages={mockMessages}
        pinnedCard={{ title: 'Pattern 1', content: 'What is your name?' }}
        isRecording={false}
        voiceMode="push-to-talk"
        onToggleRecording={mockOnToggleRecording}
        onToggleVoiceMode={mockOnToggleVoiceMode}
      />
    )

    const micButton = screen.getByRole('button', { name: /microphone/i })
    fireEvent.click(micButton)
    expect(mockOnToggleRecording).toHaveBeenCalledTimes(1)
  })

  it('shows recording state when isRecording is true', () => {
    render(
      <MobileChatOverlay
        isOpen={true}
        onClose={mockOnClose}
        messages={mockMessages}
        pinnedCard={{ title: 'Pattern 1', content: 'What is your name?' }}
        isRecording={true}
        voiceMode="push-to-talk"
        onToggleRecording={mockOnToggleRecording}
        onToggleVoiceMode={mockOnToggleVoiceMode}
      />
    )

    const micButton = screen.getByRole('button', { name: /microphone/i })
    expect(micButton).toHaveClass('bg-destructive')
  })
})
