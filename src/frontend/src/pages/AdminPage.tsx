// src/frontend/src/pages/AdminPage.tsx
import { useTranslation } from 'react-i18next'
import { ArrowLeft } from 'lucide-react'
import { UserManagement } from '@/components/admin/UserManagement'

export function AdminPage() {
  const { t, i18n } = useTranslation()

  const handleBackToApp = () => {
    window.location.hash = '#/'
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="mx-auto max-w-5xl flex items-center justify-between px-4 py-4">
          <div className="flex items-center gap-4">
            <button
              onClick={handleBackToApp}
              className="rounded-lg p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              title="Back to app"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            <div>
              <h1 className="text-xl font-bold">{t('admin.title')}</h1>
              <p className="text-sm text-muted-foreground">{t('admin.subtitle')}</p>
            </div>
          </div>
          <select
            value={i18n.language}
            onChange={(e) => i18n.changeLanguage(e.target.value)}
            className="rounded-md border bg-background px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="es">Español</option>
            <option value="en">English</option>
          </select>
        </div>
      </header>

      {/* Main content */}
      <main className="mx-auto max-w-5xl px-4 py-6">
        <UserManagement />
      </main>
    </div>
  )
}
