// src/frontend/src/auth/AuthProvider.tsx
import { MsalProvider } from "@azure/msal-react";
import { PublicClientApplication } from "@azure/msal-browser";
import { msalConfig } from "./msalConfig";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";

const msalInstance = new PublicClientApplication(msalConfig);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    msalInstance.initialize().then(async () => {
      // Handle redirect promise - MUST complete before marking initialized
      const response = await msalInstance.handleRedirectPromise();
      if (response) {
        msalInstance.setActiveAccount(response.account);
      } else {
        // No redirect response, check for existing accounts
        const accounts = msalInstance.getAllAccounts();
        if (accounts.length > 0) {
          msalInstance.setActiveAccount(accounts[0]);
        }
      }
      setIsInitialized(true);
    });
  }, []);

  if (!isInitialized) {
    return <div>Loading...</div>;
  }

  return <MsalProvider instance={msalInstance}>{children}</MsalProvider>;
}

export { msalInstance };
