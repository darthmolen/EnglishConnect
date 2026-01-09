// src/frontend/src/components/admin/UserManagement.tsx
import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, X, UserPlus } from 'lucide-react'
import { adminListUsers, adminApproveUser, adminAssignRole, type UserListItem } from '@/services/api'

type StatusFilter = 'all' | 'pending' | 'approved' | 'rejected'

export function UserManagement() {
  const { t } = useTranslation()
  const [users, setUsers] = useState<UserListItem[]>([])
  const [filter, setFilter] = useState<StatusFilter>('all')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const loadUsers = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const status = filter === 'all' ? undefined : filter
      const data = await adminListUsers(status)
      setUsers(data)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [filter])

  const handleApprove = async (userId: string, approved: boolean) => {
    setActionLoading(userId)
    try {
      await adminApproveUser(userId, approved)
      await loadUsers()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setActionLoading(null)
    }
  }

  const handleAssignRole = async (userId: string, role: string) => {
    setActionLoading(userId)
    try {
      await adminAssignRole(userId, role)
      await loadUsers()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setActionLoading(null)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'approved':
        return 'bg-green-100 text-green-800'
      case 'rejected':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-yellow-100 text-yellow-800'
    }
  }

  return (
    <div className="space-y-6">
      {/* Filter tabs */}
      <div className="flex gap-2 border-b">
        {(['all', 'pending', 'approved', 'rejected'] as StatusFilter[]).map((status) => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              filter === status
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            {t(`admin.filter${status.charAt(0).toUpperCase() + status.slice(1)}`)}
          </button>
        ))}
      </div>

      {/* Error message */}
      {error && (
        <div className="rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Loading state */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-muted-foreground">{t('app.loading')}</div>
        </div>
      ) : users.length === 0 ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-muted-foreground">{t('admin.noUsers')}</div>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="px-4 py-3 text-left text-sm font-medium">{t('auth.email')}</th>
                <th className="px-4 py-3 text-left text-sm font-medium">{t('auth.firstName')}</th>
                <th className="px-4 py-3 text-left text-sm font-medium">{t('admin.status')}</th>
                <th className="px-4 py-3 text-left text-sm font-medium">{t('admin.roles')}</th>
                <th className="px-4 py-3 text-left text-sm font-medium">{t('admin.createdAt')}</th>
                <th className="px-4 py-3 text-left text-sm font-medium">{t('admin.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b hover:bg-muted/30">
                  <td className="px-4 py-3 text-sm">{user.email}</td>
                  <td className="px-4 py-3 text-sm">
                    {user.display_name || `${user.first_name || ''} ${user.last_name || ''}`.trim() || '-'}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block rounded-full px-2 py-1 text-xs font-medium ${getStatusBadgeClass(
                        user.approval_status
                      )}`}
                    >
                      {user.approval_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <div className="flex flex-wrap gap-1">
                      {user.roles.map((role) => (
                        <span
                          key={role}
                          className="inline-block rounded bg-primary/10 px-2 py-0.5 text-xs text-primary"
                        >
                          {role}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">
                    {formatDate(user.created_at)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {user.approval_status === 'pending' && (
                        <>
                          <button
                            onClick={() => handleApprove(user.id, true)}
                            disabled={actionLoading === user.id}
                            className="rounded-lg bg-green-600 p-1.5 text-white transition-colors hover:bg-green-700 disabled:opacity-50"
                            title={t('admin.approve')}
                          >
                            <Check className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => handleApprove(user.id, false)}
                            disabled={actionLoading === user.id}
                            className="rounded-lg bg-red-600 p-1.5 text-white transition-colors hover:bg-red-700 disabled:opacity-50"
                            title={t('admin.reject')}
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </>
                      )}
                      {user.approval_status === 'approved' && !user.roles.includes('teacher') && (
                        <button
                          onClick={() => handleAssignRole(user.id, 'teacher')}
                          disabled={actionLoading === user.id}
                          className="rounded-lg bg-primary p-1.5 text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
                          title={t('admin.assignRole')}
                        >
                          <UserPlus className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
