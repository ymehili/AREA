import React, { useCallback, useMemo, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { requestJson, ApiError } from "../utils/api";

// Define types
type LoginMethodStatus = {
  provider: string;
  linked: boolean;
  identifier?: string | null;
};

type UserProfile = {
  email: string;
  full_name?: string | null;
  is_confirmed: boolean;
  has_password: boolean;
  login_methods: LoginMethodStatus[];
};

// Define constants
const STORAGE_KEY = "area_mobile_session";

// Define types for auth context
type AuthContextValue = {
  token: string | null;
  email: string | null;
  initializing: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  setEmail: (email: string | null) => Promise<void>;
  persistSession: (token: string | null, email: string | null) => Promise<void>;
};

type StoredSession = {
  token: string;
  email?: string;
};

// Create context
const AuthContext = React.createContext<AuthContextValue | undefined>(undefined);

// Define functions that were duplicated in the original App.tsx
async function loadSession(): Promise<StoredSession | null> {
  const raw = await AsyncStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as StoredSession;
  } catch {
    await AsyncStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

// Auth provider component
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [loading, setLoading] = useState(false);

  React.useEffect(() => {
    loadSession()
      .then((session) => {
        if (session) {
          setToken(session.token);
          setEmail(session.email ?? null);
        }
      })
      .finally(() => setInitializing(false));
  }, []);

  const persistSession = useCallback(async (nextToken: string | null, nextEmail: string | null) => {
    setToken(nextToken);
    setEmail(nextEmail);
    if (nextToken) {
      await AsyncStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ token: nextToken, email: nextEmail ?? undefined }),
      );
    } else {
      await AsyncStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  const login = useCallback(
    async (loginEmail: string, password: string) => {
      setLoading(true);
      try {
        const data = await requestJson<{ access_token: string }>(
          "/auth/login",
          {
            method: "POST",
            body: JSON.stringify({ email: loginEmail, password }),
          },
        );
        await persistSession(data.access_token, loginEmail);
      } catch (error) {
        if (error instanceof Error && 'status' in error) {
          if ((error as any).status === 403) {
            throw new Error(
              "Please confirm your email address before logging in. Check your inbox for the confirmation link.",
            );
          }
          if ((error as any).status === 401) {
            throw new Error("Unable to log in. Please check your credentials.");
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
        await requestJson<StoredSession>(
          "/auth/register",
          {
            method: "POST",
            body: JSON.stringify({ email: registerEmail, password }),
          },
        );
      } catch (error) {
        if (error instanceof Error) {
          throw new Error(error.message);
        }
        throw new Error("Unable to create account. Please try again.");
      } finally {
        setLoading(false);
      }
    },
    [persistSession],
  );

  const logout = useCallback(async () => {
    await persistSession(null, null);
  }, [persistSession]);

  const setEmailAddress = useCallback(
    async (nextEmail: string | null) => {
      if (!token) {
        setEmail(nextEmail);
        return;
      }
      await persistSession(token, nextEmail);
    },
    [persistSession, token],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      email,
      initializing,
      loading,
      login,
      register,
      logout,
      setEmail: setEmailAddress,
      persistSession,
    }),
    [email, initializing, loading, login, logout, register, token, setEmailAddress, persistSession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Hook to use auth context
export function useAuth(): AuthContextValue {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}