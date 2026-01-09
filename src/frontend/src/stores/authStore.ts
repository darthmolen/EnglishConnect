// src/frontend/src/stores/authStore.ts
/**
 * Unified auth store supporting both local JWT and Azure AD authentication.
 */
import { create } from 'zustand'
import type { AccountInfo } from '@azure/msal-browser'
import {
  getAccessToken as getStoredAccessToken,
  getRefreshToken,
  getStoredUser,
  storeTokens,
  storeUser,
  clearAuth,
  isAccessTokenExpired,
  type LocalUser,
} from '@/auth/localAuth'
import {
  fetchAuthConfig,
  authLogin,
  authLogout,
  authRefreshToken,
  fetchCurrentUser,
  type AuthConfig,
  type LoginRequest,
} from '@/services/api'

// Auth provider type
type AuthProvider = 'local' | 'azure_ad' | null

// Unified account type for backwards compatibility
interface UnifiedAccount {
  name: string | null
  username: string
  email?: string
}

interface AuthState {
  // Common state
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  authConfig: AuthConfig | null

  // Provider-specific state
  authProvider: AuthProvider
  localUser: LocalUser | null
  msalAccount: AccountInfo | null

  // Backwards-compatible computed properties
  account: UnifiedAccount | null

  // Actions
  initialize: () => Promise<void>
  login: () => void  // Navigate to login page
  loginLocal: (credentials: LoginRequest) => Promise<void>
  loginAzureAd: () => Promise<void>
  logout: () => Promise<void>
  getAccessToken: () => Promise<string | null>
  checkAuth: () => void
  setError: (error: string | null) => void

  // For checking if Azure AD is available
  isAzureAdEnabled: () => boolean
  isLocalAuthEnabled: () => boolean
}

// MSAL instance (lazy loaded to avoid initialization issues)
let msalInstance: any = null
let loginRequest: any = null

async function getMsalInstance() {
  if (!msalInstance) {
    const { msalInstance: instance } = await import('@/auth/AuthProvider')
    const { loginRequest: req } = await import('@/auth/msalConfig')
    msalInstance = instance
    loginRequest = req
  }
  return { msalInstance, loginRequest }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  isAuthenticated: false,
  isLoading: true,
  error: null,
  authConfig: null,
  authProvider: null,
  localUser: null,
  msalAccount: null,

  // Backwards-compatible computed account property
  get account(): UnifiedAccount | null {
    const { localUser, msalAccount, authProvider } = get()
    if (authProvider === 'local' && localUser) {
      return {
        name: localUser.firstName
          ? `${localUser.firstName}${localUser.lastName ? ' ' + localUser.lastName : ''}`
          : null,
        username: localUser.email,
        email: localUser.email,
      }
    }
    if (authProvider === 'azure_ad' && msalAccount) {
      return {
        name: msalAccount.name ?? null,
        username: msalAccount.username,
        email: msalAccount.username,
      }
    }
    return null
  },

  // Navigate to login page (for backwards compatibility)
  login: () => {
    window.location.href = '/login'
  },

  initialize: async () => {
    set({ isLoading: true, error: null })

    try {
      // Fetch auth config from backend
      const config = await fetchAuthConfig()
      set({ authConfig: config })

      // Check for existing local auth session
      if (config.auth_mode === 'local' || config.auth_mode === 'both') {
        const storedUser = getStoredUser()
        const hasToken = getStoredAccessToken()

        if (storedUser && hasToken) {
          // Try to refresh if expired
          if (isAccessTokenExpired()) {
            const refreshTokenStr = getRefreshToken()
            if (refreshTokenStr) {
              try {
                const tokens = await authRefreshToken(refreshTokenStr)
                storeTokens(tokens)
                const user = await fetchCurrentUser(tokens.access_token)
                storeUser(user)
                set({
                  isAuthenticated: true,
                  authProvider: 'local',
                  localUser: user,
                  isLoading: false,
                })
                return
              } catch {
                // Refresh failed, clear auth
                clearAuth()
              }
            }
          } else {
            // Token still valid
            set({
              isAuthenticated: true,
              authProvider: 'local',
              localUser: storedUser,
              isLoading: false,
            })
            return
          }
        }
      }

      // Check for existing Azure AD session
      if (config.auth_mode === 'azure_ad' || config.auth_mode === 'both') {
        try {
          const { msalInstance: msal } = await getMsalInstance()
          const accounts = msal.getAllAccounts()
          if (accounts.length > 0) {
            msal.setActiveAccount(accounts[0])
            set({
              isAuthenticated: true,
              authProvider: 'azure_ad',
              msalAccount: accounts[0],
              isLoading: false,
            })
            return
          }
        } catch {
          // MSAL not available or failed
        }
      }

      // No existing session
      set({ isAuthenticated: false, isLoading: false })
    } catch (error) {
      set({
        error: (error as Error).message,
        isLoading: false,
      })
    }
  },

  loginLocal: async (credentials: LoginRequest) => {
    set({ isLoading: true, error: null })

    try {
      const tokens = await authLogin(credentials)
      storeTokens(tokens)

      const user = await fetchCurrentUser(tokens.access_token)
      storeUser(user)

      set({
        isAuthenticated: true,
        authProvider: 'local',
        localUser: user,
        isLoading: false,
      })
    } catch (error) {
      set({
        error: (error as Error).message,
        isLoading: false,
      })
      throw error
    }
  },

  loginAzureAd: async () => {
    set({ isLoading: true, error: null })

    try {
      const { msalInstance: msal, loginRequest: req } = await getMsalInstance()
      await msal.loginRedirect(req)
    } catch (error) {
      set({
        error: (error as Error).message,
        isLoading: false,
      })
    }
  },

  logout: async () => {
    const { authProvider } = get()
    set({ isLoading: true })

    try {
      if (authProvider === 'local') {
        // Revoke refresh token on server
        const accessToken = getStoredAccessToken()
        const refreshToken = getRefreshToken()
        if (accessToken && refreshToken) {
          await authLogout(accessToken, refreshToken)
        }
        clearAuth()
      } else if (authProvider === 'azure_ad') {
        const { msalInstance: msal } = await getMsalInstance()
        await msal.logoutRedirect()
      }

      set({
        isAuthenticated: false,
        authProvider: null,
        localUser: null,
        msalAccount: null,
        isLoading: false,
      })
    } catch (error) {
      set({
        error: (error as Error).message,
        isLoading: false,
      })
    }
  },

  getAccessToken: async () => {
    const { authProvider } = get()

    if (authProvider === 'local') {
      // Check if token needs refresh
      if (isAccessTokenExpired()) {
        const refreshTokenStr = getRefreshToken()
        if (refreshTokenStr) {
          try {
            const tokens = await authRefreshToken(refreshTokenStr)
            storeTokens(tokens)
            return tokens.access_token
          } catch {
            // Refresh failed, user needs to re-login
            set({
              isAuthenticated: false,
              authProvider: null,
              localUser: null,
            })
            clearAuth()
            return null
          }
        }
        return null
      }
      return getStoredAccessToken()
    } else if (authProvider === 'azure_ad') {
      try {
        const { msalInstance: msal, loginRequest: req } = await getMsalInstance()
        const account = msal.getActiveAccount()
        if (!account) return null

        const response = await msal.acquireTokenSilent({
          ...req,
          account,
        })
        // Use ID token for Azure AD (access tokens for Graph can't be verified)
        return response.idToken
      } catch {
        // Token expired, need to re-authenticate
        await get().loginAzureAd()
        return null
      }
    }

    return null
  },

  checkAuth: () => {
    // Legacy method for compatibility - just triggers initialize if not done
    const { authConfig } = get()
    if (!authConfig) {
      get().initialize()
    }
  },

  setError: (error: string | null) => {
    set({ error })
  },

  isAzureAdEnabled: () => {
    const { authConfig } = get()
    return authConfig?.auth_mode === 'azure_ad' || authConfig?.auth_mode === 'both'
  },

  isLocalAuthEnabled: () => {
    const { authConfig } = get()
    return authConfig?.auth_mode === 'local' || authConfig?.auth_mode === 'both'
  },
}))

// Re-export for backwards compatibility
export type { LocalUser } from '@/auth/localAuth'
