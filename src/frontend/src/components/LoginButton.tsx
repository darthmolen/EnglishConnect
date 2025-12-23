// src/frontend/src/components/LoginButton.tsx
import { useAuthStore } from "../stores/authStore";
import { Button } from "./ui/button";

export function LoginButton() {
  const { login, isLoading } = useAuthStore();

  return (
    <Button onClick={login} disabled={isLoading}>
      {isLoading ? "Signing in..." : "Sign in with Microsoft"}
    </Button>
  );
}
