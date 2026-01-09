// src/frontend/src/components/auth/PendingApproval.tsx
import { useTranslation } from 'react-i18next'
import { Clock } from 'lucide-react'

interface PendingApprovalProps {
  onBackToSignIn: () => void
}

export function PendingApproval({ onBackToSignIn }: PendingApprovalProps) {
  const { t } = useTranslation()

  return (
    <div className="w-full max-w-sm space-y-6 text-center">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
        <Clock className="h-8 w-8 text-primary" />
      </div>

      <div>
        <h1 className="text-2xl font-bold">{t('auth.pendingTitle')}</h1>
        <p className="mt-2 text-sm text-muted-foreground">{t('auth.pendingSubtitle')}</p>
      </div>

      <div className="rounded-lg bg-muted p-4 text-sm">
        <p>{t('auth.pendingMessage')}</p>
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
