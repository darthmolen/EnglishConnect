// src/frontend/src/components/auth/SignUpForm.tsx
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { authSignup } from '@/services/api'

interface SignUpFormProps {
  onSignInClick: () => void
  onSuccess: () => void
}

export function SignUpForm({ onSignInClick, onSuccess }: SignUpFormProps) {
  const { t } = useTranslation()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validate required fields
    if (!email || !password || !confirmPassword) {
      setError(t('auth.errors.fieldsRequired'))
      return
    }

    // Validate password match
    if (password !== confirmPassword) {
      setError(t('auth.errors.passwordMismatch'))
      return
    }

    // Validate password strength (at least 8 characters)
    if (password.length < 8) {
      setError(t('auth.errors.passwordTooShort'))
      return
    }

    setIsLoading(true)

    try {
      await authSignup({
        email,
        password,
        confirm_password: confirmPassword,
        first_name: firstName || undefined,
        last_name: lastName || undefined,
      })
      onSuccess()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="w-full max-w-sm space-y-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold">{t('auth.signUpTitle')}</h1>
        <p className="mt-2 text-sm text-muted-foreground">{t('auth.signUpSubtitle')}</p>
      </div>

      {error && (
        <div className="rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="firstName" className="block text-sm font-medium">
              {t('auth.firstName')}
            </label>
            <input
              id="firstName"
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              className="mt-1 block w-full rounded-lg border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder={t('auth.firstNamePlaceholder')}
              disabled={isLoading}
              autoComplete="given-name"
            />
          </div>
          <div>
            <label htmlFor="lastName" className="block text-sm font-medium">
              {t('auth.lastName')}
            </label>
            <input
              id="lastName"
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              className="mt-1 block w-full rounded-lg border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder={t('auth.lastNamePlaceholder')}
              disabled={isLoading}
              autoComplete="family-name"
            />
          </div>
        </div>

        <div>
          <label htmlFor="signupEmail" className="block text-sm font-medium">
            {t('auth.email')} <span className="text-destructive">*</span>
          </label>
          <input
            id="signupEmail"
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

        <div>
          <label htmlFor="signupPassword" className="block text-sm font-medium">
            {t('auth.password')} <span className="text-destructive">*</span>
          </label>
          <input
            id="signupPassword"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full rounded-lg border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder={t('auth.passwordPlaceholder')}
            disabled={isLoading}
            autoComplete="new-password"
            required
          />
          <p className="mt-1 text-xs text-muted-foreground">{t('auth.passwordHint')}</p>
        </div>

        <div>
          <label htmlFor="confirmPassword" className="block text-sm font-medium">
            {t('auth.confirmPassword')} <span className="text-destructive">*</span>
          </label>
          <input
            id="confirmPassword"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="mt-1 block w-full rounded-lg border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder={t('auth.confirmPasswordPlaceholder')}
            disabled={isLoading}
            autoComplete="new-password"
            required
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full rounded-lg bg-primary px-4 py-2 text-primary-foreground font-medium transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isLoading ? t('auth.creatingAccount') : t('auth.signUpButton')}
        </button>

        <p className="text-center text-sm text-muted-foreground">
          {t('auth.alreadyHaveAccount')}{' '}
          <button
            type="button"
            onClick={onSignInClick}
            className="text-primary hover:underline"
          >
            {t('auth.signInLink')}
          </button>
        </p>
      </form>
    </div>
  )
}
