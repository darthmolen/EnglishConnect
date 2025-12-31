import { useTranslation } from 'react-i18next'
import { Mic, Square, Volume2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface VoiceButtonProps {
  isRecording: boolean
  isPlaying: boolean
  onPress: () => void
  disabled?: boolean
}

export function VoiceButton({
  isRecording,
  isPlaying,
  onPress,
  disabled = false,
}: VoiceButtonProps) {
  const { t } = useTranslation()
  const isDisabled = disabled || isPlaying

  return (
    <button
      type="button"
      onClick={onPress}
      disabled={isDisabled}
      className={cn(
        'flex h-16 w-16 items-center justify-center rounded-full transition-all',
        'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        isRecording
          ? 'bg-destructive text-destructive-foreground animate-pulse'
          : 'bg-primary text-primary-foreground hover:bg-primary/90',
        isDisabled && 'opacity-50 cursor-not-allowed'
      )}
      aria-label={isRecording ? t('voice.stopRecording') : t('voice.startRecording')}
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
