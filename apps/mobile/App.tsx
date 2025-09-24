import { StatusBar } from "expo-status-bar";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Button,
  Platform,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import Constants from "expo-constants";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { NavigationContainer, useFocusEffect, useNavigation } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import * as WebBrowser from "expo-web-browser";
import * as Linking from "expo-linking";

function resolveApiBaseUrl(): string {
  const explicit = process.env.EXPO_PUBLIC_API_URL;
  if (explicit && typeof explicit === "string" && explicit.trim() !== "") {
    return explicit.replace(/\/$/, "");
  }
  // Try to derive LAN IP from Expo runtime (works in Expo Go)
  const anyConstants = Constants as unknown as Record<string, any>;
  const debuggerHost: string | undefined =
    anyConstants?.expoGoConfig?.debuggerHost || anyConstants?.manifest?.debuggerHost;
  const hostUri: string | undefined =
    anyConstants?.expoConfig?.hostUri || anyConstants?.expoGoConfig?.hostUri;
  const candidate = (debuggerHost || hostUri)?.split(":")[0];
  if (candidate && /^\d+\.\d+\.\d+\.\d+$/.test(candidate)) {
    return `http://${candidate}:8080/api/v1`;
  }
  // Emulators
  if (Platform.OS === "android") {
    // Android emulator maps host loopback to 10.0.2.2
    return "http://10.0.2.2:8080/api/v1";
  }
  // iOS Simulator usually reaches host via localhost
  return "http://localhost:8080/api/v1";
}

const API_BASE_URL = resolveApiBaseUrl();
const STORAGE_KEY = "area_mobile_session";

class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
  }
}

async function parseError(response: Response): Promise<string> {
  try {
    const data = await response.json();
    if (typeof data === "string") {
      return data;
    }
    if (data?.detail) {
      if (typeof data.detail === "string") {
        return data.detail;
      }
      if (Array.isArray(data.detail) && data.detail.length > 0) {
        const detail = data.detail[0];
        if (typeof detail === "string") {
          return detail;
        }
        if (detail?.msg) {
          return detail.msg as string;
        }
      }
    }
  } catch {
    // ignore parsing errors
  }
  return `Request failed with status ${response.status}`;
}

async function requestJson<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  const headers = new Headers(options.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const bodyIsJson = options.body && !(options.body instanceof FormData) && !headers.has("Content-Type");
  if (bodyIsJson) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(url, { ...options, headers });
  } catch (networkError) {
    // Normalize network-level failures
    const message =
      networkError instanceof Error
        ? `Network error: ${networkError.message}`
        : "Network error: request failed";
    throw new ApiError(0, message);
  }
  if (response.status === 401) {
    throw new ApiError(401, "Unauthorized");
  }
  if (!response.ok) {
    throw new ApiError(response.status, await parseError(response));
  }
  return (await response.json()) as T;
}

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

async function getProfile(token: string): Promise<UserProfile> {
  return requestJson<UserProfile>("/users/me", {}, token);
}

async function updateProfileRequest(
  token: string,
  payload: { full_name?: string | null; email?: string },
): Promise<UserProfile> {
  return requestJson<UserProfile>(
    "/users/me",
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
    token,
  );
}

async function changePasswordRequest(
  token: string,
  payload: { current_password: string; new_password: string },
): Promise<UserProfile> {
  return requestJson<UserProfile>(
    "/users/me/password",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

async function linkLoginProvider(
  token: string,
  provider: string,
  identifier: string,
): Promise<LoginMethodStatus> {
  return requestJson<LoginMethodStatus>(
    `/users/me/login-methods/${provider}`,
    {
      method: "POST",
      body: JSON.stringify({ identifier }),
    },
    token,
  );
}

async function unlinkLoginProvider(
  token: string,
  provider: string,
): Promise<LoginMethodStatus> {
  return requestJson<LoginMethodStatus>(
    `/users/me/login-methods/${provider}`,
    {
      method: "DELETE",
    },
    token,
  );
}

const PROVIDER_LABELS: Record<string, string> = {
  google: "Google",
  github: "GitHub",
  microsoft: "Microsoft",
};

// Mirrored options from web wizard for a simple, consistent UX
const SERVICES = ["Gmail", "Google Drive", "Slack", "GitHub"] as const;
const TRIGGERS_BY_SERVICE: Record<string, string[]> = {
  Gmail: ["New Email", "New Email w/ Attachment"],
  "Google Drive": ["New File in Folder"],
  Slack: ["New Message in Channel"],
  GitHub: ["New Pull Request"],
};
const ACTIONS_BY_SERVICE: Record<string, string[]> = {
  Gmail: ["Send Email"],
  "Google Drive": ["Upload File", "Create Folder"],
  Slack: ["Send Message"],
  GitHub: ["Create Issue"],
};

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

const AuthContext = React.createContext<AuthContextValue | undefined>(undefined);

function useAuth(): AuthContextValue {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

type StoredSession = {
  token: string;
  email?: string;
};

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

function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
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
        if (error instanceof ApiError) {
          if (error.status === 403) {
            throw new Error(
              "Please confirm your email address before logging in. Check your inbox for the confirmation link.",
            );
          }
          if (error.status === 401) {
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
        if (error instanceof ApiError) {
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

function LoginScreen() {
  const auth = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async () => {
    setError(null);
    try {
      if (mode === "login") {
        await auth.login(email, password);
      } else {
        await auth.register(email, password);
        setMode("login");
        setPassword("");
        Alert.alert(
          "Check your email",
          "We sent a confirmation link. Confirm your email before signing in.",
        );
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Something went wrong.";
      setError(message);
      Alert.alert("Authentication failed", message);
    }
  }, [auth, email, mode, password]);

  const handleGoogleSignIn = useCallback(async () => {
    try {
      const apiUrl = process.env.EXPO_PUBLIC_API_URL;
      const mobileRedirectEnv = process.env.EXPO_PUBLIC_FRONTEND_URL_MOBILE;

      if (!apiUrl) {
        throw new Error("EXPO_PUBLIC_API_URL environment variable is not defined");
      }

      const redirectUrl = mobileRedirectEnv && mobileRedirectEnv.trim() !== ""
        ? mobileRedirectEnv
        : Linking.createURL("/oauth/callback");

      console.log("Starting OAuth flow...");
      console.log("OAuth URL:", `${apiUrl}/api/v1/oauth/google`);
      console.log("Return URL:", redirectUrl);

      const result = await WebBrowser.openAuthSessionAsync(
        `${apiUrl}/api/v1/oauth/google`,
        redirectUrl,
      );

      console.log('OAuth result:', result);

      if (result.type === 'success' && result.url) {
        console.log('Success URL received:', result.url);
        
        // Extract token from the redirect URL
        const url = new URL(result.url);
        console.log('Parsed URL:', {
          pathname: url.pathname,
          search: url.search,
          hash: url.hash
        });
        
        // Check query parameters first (mobile redirect)
        let accessToken = url.searchParams.get('access_token');
        console.log('Token from query params:', accessToken);
        
        // If not in query, check URL hash (web redirect)
        if (!accessToken && url.hash) {
          const hashParams = new URLSearchParams(url.hash.substring(1));
          accessToken = hashParams.get('access_token');
          console.log('Token from hash:', accessToken);
        }

        if (accessToken) {
          console.log('Found access token, persisting session...');
          // Store the token using your existing auth system
          await auth.persistSession(accessToken, null);
          Alert.alert('Success', 'Signed in with Google successfully!');
        } else {
          console.log('No access token found in URL');
          throw new Error('No access token received from OAuth flow');
        }
      } else if (result.type === 'cancel') {
        console.log('OAuth cancelled by user');
      } else {
        console.log('Unexpected OAuth result type:', result.type);
      }
    } catch (error) {
      console.error('Google OAuth error:', error);
      const message = error instanceof Error ? error.message : "Google sign-in failed";
      Alert.alert('OAuth Error', message);
    }
  }, [auth]);

  return (
    <SafeAreaView style={styles.centered}>
      <Text style={styles.title}>Action-Reaction</Text>
      <View style={styles.toggleRow}>
        <Button
          title={mode === "login" ? "Need an account?" : "Have an account?"}
          onPress={() => setMode((prev) => (prev === "login" ? "register" : "login"))}
        />
      </View>
      <View style={styles.formGroup}>
        <Text>Email</Text>
        <TextInput
          style={styles.input}
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          keyboardType="email-address"
        />
      </View>
      <View style={styles.formGroup}>
        <Text>Password</Text>
        <TextInput
          style={styles.input}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />
      </View>
      {error ? <Text style={styles.errorText}>{error}</Text> : null}
      <Button
        title={auth.loading ? "Please wait..." : mode === "login" ? "Log in" : "Create account"}
        onPress={submit}
        disabled={auth.loading}
      />
      <View style={{ height: 16 }} />
      <Button
        title="Sign in with Google"
        onPress={handleGoogleSignIn} // Use the new handler instead of window.open
      />
    </SafeAreaView>
  );
}

function DashboardScreen() {
  const auth = useAuth();
  const navigation = useNavigation<any>();
  const [areas, setAreas] = useState<{ id: string; name: string; trigger: string; action: string; enabled: boolean }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAreas = useCallback(async () => {
    if (!auth.token) {
      return;
    }
    setLoading(true);
    try {
      const data = await requestJson<{ 
        id: string; 
        name: string; 
        trigger_service: string; 
        trigger_action: string; 
        reaction_service: string; 
        reaction_action: string; 
        enabled: boolean;
        created_at: string;
        updated_at: string;
      }[]>(
        "/areas",
        { method: "GET" },
        auth.token,
      );
      const transformed = data.map(area => ({
        id: area.id,
        name: area.name,
        trigger: `${area.trigger_service}: ${area.trigger_action}`,
        action: `${area.reaction_service}: ${area.reaction_action}`,
        enabled: area.enabled,
      }));
      setAreas(transformed);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to load areas.";
      if (err instanceof ApiError && err.status === 401) {
        await auth.logout();
        return;
      }
      setError(message);
      Alert.alert("Failed to load areas", message);
    } finally {
      setLoading(false);
    }
  }, [auth]);

  useEffect(() => {
    void loadAreas();
  }, [loadAreas]);

  useFocusEffect(
    useCallback(() => {
      void loadAreas();
      return () => {};
    }, [loadAreas]),
  );

  const toggleArea = async (id: string, enabled: boolean) => {
    try {
      const endpoint = enabled ? `/areas/${id}/enable` : `/areas/${id}/disable`;
      await requestJson(
        endpoint,
        { method: "POST" },
        auth.token,
      );
      setAreas((prev) => prev.map((a) => (a.id === id ? { ...a, enabled } : a)));
      Alert.alert("Success", `Area ${enabled ? "enabled" : "disabled"}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : `Failed to ${enabled ? "enable" : "disable"} area.`;
      if (err instanceof ApiError && err.status === 401) {
        await auth.logout();
        return;
      }
      Alert.alert("Error", message);
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.screen}>
        <Text style={styles.h1}>Dashboard</Text>
        <View style={styles.centered}>
          <ActivityIndicator size="large" />
        </View>
      </SafeAreaView>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={styles.screen}>
        <Text style={styles.h1}>Dashboard</Text>
        <View style={styles.centered}>
          <Text style={styles.errorText}>{error}</Text>
          <View style={{ height: 12 }} />
          <Button title="Retry" onPress={() => void loadAreas()} />
        </View>
      </SafeAreaView>
    );
  }

  if (areas.length === 0) {
    return (
      <SafeAreaView style={styles.screen}>
        <Text style={styles.h1}>Dashboard</Text>
        <View style={styles.centered}>
          <Text style={styles.muted}>You have no AREAs yet.</Text>
          <View style={{ height: 12 }} />
          <Button title="Create your first AREA" onPress={() => navigation.navigate("Wizard") } />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.screen}>
      <Text style={styles.h1}>Dashboard</Text>
      <ScrollView>
        {areas.map((area) => (
          <View key={area.id} style={styles.card}>
            <View style={styles.rowBetween}>
              <Text style={styles.cardTitle}>{area.name}</Text>
              <Text style={styles.smallMuted}>{area.enabled ? "Enabled" : "Disabled"}</Text>
            </View>
            <Text style={styles.muted}>When: {area.trigger}</Text>
            <Text style={styles.muted}>Then: {area.action}</Text>
            <View style={{ height: 8 }} />
            <View style={styles.rowBetween}>
              <Button 
                title={area.enabled ? "Disable" : "Enable"} 
                onPress={() => void toggleArea(area.id, !area.enabled)} 
              />
              <Button 
                title="Delete" 
                onPress={() => {
                  Alert.alert("Delete AREA", "Are you sure?", [
                    { text: "Cancel", style: "cancel" },
                    { text: "Delete", style: "destructive", onPress: () => {
                      requestJson(`/areas/${area.id}`, { method: "DELETE" }, (auth as any).token)
                        .then(() => {
                          setAreas(prev => prev.filter(a => a.id !== area.id));
                          Alert.alert("Deleted", "Area removed.");
                        })
                        .catch((err) => {
                          const message = err instanceof ApiError ? err.message : "Failed to delete area.";
                          Alert.alert("Error", message);
                        });
                    } },
                  ]);
                }} 
              />
            </View>
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

function ConnectionsScreen() {
  const auth = useAuth();
  const [services, setServices] = useState<{ slug: string; name: string; description?: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadServices = useCallback(async () => {
    if (!auth.token) {
      return;
    }
    setLoading(true);
    try {
      const data = await requestJson<{ services: { slug: string; name: string; description: string }[] }>(
        "/services/services",
        { method: "GET" },
        auth.token,
      );
      setServices(data.services);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to load services.";
      if (err instanceof ApiError && err.status === 401) {
        await auth.logout();
        return;
      }
      setError(message);
      Alert.alert("Failed to load services", message);
    } finally {
      setLoading(false);
    }
  }, [auth]);

  useEffect(() => {
    void loadServices();
  }, [loadServices]);

  if (loading) {
    return (
      <SafeAreaView style={styles.screen}>
        <Text style={styles.h1}>Service Connection Hub</Text>
        <View style={styles.centered}>
          <ActivityIndicator size="large" />
        </View>
      </SafeAreaView>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={styles.screen}>
        <Text style={styles.h1}>Service Connection Hub</Text>
        <View style={styles.centered}>
          <Text style={styles.errorText}>{error}</Text>
          <View style={{ height: 12 }} />
          <Button title="Retry" onPress={() => void loadServices()} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.screen}>
      <Text style={styles.h1}>Service Connection Hub</Text>
      {services.map((s) => (
        <View key={s.slug} style={styles.rowBetween}>
          <View>
            <Text>{s.name}</Text>
            <Text style={styles.muted}>{s.description}</Text>
          </View>
          <Button title="Connect" onPress={() => {}} />
        </View>
      ))}
    </SafeAreaView>
  );
}

function WizardScreen() {
  const auth = useAuth();
  const navigation = useNavigation<any>();
  const [step, setStep] = useState(1);
  const [triggerService, setTriggerService] = useState("");
  const [trigger, setTrigger] = useState("");
  const [actionService, setActionService] = useState("");
  const [action, setAction] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const canNext = React.useMemo(() => {
    if (step === 1) return !!triggerService;
    if (step === 2) return !!trigger;
    if (step === 3) return !!actionService;
    if (step === 4) return !!action;
    return true;
  }, [step, triggerService, trigger, actionService, action]);

  const submit = useCallback(async () => {
    if (!auth.token) {
      Alert.alert("Not signed in", "Please log in first.");
      return;
    }
    if (!(triggerService && trigger && actionService && action)) {
      Alert.alert("Missing info", "Complete all steps before creating the AREA.");
      return;
    }
    setSubmitting(true);
    try {
      await requestJson(
        "/areas",
        {
          method: "POST",
          body: JSON.stringify({
            name: `${triggerService} → ${actionService}`,
            trigger_service: triggerService,
            trigger_action: trigger,
            reaction_service: actionService,
            reaction_action: action,
          }),
        },
        auth.token,
      );
      Alert.alert("Created", "Your AREA was created successfully.");
      navigation.navigate("Dashboard");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to create AREA.";
      if (err instanceof ApiError && err.status === 401) {
        await auth.logout();
        return;
      }
      Alert.alert("Creation failed", message);
    } finally {
      setSubmitting(false);
    }
  }, [auth, triggerService, trigger, actionService, action, navigation]);

  return (
    <SafeAreaView style={styles.screen}>
      <Text style={styles.h1}>AREA Creation Wizard</Text>
      <Text style={styles.muted}>Step {step} of 5</Text>
      <View style={{ height: 16 }} />

      {step === 1 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Step 1: Choose Trigger Service</Text>
          {SERVICES.map((s) => (
            <View key={s} style={{ marginBottom: 8 }}>
              <Button title={s} onPress={() => setTriggerService(s)} />
            </View>
          ))}
          {triggerService ? <Text style={styles.muted}>Selected: {triggerService}</Text> : null}
        </View>
      )}

      {step === 2 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Step 2: Choose Trigger</Text>
          {(TRIGGERS_BY_SERVICE[triggerService] ?? []).map((t) => (
            <View key={t} style={{ marginBottom: 8 }}>
              <Button title={t} onPress={() => setTrigger(t)} />
            </View>
          ))}
          {trigger ? <Text style={styles.muted}>Selected: {trigger}</Text> : null}
        </View>
      )}

      {step === 3 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Step 3: Choose REAction Service</Text>
          {SERVICES.map((s) => (
            <View key={s} style={{ marginBottom: 8 }}>
              <Button title={s} onPress={() => setActionService(s)} />
            </View>
          ))}
          {actionService ? <Text style={styles.muted}>Selected: {actionService}</Text> : null}
        </View>
      )}

      {step === 4 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Step 4: Choose REAction</Text>
          {(ACTIONS_BY_SERVICE[actionService] ?? []).map((a) => (
            <View key={a} style={{ marginBottom: 8 }}>
              <Button title={a} onPress={() => setAction(a)} />
            </View>
          ))}
          {action ? <Text style={styles.muted}>Selected: {action}</Text> : null}
        </View>
      )}

      {step === 5 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Step 5: Review & Confirm</Text>
          <Text style={styles.muted}>
            If new "{trigger}" in {triggerService}, then "{action}" in {actionService}.
          </Text>
        </View>
      )}

      <View style={{ height: 16 }} />
      <View style={styles.rowBetween}>
        <Button title="Back" onPress={() => setStep(Math.max(1, step - 1))} />
        {step < 5 ? (
          <Button title="Next" onPress={() => setStep(Math.min(step + 1, 5))} disabled={!canNext} />
        ) : (
          <Button title={submitting ? "Creating..." : "Create AREA"} onPress={() => void submit()} disabled={submitting} />
        )}
      </View>
    </SafeAreaView>
  );
}

function ProfileScreen() {
  const auth = useAuth();
  const { token, logout, setEmail: syncEmail } = auth;

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [fullName, setFullName] = useState("");
  const [email, setEmailField] = useState(auth.email ?? "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [profileSaving, setProfileSaving] = useState(false);
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [providerPending, setProviderPending] = useState<Record<string, boolean>>({});
  const [linkIdentifiers, setLinkIdentifiers] = useState<Record<string, string>>({});

  const updateLoginMethod = useCallback((nextStatus: LoginMethodStatus) => {
    setProfile((prev) => {
      if (!prev) {
        return prev;
      }
      return {
        ...prev,
        login_methods: prev.login_methods.map((method) =>
          method.provider === nextStatus.provider ? nextStatus : method,
        ),
      };
    });
  }, []);

  const loadProfile = useCallback(async () => {
    if (!token) {
      setProfile(null);
      setLoadingProfile(false);
      return;
    }
    setLoadingProfile(true);
    try {
      const data = await getProfile(token);
      setProfile(data);
      setFullName(data.full_name ?? "");
      setEmailField(data.email);
      setLinkIdentifiers((prev) => {
        const next: Record<string, string> = {};
        data.login_methods.forEach((method) => {
          next[method.provider] = prev[method.provider] ?? "";
        });
        return next;
      });
      setProfileError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        await logout();
        return;
      }
      const message = err instanceof ApiError ? err.message : "Unable to load profile.";
      setProfileError(message);
    } finally {
      setLoadingProfile(false);
    }
  }, [token, logout]);

  useEffect(() => {
    void loadProfile();
  }, [loadProfile]);

  const handleSaveProfile = useCallback(async () => {
    if (!token || !profile) {
      return;
    }
    setProfileSaving(true);
    try {
      const payload = {
        full_name: fullName.trim() === "" ? null : fullName.trim(),
        email: email.trim(),
      };
      const updated = await updateProfileRequest(token, payload);
      setProfile(updated);
      setFullName(updated.full_name ?? "");
      setEmailField(updated.email);
      await syncEmail(updated.email);
      if (!updated.is_confirmed) {
        Alert.alert("Email updated", "Please confirm the new address via the link we sent.");
      } else {
        Alert.alert("Profile updated", "Your profile details were saved.");
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        await logout();
        return;
      }
      const message = err instanceof ApiError ? err.message : "Unable to update profile.";
      Alert.alert("Update failed", message);
    } finally {
      setProfileSaving(false);
    }
  }, [token, profile, fullName, email, logout, syncEmail]);

  const handleChangePassword = useCallback(async () => {
    if (!token || !profile) {
      return;
    }
    if (newPassword !== confirmPassword) {
      Alert.alert("Password mismatch", "New password and confirmation must match.");
      return;
    }
    setPasswordSaving(true);
    try {
      const updated = await changePasswordRequest(token, {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setProfile(updated);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      Alert.alert("Password updated", "Your password has been updated.");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        await logout();
        return;
      }
      const message = err instanceof ApiError ? err.message : "Unable to change password.";
      Alert.alert("Update failed", message);
    } finally {
      setPasswordSaving(false);
    }
  }, [token, profile, currentPassword, newPassword, confirmPassword, logout]);

  const handleLinkProvider = useCallback(
    async (provider: string) => {
      if (!token || !profile) {
        return;
      }
      const rawIdentifier = linkIdentifiers[provider] ?? "";
      const trimmed = rawIdentifier.trim();
      if (!trimmed) {
        Alert.alert("Identifier required", "Enter an identifier before linking this provider.");
        return;
      }
      setProviderPending((prev) => ({ ...prev, [provider]: true }));
      try {
        const status = await linkLoginProvider(token, provider, trimmed);
        updateLoginMethod(status);
        setLinkIdentifiers((prev) => ({ ...prev, [provider]: "" }));
        Alert.alert("Linked", `${PROVIDER_LABELS[provider] ?? provider} account linked.`);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          await logout();
          return;
        }
        const message = err instanceof ApiError ? err.message : "Unable to link provider.";
        Alert.alert("Link failed", message);
      } finally {
        setProviderPending((prev) => ({ ...prev, [provider]: false }));
      }
    },
    [token, profile, linkIdentifiers, logout, updateLoginMethod],
  );

  const handleUnlinkProvider = useCallback(
    async (provider: string) => {
      if (!token || !profile) {
        return;
      }
      setProviderPending((prev) => ({ ...prev, [provider]: true }));
      try {
        const status = await unlinkLoginProvider(token, provider);
        updateLoginMethod(status);
        Alert.alert("Unlinked", `${PROVIDER_LABELS[provider] ?? provider} account unlinked.`);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          await logout();
          return;
        }
        const message = err instanceof ApiError ? err.message : "Unable to unlink provider.";
        Alert.alert("Unlink failed", message);
      } finally {
        setProviderPending((prev) => ({ ...prev, [provider]: false }));
      }
    },
    [token, profile, logout, updateLoginMethod],
  );

  if (loadingProfile) {
    return (
      <SafeAreaView style={styles.screen}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" />
        </View>
      </SafeAreaView>
    );
  }

  if (profileError) {
    return (
      <SafeAreaView style={styles.screen}>
        <Text style={styles.h1}>Profile</Text>
        <View style={styles.centered}>
          <Text style={styles.errorText}>{profileError}</Text>
          <View style={{ height: 12 }} />
          <Button title="Retry" onPress={() => void loadProfile()} />
        </View>
      </SafeAreaView>
    );
  }

  if (!profile) {
    return (
      <SafeAreaView style={styles.screen}>
        <View style={styles.centered}>
          <Text style={styles.muted}>We couldn’t load your profile right now.</Text>
          <View style={{ height: 12 }} />
          <Button title="Retry" onPress={() => void loadProfile()} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.screen}>
      <ScrollView contentContainerStyle={styles.profileScroll}>
        <Text style={styles.h1}>Profile</Text>
        <Text style={styles.muted}>Manage your account details and login methods.</Text>
        <View style={{ height: 16 }} />
        {!profile.is_confirmed && (
          <View style={styles.alertBox}>
            <Text style={styles.alertTitle}>Email confirmation required</Text>
            <Text style={styles.alertText}>
              We sent a confirmation link to {profile.email}. Confirm it before signing in again.
            </Text>
          </View>
        )}

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Basic information</Text>
          <View style={styles.formGroup}>
            <Text>Full name</Text>
            <TextInput
              style={styles.input}
              value={fullName}
              onChangeText={setFullName}
              placeholder="Jane Doe"
              editable={!profileSaving}
            />
          </View>
          <View style={styles.formGroup}>
            <Text>Email</Text>
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={setEmailField}
              autoCapitalize="none"
              keyboardType="email-address"
              editable={!profileSaving}
            />
          </View>
          <Button
            title={profileSaving ? "Saving..." : "Save changes"}
            onPress={() => void handleSaveProfile()}
            disabled={profileSaving}
          />
        </View>

        {profile.has_password && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Password</Text>
            <View style={styles.formGroup}>
              <Text>Current password</Text>
              <TextInput
                style={styles.input}
                value={currentPassword}
                onChangeText={setCurrentPassword}
                secureTextEntry
                editable={!passwordSaving}
              />
            </View>
            <View style={styles.formGroup}>
              <Text>New password</Text>
              <TextInput
                style={styles.input}
                value={newPassword}
                onChangeText={setNewPassword}
                secureTextEntry
                editable={!passwordSaving}
              />
            </View>
            <View style={styles.formGroup}>
              <Text>Confirm new password</Text>
              <TextInput
                style={styles.input}
                value={confirmPassword}
                onChangeText={setConfirmPassword}
                secureTextEntry
                editable={!passwordSaving}
              />
            </View>
            <Button
              title={passwordSaving ? "Updating..." : "Update password"}
              onPress={() => void handleChangePassword()}
              disabled={passwordSaving}
            />
          </View>
        )}

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Login methods</Text>
          {profile.login_methods.map((method) => {
            const label = PROVIDER_LABELS[method.provider] ?? method.provider;
            const pending = providerPending[method.provider] ?? false;
            return (
              <View key={method.provider} style={styles.methodBlock}>
                <Text style={styles.methodLabel}>{label}</Text>
                <Text style={styles.smallMuted}>
                  {method.linked
                    ? `Linked as ${method.identifier ?? "hidden identifier"}`
                    : "Not linked"}
                </Text>
                <View style={{ height: 8 }} />
                {method.linked ? (
                  <Button
                    title={pending ? "Unlinking..." : "Unlink"}
                    onPress={() => void handleUnlinkProvider(method.provider)}
                    disabled={pending}
                  />
                ) : (
                  <>
                    <TextInput
                      style={styles.input}
                      value={linkIdentifiers[method.provider] ?? ""}
                      onChangeText={(value) =>
                        setLinkIdentifiers((prev) => ({ ...prev, [method.provider]: value }))
                      }
                      placeholder="Identifier"
                      autoCapitalize="none"
                      editable={!pending}
                    />
                    <View style={{ height: 8 }} />
                    <Button
                      title={pending ? "Linking..." : "Link"}
                      onPress={() => void handleLinkProvider(method.provider)}
                      disabled={pending || !(linkIdentifiers[method.provider]?.trim())}
                    />
                  </>
                )}
              </View>
            );
          })}
        </View>

        <View style={{ height: 24 }} />
        <Button title="Logout" onPress={() => logout().catch(() => {})} />
      </ScrollView>
    </SafeAreaView>
  );
}

const Stack = createNativeStackNavigator();
const Tabs = createBottomTabNavigator();

function TabsNavigator() {
  return (
    <Tabs.Navigator>
      <Tabs.Screen name="Dashboard" component={DashboardScreen} />
      <Tabs.Screen name="Connections" component={ConnectionsScreen} />
      <Tabs.Screen name="Wizard" component={WizardScreen} />
      <Tabs.Screen name="Profile" component={ProfileScreen} />
    </Tabs.Navigator>
  );
}

function RootNavigator() {
  const auth = useAuth();

  if (auth.initializing) {
    return (
      <SafeAreaView style={styles.centered}>
        <ActivityIndicator size="large" />
      </SafeAreaView>
    );
  }

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {auth.token ? (
        <Stack.Screen name="Main" component={TabsNavigator} />
      ) : (
        <Stack.Screen name="Login" component={LoginScreen} />
      )}
    </Stack.Navigator>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <NavigationContainer>
        <RootNavigator />
      </NavigationContainer>
      <StatusBar style="auto" />
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#fff", padding: 16 },
  centered: { flex: 1, backgroundColor: "#fff", padding: 16, justifyContent: "center" },
  profileScroll: { padding: 16, paddingBottom: 48 },
  title: { fontSize: 24, fontWeight: "600", marginBottom: 24, textAlign: "center" },
  h1: { fontSize: 22, fontWeight: "600", marginBottom: 12 },
  formGroup: { marginBottom: 12 },
  input: { borderWidth: 1, borderColor: "#ddd", padding: 10, borderRadius: 6 },
  muted: { color: "#666", marginTop: 4 },
  smallMuted: { color: "#666", fontSize: 13 },
  rowBetween: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 12,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: "#eee",
  },
  card: { borderWidth: 1, borderColor: "#eee", borderRadius: 8, padding: 12, marginBottom: 12 },
  cardTitle: { fontWeight: "600", marginBottom: 4 },
  alertBox: {
    borderWidth: 1,
    borderColor: "#fcd34d",
    backgroundColor: "#fef3c7",
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
  },
  alertTitle: { fontWeight: "600", marginBottom: 4, color: "#92400e" },
  alertText: { color: "#92400e", fontSize: 13 },
  methodBlock: {
    borderWidth: 1,
    borderColor: "#eee",
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
    backgroundColor: "#fff",
  },
  methodLabel: { fontWeight: "600" },
  errorText: { color: "red", textAlign: "center" },
  toggleRow: { marginBottom: 16 },
});
