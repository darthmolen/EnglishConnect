// src/frontend/src/components/auth/PasswordResetForm.tsx
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { requestPasswordReset } from '@/services/api'
import { Mail } from 'lucide-react'

interface PasswordResetFormProps {
  onBackToSignIn: () => void
}

export function PasswordResetForm({ onBackToSignIn }: PasswordResetFormProps) {
  const { t } = useTranslation()

  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!email) return

    setIsLoading(true)

    try {
      await requestPasswordReset(email)
      setIsSubmitted(true)
    } finally {
      setIsLoading(false)
    }
  }

  if (isSubmitted) {
    return (
      <div className="w-full max-w-sm space-y-6 text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
          <Mail className="h-8 w-8 text-primary" />
        </div>

        <div>
          <h1 className="text-2xl font-bold">{t('auth.resetEmailSentTitle')}</h1>
          <p className="mt-2 text-sm text-muted-foreground">{t('auth.resetEmailSentMessage')}</p>
        </div>

        <button
          type="button"
          onClick={onBackToSignIn}
          className="text-sm text-primary hover:underline"
        >
          {t('auth.backToSignIn')}
        </button>
      </div>
    )
  }

  return (
    <div className="w-full max-w-sm space-y-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold">{t('auth.resetPasswordTitle')}</h1>
        <p className="mt-2 text-sm text-muted-foreground">{t('auth.resetPasswordSubtitle')}</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="resetEmail" className="block text-sm font-medium">
            {t('auth.email')}
          </label>
          <input
            id="resetEmail"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full rounded-lg border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder={t('auth.emailPlaceholder')}
            disabled={isLoading}
            autoComplete="email"
            required
          />
        </div>

        <button
          type="submit"
          disabled={isLoading || !email}
          className="w-full rounded-lg bg-primary px-4 py-2 text-primary-foreground font-medium transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isLoading ? t('auth.sendingEmail') : t('auth.sendResetLink')}
        </button>

        <button
          type="button"
          onClick={onBackToSignIn}
          className="w-full text-sm text-muted-foreground hover:text-foreground"
        >
          {t('auth.backToSignIn')}
        </button>
      </form>
    </div>
  )
}
