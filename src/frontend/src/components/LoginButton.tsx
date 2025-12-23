// src/frontend/src/components/LoginButton.tsx
import { useAuthStore } from "../stores/authStore";

export function LoginButton() {
  const { login, isLoading } = useAuthStore();

  return (
    <button
      onClick={login}
      disabled={isLoading}
      className="rounded-lg bg-primary px-6 py-3 text-primary-foreground font-medium transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
    >
      {isLoading ? "Signing in..." : "Sign in with Microsoft"}
    </button>
  );
}
