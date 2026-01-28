import { useCallback, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Mic, Square, Volume2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface VoiceButtonProps {
  isRecording: boolean
  isPlaying: boolean
  onStartRecording: () => void
  onStopRecording: () => void
  disabled?: boolean
  title?: string
}

export function VoiceButton({
  isRecording,
  isPlaying,
  onStartRecording,
  onStopRecording,
  disabled = false,
  title,
}: VoiceButtonProps) {
  const { t } = useTranslation()
  const isDisabled = disabled || isPlaying
  const buttonRef = useRef<HTMLButtonElement>(null)
  const isRecordingRef = useRef(isRecording)
  const isDisabledRef = useRef(isDisabled)
  const onStartRef = useRef(onStartRecording)
  const onStopRef = useRef(onStopRecording)

  // Keep refs in sync with props for use in native event handlers
  useEffect(() => { isRecordingRef.current = isRecording }, [isRecording])
  useEffect(() => { isDisabledRef.current = isDisabled }, [isDisabled])
  useEffect(() => { onStartRef.current = onStartRecording }, [onStartRecording])
  useEffect(() => { onStopRef.current = onStopRecording }, [onStopRecording])

  // Stop recording when mouse/touch leaves the button while held
  const handlePointerLeave = useCallback(() => {
    if (isRecordingRef.current) {
      onStopRecording()
    }
  }, [onStopRecording])

  // Stop recording if page loses focus while recording
  useEffect(() => {
    const handleBlur = () => {
      if (isRecordingRef.current) {
        onStopRecording()
      }
    }

    window.addEventListener('blur', handleBlur)
    return () => window.removeEventListener('blur', handleBlur)
  }, [onStopRecording])

  // Handle keyboard accessibility (Space/Enter to hold)
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (isDisabled) return
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault()
        if (!isRecordingRef.current) {
          onStartRecording()
        }
      }
    },
    [isDisabled, onStartRecording]
  )

  const handleKeyUp = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault()
        if (isRecordingRef.current) {
          onStopRecording()
        }
      }
    },
    [onStopRecording]
  )

  // Handle mouse events
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (isDisabled) return
      e.preventDefault()
      onStartRecording()
    },
    [isDisabled, onStartRecording]
  )

  const handleMouseUp = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      if (isRecordingRef.current) {
        onStopRecording()
      }
    },
    [onStopRecording]
  )

  // Non-passive touch event listeners (attached via ref to allow preventDefault)
  // React registers touch handlers as passive by default, which blocks preventDefault.
  // We need preventDefault to stop synthetic mouse events from firing after touch.
  useEffect(() => {
    const button = buttonRef.current
    if (!button) return

    const onTouchStart = (e: TouchEvent) => {
      if (isDisabledRef.current) return
      e.preventDefault()
      onStartRef.current()
    }

    const onTouchEnd = (e: TouchEvent) => {
      e.preventDefault()
      if (isRecordingRef.current) {
        onStopRef.current()
      }
    }

    const onTouchCancel = () => {
      if (isRecordingRef.current) {
        onStopRef.current()
      }
    }

    button.addEventListener('touchstart', onTouchStart, { passive: false })
    button.addEventListener('touchend', onTouchEnd, { passive: false })
    button.addEventListener('touchcancel', onTouchCancel)

    return () => {
      button.removeEventListener('touchstart', onTouchStart)
      button.removeEventListener('touchend', onTouchEnd)
      button.removeEventListener('touchcancel', onTouchCancel)
    }
  }, [])

  return (
    <button
      ref={buttonRef}
      type="button"
      disabled={isDisabled}
      title={title || t('voice.holdToTalk')}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      onMouseLeave={handlePointerLeave}
      onKeyDown={handleKeyDown}
      onKeyUp={handleKeyUp}
      className={cn(
        'flex h-16 w-16 items-center justify-center rounded-full transition-all select-none touch-none',
        'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        isRecording
          ? 'bg-destructive text-destructive-foreground animate-pulse'
          : 'bg-primary text-primary-foreground hover:bg-primary/90',
        isDisabled && 'opacity-50 cursor-not-allowed'
      )}
      aria-label={isRecording ? t('voice.recording') : t('voice.holdToTalk')}
    >
      {isPlaying ? (
        <Volume2 className="h-8 w-8 animate-pulse" />
      ) : isRecording ? (
        <Square className="h-6 w-6" />
      ) : (
        <Mic className="h-8 w-8" />
      )}
    </button>
  )
}
