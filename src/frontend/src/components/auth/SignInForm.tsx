// src/frontend/src/components/auth/SignInForm.tsx
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'

interface SignInFormProps {
  onSignUpClick: () => void
  onForgotPasswordClick: () => void
}

export function SignInForm({ onSignUpClick, onForgotPasswordClick }: SignInFormProps) {
  const { t } = useTranslation()
  const { loginLocal, loginAzureAd, isLoading, error, setError, isAzureAdEnabled, isLocalAuthEnabled } =
    useAuthStore()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!email || !password) {
      setError(t('auth.errors.fieldsRequired'))
      return
    }

    try {
      await loginLocal({ email, password })
      // Redirect to home on successful login
      window.location.hash = '#/'
    } catch {
      // Error is already set in the store
    }
  }

  const handleAzureAdLogin = () => {
    loginAzureAd()
  }

  return (
    <div className="w-full max-w-sm space-y-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold">{t('auth.signInTitle')}</h1>
        <p className="mt-2 text-sm text-muted-foreground">{t('auth.signInSubtitle')}</p>
      </div>

      {error && (
        <div className="rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {isLocalAuthEnabled() && (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium">
              {t('auth.email')}
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full rounded-lg border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder={t('auth.emailPlaceholder')}
              disabled={isLoading}
              autoComplete="email"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium">
              {t('auth.password')}
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full rounded-lg border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder={t('auth.passwordPlaceholder')}
              disabled={isLoading}
              autoComplete="current-password"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded-lg bg-primary px-4 py-2 text-primary-foreground font-medium transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading ? t('auth.signingIn') : t('auth.signInButton')}
          </button>

          <div className="flex justify-between text-sm">
            <button
              type="button"
              onClick={onForgotPasswordClick}
              className="text-primary hover:underline"
            >
              {t('auth.forgotPassword')}
            </button>
            <button
              type="button"
              onClick={onSignUpClick}
              className="text-primary hover:underline"
            >
              {t('auth.createAccount')}
            </button>
          </div>
        </form>
      )}

      {isAzureAdEnabled() && isLocalAuthEnabled() && (
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-background px-2 text-muted-foreground">{t('auth.or')}</span>
          </div>
        </div>
      )}

      {isAzureAdEnabled() && (
        <button
          type="button"
          onClick={handleAzureAdLogin}
          disabled={isLoading}
          className="w-full rounded-lg border bg-background px-4 py-2 font-medium transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
        >
          {t('auth.signInWithMicrosoft')}
        </button>
      )}
    </div>
  )
}
