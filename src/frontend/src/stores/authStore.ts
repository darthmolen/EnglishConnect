// src/frontend/src/stores/authStore.ts
import { create } from "zustand";
import { AccountInfo } from "@azure/msal-browser";
import { msalInstance } from "../auth/AuthProvider";
import { loginRequest } from "../auth/msalConfig";

interface AuthState {
  account: AccountInfo | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  getAccessToken: () => Promise<string | null>;
  checkAuth: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  account: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,

  checkAuth: () => {
    const accounts = msalInstance.getAllAccounts();
    if (accounts.length > 0) {
      msalInstance.setActiveAccount(accounts[0]);
      set({ account: accounts[0], isAuthenticated: true, isLoading: false });
    } else {
      set({ account: null, isAuthenticated: false, isLoading: false });
    }
  },

  login: async () => {
    set({ isLoading: true, error: null });
    try {
      await msalInstance.loginRedirect(loginRequest);
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
    }
  },

  logout: async () => {
    set({ isLoading: true });
    try {
      await msalInstance.logoutRedirect();
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
    }
  },

  getAccessToken: async () => {
    const account = msalInstance.getActiveAccount();
    if (!account) return null;

    try {
      const response = await msalInstance.acquireTokenSilent({
        ...loginRequest,
        account,
      });
      return response.accessToken;
    } catch (error) {
      // Token expired, need to re-authenticate
      await get().login();
      return null;
    }
  },
}));
