"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError, LoginResponse, UserResponse, loadStoredSession, requestJson, saveStoredSession } from "@/lib/api";

export type AuthContextValue = {
  token: string | null;
  email: string | null;
  initializing: boolean;
  loading: boolean;
  pendingConfirmationEmail: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  clearPendingConfirmation: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [loading, setLoading] = useState(false);
  const [pendingConfirmationEmail, setPendingConfirmationEmail] = useState<string | null>(null);

  useEffect(() => {
    const session = loadStoredSession();
    if (session) {
      setToken(session.token);
      setEmail(session.email ?? null);
    }
    setInitializing(false);
  }, []);

  const persistSession = useCallback((nextToken: string | null, nextEmail: string | null) => {
    setToken(nextToken);
    setEmail(nextEmail);
    if (nextToken) {
      saveStoredSession({ token: nextToken, email: nextEmail ?? undefined });
    } else {
      saveStoredSession(null);
    }
    if (nextToken) {
      setPendingConfirmationEmail(null);
    }
  }, []);

  const login = useCallback(
    async (loginEmail: string, password: string) => {
      setLoading(true);
      try {
        const data = await requestJson<LoginResponse>(
          "/auth/login",
          {
            method: "POST",
            body: JSON.stringify({ email: loginEmail, password }),
          },
        );
        persistSession(data.access_token, loginEmail);
        setPendingConfirmationEmail(null);
      } catch (error) {
        if (error instanceof ApiError) {
          if (error.status === 403) {
            setPendingConfirmationEmail(loginEmail);
            throw new Error(
              "Please confirm your email address before logging in. Check your inbox for the confirmation link.",
            );
          }
          throw new Error(error.message);
        }
        throw new Error("Unable to log in. Please try again.");
      } finally {
        setLoading(false);
      }
    },
    [persistSession],
  );

  const register = useCallback(
    async (registerEmail: string, password: string) => {
      setLoading(true);
      try {
        await requestJson<UserResponse>(
          "/auth/register",
          {
            method: "POST",
            body: JSON.stringify({ email: registerEmail, password }),
          },
        );
        setPendingConfirmationEmail(registerEmail);
      } catch (error) {
        if (error instanceof ApiError) {
          throw new Error(error.message);
        }
        throw new Error("Unable to register. Please try again.");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const logout = useCallback(() => {
    persistSession(null, null);
    router.push("/");
  }, [persistSession, router]);

  const clearPendingConfirmation = useCallback(() => {
    setPendingConfirmationEmail(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      email,
      initializing,
      loading,
      pendingConfirmationEmail,
      login,
      register,
      logout,
      clearPendingConfirmation,
    }),
    [
      email,
      initializing,
      loading,
      login,
      logout,
      pendingConfirmationEmail,
      register,
      token,
      clearPendingConfirmation,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuthContext must be used within an AuthProvider");
  }
  return context;
}
