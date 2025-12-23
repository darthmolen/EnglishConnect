// src/frontend/src/components/UserProfile.tsx
import { useAuthStore } from "../stores/authStore";

export function UserProfile() {
  const { account, logout, isLoading } = useAuthStore();

  if (!account) return null;

  return (
    <div className="flex items-center gap-4">
      <span className="text-sm">{account.name || account.username}</span>
      <button
        onClick={logout}
        disabled={isLoading}
        className="rounded-lg border border-input bg-background px-3 py-1.5 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground disabled:cursor-not-allowed disabled:opacity-50"
      >
        Sign out
      </button>
    </div>
  );
}
