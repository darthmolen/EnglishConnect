// src/frontend/src/pages/LoginPage.tsx
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { SignInForm } from '@/components/auth/SignInForm'
import { SignUpForm } from '@/components/auth/SignUpForm'
import { PendingApproval } from '@/components/auth/PendingApproval'
import { PasswordResetForm } from '@/components/auth/PasswordResetForm'
import { useAuthStore } from '@/stores/authStore'

type AuthView = 'signIn' | 'signUp' | 'pending' | 'forgotPassword'

export function LoginPage() {
  const { t, i18n } = useTranslation()
  const { isLocalAuthEnabled } = useAuthStore()
  const [view, setView] = useState<AuthView>('signIn')

  const handleSignUpSuccess = () => {
    setView('pending')
  }

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Language selector in header */}
      <header className="flex items-center justify-end p-4">
        <select
          value={i18n.language}
          onChange={(e) => i18n.changeLanguage(e.target.value)}
          className="rounded-md border bg-background px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="es">Español</option>
          <option value="en">English</option>
        </select>
      </header>

      {/* Main content */}
      <main className="flex flex-1 flex-col items-center justify-center px-4">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-primary">{t('app.title')}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t('auth.welcomeMessage')}</p>
        </div>

        {view === 'signIn' && (
          <SignInForm
            onSignUpClick={() => setView('signUp')}
            onForgotPasswordClick={() => setView('forgotPassword')}
          />
        )}

        {view === 'signUp' && isLocalAuthEnabled() && (
          <SignUpForm
            onSignInClick={() => setView('signIn')}
            onSuccess={handleSignUpSuccess}
          />
        )}

        {view === 'pending' && (
          <PendingApproval onBackToSignIn={() => setView('signIn')} />
        )}

        {view === 'forgotPassword' && (
          <PasswordResetForm onBackToSignIn={() => setView('signIn')} />
        )}
      </main>

      {/* Footer */}
      <footer className="p-4 text-center text-xs text-muted-foreground">
        <p>{t('auth.footerText')}</p>
      </footer>
    </div>
  )
}
