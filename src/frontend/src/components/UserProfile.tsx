// src/frontend/src/components/UserProfile.tsx
import { useAuthStore } from "../stores/authStore";
import { Button } from "./ui/button";

export function UserProfile() {
  const { account, logout, isLoading } = useAuthStore();

  if (!account) return null;

  return (
    <div className="flex items-center gap-4">
      <span className="text-sm">{account.name || account.username}</span>
      <Button variant="outline" size="sm" onClick={logout} disabled={isLoading}>
        Sign out
      </Button>
    </div>
  );
}
