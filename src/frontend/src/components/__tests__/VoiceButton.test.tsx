import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { VoiceButton } from '../VoiceButton'

describe('VoiceButton', () => {
  const defaultProps = {
    isRecording: false,
    isPlaying: false,
    onStartRecording: vi.fn(),
    onStopRecording: vi.fn(),
  }

  it('renders microphone icon when not recording', () => {
    render(<VoiceButton {...defaultProps} />)
    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  it('shows recording state styling when isRecording is true', () => {
    render(<VoiceButton {...defaultProps} isRecording={true} />)
    const button = screen.getByRole('button')
    expect(button).toHaveClass('bg-destructive')
  })

  it('shows default styling when not recording', () => {
    render(<VoiceButton {...defaultProps} />)
    const button = screen.getByRole('button')
    expect(button).not.toHaveClass('bg-destructive')
  })

  it('calls onStartRecording on mouseDown', () => {
    const onStartRecording = vi.fn()
    render(<VoiceButton {...defaultProps} onStartRecording={onStartRecording} />)
    fireEvent.mouseDown(screen.getByRole('button'))
    expect(onStartRecording).toHaveBeenCalledTimes(1)
  })

  it('calls onStopRecording on mouseUp', () => {
    const onStopRecording = vi.fn()
    render(<VoiceButton {...defaultProps} isRecording={true} onStopRecording={onStopRecording} />)
    fireEvent.mouseUp(screen.getByRole('button'))
    expect(onStopRecording).toHaveBeenCalledTimes(1)
  })

  it('calls onStopRecording when mouse leaves while recording', () => {
    const onStopRecording = vi.fn()
    render(<VoiceButton {...defaultProps} isRecording={true} onStopRecording={onStopRecording} />)
    fireEvent.mouseLeave(screen.getByRole('button'))
    expect(onStopRecording).toHaveBeenCalledTimes(1)
  })

  it('calls onStartRecording on touchStart', () => {
    const onStartRecording = vi.fn()
    render(<VoiceButton {...defaultProps} onStartRecording={onStartRecording} />)
    fireEvent.touchStart(screen.getByRole('button'))
    expect(onStartRecording).toHaveBeenCalledTimes(1)
  })

  it('calls onStopRecording on touchEnd', () => {
    const onStopRecording = vi.fn()
    render(<VoiceButton {...defaultProps} isRecording={true} onStopRecording={onStopRecording} />)
    fireEvent.touchEnd(screen.getByRole('button'))
    expect(onStopRecording).toHaveBeenCalledTimes(1)
  })

  it('is disabled when isPlaying is true', () => {
    render(<VoiceButton {...defaultProps} isPlaying={true} />)
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
  })

  it('is not disabled when isPlaying is false', () => {
    render(<VoiceButton {...defaultProps} />)
    const button = screen.getByRole('button')
    expect(button).not.toBeDisabled()
  })

  it('does not call onStartRecording when disabled', () => {
    const onStartRecording = vi.fn()
    render(<VoiceButton {...defaultProps} onStartRecording={onStartRecording} disabled={true} />)
    fireEvent.mouseDown(screen.getByRole('button'))
    expect(onStartRecording).not.toHaveBeenCalled()
  })

  it('handles keyboard Space to start/stop recording', () => {
    const onStartRecording = vi.fn()
    const onStopRecording = vi.fn()
    render(
      <VoiceButton
        {...defaultProps}
        onStartRecording={onStartRecording}
        onStopRecording={onStopRecording}
      />
    )
    const button = screen.getByRole('button')
    fireEvent.keyDown(button, { key: ' ' })
    expect(onStartRecording).toHaveBeenCalledTimes(1)
  })
})
