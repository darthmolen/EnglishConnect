import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import { cn } from '@/lib/utils'

interface AuthenticatedImageProps {
  src: string
  alt: string
  className?: string
  loading?: 'lazy' | 'eager'
}

/**
 * Image component that fetches images with authentication.
 * Regular <img> tags don't send Authorization headers, so we need
 * to fetch the image with the token and create a blob URL.
 */
export function AuthenticatedImage({
  src,
  alt,
  className,
  loading = 'lazy',
}: AuthenticatedImageProps) {
  const { t } = useTranslation()
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [error, setError] = useState(false)
  const { getAccessToken } = useAuthStore()

  useEffect(() => {
    let cancelled = false
    let objectUrl: string | null = null

    async function fetchImage() {
      if (!src) return

      try {
        const token = await getAccessToken()
        if (cancelled) return

        // Build headers - include Authorization only if we have a token
        const headers: Record<string, string> = {}
        if (token) {
          headers.Authorization = `Bearer ${token}`
        }

        const response = await fetch(src, { headers })

        if (!response.ok) {
          throw new Error(`Failed to fetch image: ${response.status}`)
        }

        const blob = await response.blob()
        if (!cancelled) {
          objectUrl = URL.createObjectURL(blob)
          setBlobUrl(objectUrl)
        }
      } catch (err) {
        if (!cancelled) {
          console.error('Failed to load authenticated image:', err)
          setError(true)
        }
      }
    }

    fetchImage()

    return () => {
      cancelled = true
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl)
      }
    }
  }, [src, getAccessToken])

  if (error) {
    return (
      <div className={cn('flex items-center justify-center bg-muted text-muted-foreground text-sm', className)}>
        {t('image.unavailable')}
      </div>
    )
  }

  if (!blobUrl) {
    return (
      <div className={cn('flex items-center justify-center bg-muted animate-pulse', className)}>
        <span className="sr-only">{t('image.loading')}</span>
      </div>
    )
  }

  return (
    <img
      src={blobUrl}
      alt={alt}
      className={className}
      loading={loading}
    />
  )
}
