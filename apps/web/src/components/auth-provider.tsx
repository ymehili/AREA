"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter, usePathname } from "next/navigation";

import { ApiError, LoginResponse, UserProfile, loadStoredSession, requestJson, saveStoredSession, fetchProfile } from "@/lib/api";

export type AuthContextValue = {
  token: string | null;
  email: string | null;
  profile: UserProfile | null;
  initializing: boolean;
  loading: boolean;
  pendingConfirmationEmail: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  clearPendingConfirmation: () => void;
  setEmail: (email: string | null) => void;
  refreshProfile: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [loading, setLoading] = useState(false);
  const [pendingConfirmationEmail, setPendingConfirmationEmail] = useState<string | null>(null);

  const persistSession = useCallback((nextToken: string | null, nextEmail: string | null, userProfile: UserProfile | null = null) => {
    setToken(nextToken);
    setEmail(nextEmail);
    setProfile(userProfile);
    if (nextToken) {
      saveStoredSession({ token: nextToken, email: nextEmail ?? undefined });
    } else {
      saveStoredSession(null);
    }
    if (nextToken) {
      setPendingConfirmationEmail(null);
    }
  }, []);

  useEffect(() => {
    const session = loadStoredSession();
    if (session) {
      setToken(session.token);
      setEmail(session.email ?? null);
      // Fetch user profile if we have a token
      const fetchUserProfile = async () => {
        try {
          const userProfile = await fetchProfile(session.token);
          setProfile(userProfile);
        } catch (error) {
          console.error("Failed to fetch user profile:", error);
          // Continue without profile data if fetch fails
        }
        setInitializing(false);
      };
      
      fetchUserProfile();
    } else {
      setInitializing(false);
    }
  }, []);

  // Check for OAuth token in URL hash
  useEffect(() => {
    if (typeof window !== "undefined") {
      const hash = window.location.hash;
      if (hash.startsWith("#access_token=")) {
        const accessToken = hash.substring(14); // Remove "#access_token=" prefix
        persistSession(accessToken, null);
        // Remove the token from URL
        window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
        // Redirect to dashboard
        router.replace("/dashboard");
      }
    }
  }, [pathname, router, persistSession]);

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
        
        // Fetch user profile after login
        const userProfile = await fetchProfile(data.access_token);
        persistSession(data.access_token, loginEmail, userProfile);
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
        // We don't need a specific response type here as we only need to know if registration was successful
        await requestJson(
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
    persistSession(null, null, null);
    router.push("/");
  }, [persistSession, router]);

  const clearPendingConfirmation = useCallback(() => {
    setPendingConfirmationEmail(null);
  }, []);

  const setEmailAddress = useCallback(
    (nextEmail: string | null) => {
      if (!token) {
        setEmail(nextEmail);
        return;
      }
      persistSession(token, nextEmail, profile);
    },
    [persistSession, token, profile],
  );

  const refreshProfile = useCallback(async () => {
    if (token) {
      try {
        const userProfile = await fetchProfile(token);
        setProfile(userProfile);
      } catch (error) {
        console.error("Failed to refresh user profile:", error);
      }
    }
  }, [token]);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      email,
      profile,
      initializing,
      loading,
      pendingConfirmationEmail,
      login,
      register,
      logout,
      clearPendingConfirmation,
      setEmail: setEmailAddress,
      refreshProfile,
    }),
    [
      email,
      profile,
      initializing,
      loading,
      login,
      logout,
      pendingConfirmationEmail,
      register,
      token,
      clearPendingConfirmation,
      setEmailAddress,
      refreshProfile,
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
