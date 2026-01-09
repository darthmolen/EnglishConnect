// src/frontend/src/auth/localAuth.ts
/**
 * Local JWT authentication token management.
 *
 * Access tokens: stored in sessionStorage (cleared on tab close)
 * Refresh tokens: stored in localStorage (persistent, rotated on each use)
 */

const ACCESS_TOKEN_KEY = 'ec_access_token'
const REFRESH_TOKEN_KEY = 'ec_refresh_token'
const USER_KEY = 'ec_user'

export interface LocalUser {
  id: string
  email: string
  displayName: string | null
  firstName: string | null
  lastName: string | null
  isApproved: boolean
  approvalStatus: 'pending' | 'approved' | 'rejected'
  roles: string[]
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

/**
 * Store tokens after successful login.
 */
export function storeTokens(tokens: TokenResponse): void {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token)
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
}

/**
 * Store user info after successful login.
 */
export function storeUser(user: LocalUser): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

/**
 * Get the stored access token.
 */
export function getAccessToken(): string | null {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY)
}

/**
 * Get the stored refresh token.
 */
export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

/**
 * Get stored user info.
 */
export function getStoredUser(): LocalUser | null {
  const userJson = localStorage.getItem(USER_KEY)
  if (!userJson) return null
  try {
    return JSON.parse(userJson) as LocalUser
  } catch {
    return null
  }
}

/**
 * Clear all stored auth data (logout).
 */
export function clearAuth(): void {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

/**
 * Check if access token exists (not necessarily valid).
 */
export function hasAccessToken(): boolean {
  return !!getAccessToken()
}

/**
 * Check if refresh token exists.
 */
export function hasRefreshToken(): boolean {
  return !!getRefreshToken()
}

/**
 * Parse JWT token payload (without verification).
 * Used to check expiration client-side.
 */
export function parseJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(jsonPayload)
  } catch {
    return null
  }
}

/**
 * Check if access token is expired (with 60s buffer).
 */
export function isAccessTokenExpired(): boolean {
  const token = getAccessToken()
  if (!token) return true

  const payload = parseJwtPayload(token)
  if (!payload || typeof payload.exp !== 'number') return true

  // Check with 60 second buffer
  const expiresAt = payload.exp * 1000
  return Date.now() > expiresAt - 60000
}
