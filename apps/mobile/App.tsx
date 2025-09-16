import { StatusBar } from "expo-status-bar";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Button,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";

const API_BASE_URL = (process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8080/api/v1").replace(/\/$/, "");
const STORAGE_KEY = "area_mobile_session";

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

  const response = await fetch(url, { ...options, headers });
  if (response.status === 401) {
    throw new Error("unauthorized");
  }
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as T;
}

type AuthContextValue = {
  token: string | null;
  email: string | null;
  initializing: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
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
        if (error instanceof Error && error.message !== "unauthorized") {
          throw error;
        }
        throw new Error("Unable to log in. Please check your credentials.");
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
        const data = await requestJson<{ access_token: string }>(
          "/auth/login",
          {
            method: "POST",
            body: JSON.stringify({ email: registerEmail, password }),
          },
        );
        await persistSession(data.access_token, registerEmail);
      } catch (error) {
        if (error instanceof Error && error.message !== "unauthorized") {
          throw error;
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

  const value = useMemo<AuthContextValue>(
    () => ({ token, email, initializing, loading, login, register, logout }),
    [email, initializing, loading, login, logout, register, token],
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
        Alert.alert("Account created", "You are now signed in.");
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Something went wrong.";
      setError(message);
      Alert.alert("Authentication failed", message);
    }
  }, [auth, email, mode, password]);

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
    </SafeAreaView>
  );
}

function DashboardScreen() {
  return (
    <SafeAreaView style={styles.screen}>
      <Text style={styles.h1}>Dashboard</Text>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Save Gmail invoices to Drive</Text>
        <Text style={styles.muted}>When: Gmail - New Email w/ 'Invoice'</Text>
        <Text style={styles.muted}>Then: Drive - Upload Attachment</Text>
        <View style={{ height: 8 }} />
        <Button title="Create AREA" onPress={() => {}} />
      </View>
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
      if (message === "unauthorized") {
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
  const [step, setStep] = useState(1);
  return (
    <SafeAreaView style={styles.screen}>
      <Text style={styles.h1}>AREA Creation Wizard</Text>
      <Text style={styles.muted}>Step {step} of 5</Text>
      <View style={{ height: 12 }} />
      <Button title="Next" onPress={() => setStep(Math.min(step + 1, 5))} />
    </SafeAreaView>
  );
}

function AccountScreen() {
  const auth = useAuth();
  return (
    <SafeAreaView style={styles.screen}>
      <Text style={styles.h1}>Account</Text>
      <View style={styles.formGroup}>
        <Text>Name</Text>
        <TextInput style={styles.input} defaultValue="Jane Doe" />
      </View>
      <View style={styles.formGroup}>
        <Text>Email</Text>
        <TextInput style={styles.input} value={auth.email ?? ""} editable={false} />
      </View>
      <Button title="Logout" onPress={() => auth.logout().catch(() => {})} />
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
      <Tabs.Screen name="Account" component={AccountScreen} />
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
  title: { fontSize: 24, fontWeight: "600", marginBottom: 24, textAlign: "center" },
  h1: { fontSize: 22, fontWeight: "600", marginBottom: 12 },
  formGroup: { marginBottom: 12 },
  input: { borderWidth: 1, borderColor: "#ddd", padding: 10, borderRadius: 6 },
  muted: { color: "#666", marginTop: 4 },
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
  errorText: { color: "red", textAlign: "center" },
  toggleRow: { marginBottom: 16 },
});
