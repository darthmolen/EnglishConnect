import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { VoiceButton } from '../VoiceButton'

describe('VoiceButton', () => {
  it('renders microphone icon when not recording', () => {
    render(<VoiceButton isRecording={false} isPlaying={false} onPress={vi.fn()} />)
    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  it('shows recording state styling when isRecording is true', () => {
    render(<VoiceButton isRecording={true} isPlaying={false} onPress={vi.fn()} />)
    const button = screen.getByRole('button')
    expect(button).toHaveClass('bg-destructive')
  })

  it('shows default styling when not recording', () => {
    render(<VoiceButton isRecording={false} isPlaying={false} onPress={vi.fn()} />)
    const button = screen.getByRole('button')
    expect(button).not.toHaveClass('bg-destructive')
  })

  it('calls onPress when clicked', () => {
    const handlePress = vi.fn()
    render(<VoiceButton isRecording={false} isPlaying={false} onPress={handlePress} />)
    fireEvent.click(screen.getByRole('button'))
    expect(handlePress).toHaveBeenCalledTimes(1)
  })

  it('is disabled when isPlaying is true', () => {
    render(<VoiceButton isRecording={false} isPlaying={true} onPress={vi.fn()} />)
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
  })

  it('is not disabled when isPlaying is false', () => {
    render(<VoiceButton isRecording={false} isPlaying={false} onPress={vi.fn()} />)
    const button = screen.getByRole('button')
    expect(button).not.toBeDisabled()
  })
})
