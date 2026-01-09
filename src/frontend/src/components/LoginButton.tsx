// src/frontend/src/components/LoginButton.tsx
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'

export function LoginButton() {
  const { t } = useTranslation()
  const { isLoading } = useAuthStore()

  const handleClick = () => {
    window.location.hash = '#/login'
  }

  return (
    <button
      onClick={handleClick}
      disabled={isLoading}
      className="rounded-lg bg-primary px-6 py-3 text-primary-foreground font-medium transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
    >
      {isLoading ? t('auth.signingIn') : t('auth.signInButton')}
    </button>
  )
}
