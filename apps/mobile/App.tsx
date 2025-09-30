import { StatusBar } from "expo-status-bar";
import { useAppFonts } from './src/components/FontLoader';
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
  RefreshControl,
} from "react-native";
import Constants from "expo-constants";
import { NavigationContainer, useFocusEffect, useNavigation } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import * as WebBrowser from 'expo-web-browser';

// Import custom UI components
import CustomButton from './src/components/ui/Button';
import Input from './src/components/ui/Input';
import Card from './src/components/ui/Card';
import Switch from './src/components/ui/Switch';

// Import screens
import HistoryScreen from './src/components/HistoryScreen';
import ActivityLogScreen from './src/components/ActivityLogScreen';
import ConfirmScreen from './src/components/ConfirmScreen';

// Import design system
import { Colors } from './src/constants/colors';
import { TextStyles, FontFamilies } from './src/constants/typography';

// Import auth context and API utilities
import { AuthProvider, useAuth } from './src/contexts/AuthContext';
import { ExecutionLog } from './src/utils/api';

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

// Execution Logs (these will use the imported functions)
async function getExecutionLogsByArea(token: string, areaId: string): Promise<ExecutionLog[]> {
  return requestJson<ExecutionLog[]>(
    `/execution-logs/area/${areaId}`,
    {
      method: "GET",
    },
    token,
  );
}

async function getExecutionLogById(token: string, logId: string): Promise<ExecutionLog> {
  return requestJson<ExecutionLog>(
    `/execution-logs/${logId}`,
    {
      method: "GET",
    },
    token,
  );
}

async function getProfile(token: string): Promise<UserProfile> {
  return requestJson<UserProfile>("/users/me", {}, token);
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
      const frontendUrl = process.env.EXPO_PUBLIC_FRONTEND_URL;
      
      if (!apiUrl) {
        throw new Error('EXPO_PUBLIC_API_URL environment variable is not defined');
      }
      
      if (!frontendUrl) {
        throw new Error('EXPO_PUBLIC_FRONTEND_URL environment variable is not defined');
      }
      
      console.log('Starting OAuth flow...');
      console.log('OAuth URL:', `${apiUrl}/api/v1/oauth/google`);
      console.log('Return URL:', `${frontendUrl}/oauth/callback`);
      
      const result = await WebBrowser.openAuthSessionAsync(
        `${apiUrl}/api/v1/oauth/google`,
        `${frontendUrl}/oauth/callback`
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
    <SafeAreaView style={styles.screen}>
      <ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: 'center' }}>
        <Card style={{ margin: 16, backgroundColor: Colors.backgroundLight }}>
          <Text style={[styles.title, { fontFamily: FontFamilies.heading }]}>Action-Reaction</Text>
          <View style={styles.toggleRow}>
            <CustomButton
              title={mode === "login" ? "Need an account?" : "Have an account?"}
              onPress={() => setMode((prev) => (prev === "login" ? "register" : "login"))}
              variant="link"
            />
          </View>
          <View style={styles.formGroup}>
            <Text style={{ ...TextStyles.small, color: Colors.textDark, marginBottom: 4 }}>Email</Text>
            <Input
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              keyboardType="email-address"
              placeholder="Enter your email"
            />
          </View>
          <View style={styles.formGroup}>
            <Text style={{ ...TextStyles.small, color: Colors.textDark, marginBottom: 4 }}>Password</Text>
            <Input
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              placeholder="Enter your password"
            />
          </View>
          {error ? <Text style={styles.errorText}>{error}</Text> : null}
          <View style={styles.buttonContainer}>
            <CustomButton
              title={auth.loading ? "Please wait..." : mode === "login" ? "Log in" : "Create account"}
              onPress={submit}
              disabled={auth.loading}
              variant="default"
            />
          </View>
          <View style={{ height: 16 }} />
          <View style={styles.buttonContainer}>
            <CustomButton
              title="Sign in with Google"
              onPress={handleGoogleSignIn}
              variant="outline"
            />
          </View>
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
}

function DashboardScreen() {
  const auth = useAuth();
  const navigation = useNavigation<any>();
  const typedNavigation = useNavigation<any>();
  const [areas, setAreas] = useState<{ id: string; name: string; trigger: string; action: string; enabled: boolean }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [isRefreshing, setIsRefreshing] = useState(false);

  const loadAreas = useCallback(async () => {
    if (!auth.token) {
      return;
    }
    // Only show loading indicator if this is initial load
    const shouldShowLoading = areas.length === 0;
    if (shouldShowLoading) {
      setLoading(true);
    } else {
      setIsRefreshing(true);
    }
    
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
      setIsRefreshing(false);
    }
  }, [auth, areas.length]);

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

  if (loading && areas.length === 0) { // Only show full loading screen if no areas exist yet
    return (
      <SafeAreaView style={styles.screen}>
        <Text style={styles.h1}>Dashboard</Text>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={styles.screen}>
        <Text style={styles.h1}>Dashboard</Text>
        <Card style={{ margin: 16 }}>
          <Text style={styles.errorText}>{error}</Text>
          <View style={{ height: 12 }} />
          <CustomButton title="Retry" onPress={() => void loadAreas()} variant="outline" />
        </Card>
      </SafeAreaView>
    );
  }

  if (areas.length === 0) {
    return (
      <SafeAreaView style={styles.screen}>
        <Text style={styles.h1}>Dashboard</Text>
        <Card style={{ margin: 16 }}>
          <Text style={styles.muted}>You have no AREAs yet.</Text>
          <View style={{ height: 12 }} />
          <CustomButton 
            title="Create your first AREA" 
            onPress={() => navigation.navigate("Wizard") } 
            variant="default"
          />
        </Card>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.screen}>
      <Text style={styles.h1}>Dashboard</Text>
      <ScrollView 
        style={{ flex: 1, padding: 16 }}
        refreshControl={
          <RefreshControl refreshing={isRefreshing} onRefresh={loadAreas} />
        }
      >
        {areas.map((area) => (
          <Card key={area.id} style={{ marginBottom: 16 }}>
            <View style={styles.rowBetween}>
              <Text style={styles.cardTitle}>{area.name}</Text>
              <Text style={styles.smallMuted}>{area.enabled ? "Enabled" : "Disabled"}</Text>
            </View>
            <Text style={styles.muted}>When: {area.trigger}</Text>
            <Text style={styles.muted}>Then: {area.action}</Text>
            <View style={{ height: 12 }} />
            <View style={styles.rowBetween}>
              <CustomButton 
                title={area.enabled ? "Disable" : "Enable"} 
                onPress={() => void toggleArea(area.id, !area.enabled)} 
                variant={area.enabled ? "outline" : "default"}
                style={{ flex: 1, marginRight: 4 }}
              />
              <CustomButton 
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
                variant="destructive"
                style={{ flex: 1, marginLeft: 4 }}
              />
            </View>
            <View style={{ height: 8 }} />
            <Switch 
              value={area.enabled} 
              onValueChange={(value) => void toggleArea(area.id, value)} 
            />
          </Card>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

function ConnectionsScreen() {
  const auth = useAuth();
  const [services, setServices] = useState<{ id: string; name: string; description: string; connected: boolean; connection_id?: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [isRefreshing, setIsRefreshing] = useState(false);

  const loadServices = useCallback(async () => {
    if (!auth.token) {
      return;
    }
    // Only show loading indicator if this is initial load
    const shouldShowLoading = services.length === 0;
    if (shouldShowLoading) {
      setLoading(true);
    } else {
      setIsRefreshing(true);
    }
    
    try {
      // Load available services from catalog
      const servicesData = await requestJson<{ services: { slug: string; name: string; description: string }[] }>(
        "/services/services",
        { method: "GET" },
        auth.token,
      );

      // Load OAuth providers
      const providersData = await requestJson<{ providers: string[] }>(
        "/service-connections/providers",
        { method: "GET" },
        auth.token,
      );

      // Load existing connections
      const connectionsData = await requestJson<{ id: string; service_name: string; oauth_metadata?: any }[]>(
        "/users/me/connections",
        { method: "GET" },
        auth.token,
      );

      // Filter services to only show those with OAuth2 implementations
      // and merge with connection status
      const transformed = servicesData.services
        .filter((service) => providersData.providers.includes(service.slug))
        .map((service) => {
          const connection = connectionsData.find(
            (conn) => conn.service_name === service.slug
          );
          return {
            id: service.slug,
            name: service.name,
            description: service.description || "",
            connected: !!connection,
            connection_id: connection?.id,
          };
        });

      setServices(transformed);
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
      setIsRefreshing(false);
    }
  }, [auth, services.length]);

  useEffect(() => {
    void loadServices();
  }, [loadServices]);

  const testConnection = async (serviceId: string, connectionId: string) => {
    if (!auth.token) {
      return;
    }

    try {
      const testResult = await requestJson<{ success: boolean; [key: string]: unknown }>(
        `/service-connections/test/${serviceId}/${connectionId}`,
        { method: "GET" },
        auth.token,
      );

      if (testResult.success) {
        Alert.alert(`${serviceId} connection test successful!`);
      } else {
        Alert.alert(`${serviceId} connection test failed.`);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to test connection.";
      if (message.includes("401")) {
        await auth.logout();
        return;
      }
      Alert.alert("Test failed", message);
    }
  };

  const disconnectService = async (serviceId: string, connectionId: string) => {
    if (!auth.token) {
      return;
    }

    try {
      await requestJson(
        `/service-connections/connections/${connectionId}`,
        { method: "DELETE" },
        auth.token,
      );

      Alert.alert(`${serviceId} disconnected successfully.`);
      // Reload services to update connection status
      void loadServices();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to disconnect service.";
      if (message.includes("401")) {
        await auth.logout();
        return;
      }
      Alert.alert("Disconnect failed", message);
    }
  };

  if (loading && services.length === 0) { // Only show full loading screen if no services exist yet
    return (
      <SafeAreaView style={styles.screen}>
        <Text style={styles.h1}>Service Connection Hub</Text>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={styles.screen}>
        <Text style={styles.h1}>Service Connection Hub</Text>
        <Card style={{ margin: 16 }}>
          <Text style={styles.errorText}>{error}</Text>
          <View style={{ height: 12 }} />
          <CustomButton title="Retry" onPress={() => void loadServices()} variant="outline" />
        </Card>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.screen}>
      <Text style={styles.h1}>Service Connection Hub</Text>
      <ScrollView 
        style={{ flex: 1, padding: 16 }}
        refreshControl={
          <RefreshControl refreshing={isRefreshing} onRefresh={loadServices} />
        }
      >
        {services.map((s) => (
          <Card key={s.id} style={{ marginBottom: 16 }}>
            <View style={styles.rowBetween}>
              <View style={{ flex: 1, marginRight: 12 }}>
                <Text style={styles.cardTitle}>{s.name}</Text>
                <Text style={styles.muted}>{s.description}</Text>
              </View>
              <View style={{ alignItems: 'flex-end' }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 4 }}>
                  <View
                    style={{
                      backgroundColor: s.connected ? Colors.success : Colors.muted,
                      paddingHorizontal: 8,
                      paddingVertical: 4,
                      borderRadius: 4,
                      marginRight: 8,
                    }}
                  >
                    <Text style={{ color: Colors.backgroundLight, fontSize: 12 }}>
                      {s.connected ? "Connected" : "Not connected"}
                    </Text>
                  </View>
                </View>
                <View style={{ flexDirection: 'row' }}>
                  {s.connected ? (
                    <>
                      {s.connection_id && (
                        <CustomButton 
                          title="Test" 
                          onPress={() => testConnection(s.id, s.connection_id!)} 
                          variant="outline" 
                          style={{ marginRight: 8 }}
                        />
                      )}
                      <CustomButton 
                        title="Disconnect" 
                        onPress={() => s.connection_id && disconnectService(s.id, s.connection_id)}
                        variant="outline"
                      />
                    </>
                  ) : (
                    <CustomButton 
                      title="Connect" 
                      onPress={() => {}} 
                      variant="default"
                    />
                  )}
                </View>
              </View>
            </View>
          </Card>
        ))}
      </ScrollView>
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
      <ScrollView contentContainerStyle={{ padding: 16, flexGrow: 1 }}>
        <Card>
          <Text style={styles.h1}>AREA Creation Wizard</Text>
          <Text style={styles.muted}>Step {step} of 5</Text>
          
          {/* Step progress indicator */}
          <View style={{ flexDirection: "row", justifyContent: "space-between", marginVertical: 16 }}>
            {[1, 2, 3, 4, 5].map((s) => (
              <View key={s} style={{ alignItems: "center", flex: 1 }}>
                <View style={[
                  {
                    width: 32,
                    height: 32,
                    borderRadius: 16,
                    alignItems: "center",
                    justifyContent: "center",
                    backgroundColor: s === step ? Colors.primary : s < step ? Colors.success : Colors.muted,
                  }
                ]}>
                  <Text style={{ color: Colors.backgroundLight, fontWeight: "bold" }}>
                    {s}
                  </Text>
                </View>
                <Text style={[styles.smallMuted, { marginTop: 4, fontSize: 10, textAlign: "center" }]}>
                  {s === 1 && 'Trigger'}
                  {s === 2 && 'Action'}
                  {s === 3 && 'Reaction'}
                  {s === 4 && 'Confirm'}
                  {s === 5 && 'Review'}
                </Text>
              </View>
            ))}
          </View>

          {step === 1 && (
            <View style={{ marginBottom: 16 }}>
              <Text style={styles.cardTitle}>Step 1: Choose Trigger Service</Text>
              {SERVICES.map((s) => (
                <View key={s} style={{ marginBottom: 8 }}>
                  <CustomButton 
                    title={s} 
                    onPress={() => setTriggerService(s)} 
                    variant={triggerService === s ? "default" : "outline"}
                  />
                </View>
              ))}
              {triggerService ? <Text style={styles.muted}>Selected: {triggerService}</Text> : null}
            </View>
          )}

          {step === 2 && (
            <View style={{ marginBottom: 16 }}>
              <Text style={styles.cardTitle}>Step 2: Choose Trigger</Text>
              {(TRIGGERS_BY_SERVICE[triggerService] ?? []).map((t) => (
                <View key={t} style={{ marginBottom: 8 }}>
                  <CustomButton 
                    title={t} 
                    onPress={() => setTrigger(t)} 
                    variant={trigger === t ? "default" : "outline"}
                  />
                </View>
              ))}
              {trigger ? <Text style={styles.muted}>Selected: {trigger}</Text> : null}
            </View>
          )}

          {step === 3 && (
            <View style={{ marginBottom: 16 }}>
              <Text style={styles.cardTitle}>Step 3: Choose REAction Service</Text>
              {SERVICES.map((s) => (
                <View key={s} style={{ marginBottom: 8 }}>
                  <CustomButton 
                    title={s} 
                    onPress={() => setActionService(s)} 
                    variant={actionService === s ? "default" : "outline"}
                  />
                </View>
              ))}
              {actionService ? <Text style={styles.muted}>Selected: {actionService}</Text> : null}
            </View>
          )}

          {step === 4 && (
            <View style={{ marginBottom: 16 }}>
              <Text style={styles.cardTitle}>Step 4: Choose REAction</Text>
              {(ACTIONS_BY_SERVICE[actionService] ?? []).map((a) => (
                <View key={a} style={{ marginBottom: 8 }}>
                  <CustomButton 
                    title={a} 
                    onPress={() => setAction(a)} 
                    variant={action === a ? "default" : "outline"}
                  />
                </View>
              ))}
              {action ? <Text style={styles.muted}>Selected: {action}</Text> : null}
            </View>
          )}

          {step === 5 && (
            <View style={{ marginBottom: 16 }}>
              <Text style={styles.cardTitle}>Step 5: Review & Confirm</Text>
              <Text style={styles.muted}>
                If new "{trigger}" in {triggerService}, then "{action}" in {actionService}.
              </Text>
            </View>
          )}

          <View style={{ height: 16 }} />
          <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
            <CustomButton 
              title="Back" 
              onPress={() => setStep(Math.max(1, step - 1))} 
              variant="outline"
              disabled={step <= 1}
            />
            {step < 5 ? (
              <CustomButton 
                title="Next" 
                onPress={() => setStep(Math.min(step + 1, 5))} 
                disabled={!canNext || submitting}
              />
            ) : (
              <CustomButton 
                title={submitting ? "Creating..." : "Create AREA"} 
                onPress={() => void submit()} 
                disabled={submitting}
              />
            )}
          </View>
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
}

function ProfileScreen() {
  const auth = useAuth();
  const navigation = useNavigation();
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
      const data = await requestJson<UserProfile>("/users/me", {}, token);
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
      const updated = await requestJson<UserProfile>(
        "/users/me",
        {
          method: "PATCH",
          body: JSON.stringify(payload),
        },
        token,
      );
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
      const updated = await requestJson<UserProfile>(
        "/users/me/password",
        {
          method: "POST",
          body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword,
          }),
        },
        token,
      );
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
        const status = await requestJson<LoginMethodStatus>(
          `/users/me/login-methods/${provider}`,
          {
            method: "POST",
            body: JSON.stringify({ identifier: trimmed }),
          },
          token,
        );
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
        const status = await requestJson<LoginMethodStatus>(
          `/users/me/login-methods/${provider}`,
          {
            method: "DELETE",
          },
          token,
        );
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
            <View style={{ height: 8 }} />
            <CustomButton 
              title="Resend confirmation email" 
              onPress={async () => {
                try {
                  await requestJson(`/auth/confirm/resend`, {
                    method: "POST",
                    body: JSON.stringify({ email: profile.email }),
                  }, token);
                  Alert.alert("Email sent", "A new confirmation email has been sent.");
                } catch (error: any) {
                  Alert.alert("Error", error.message || "Failed to resend confirmation email.");
                }
              }} 
              variant="outline" 
            />
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

        <View style={{ height: 12 }} />
        <CustomButton title="Activity Log" onPress={() => navigation.navigate("ActivityLog" as never)} variant="default" />
        <View style={{ height: 12 }} />
        <CustomButton title="Logout" onPress={() => logout().catch(() => {})} variant="outline" />
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
      <Tabs.Screen name="History" component={HistoryScreen} />
      <Tabs.Screen name="Connections" component={ConnectionsScreen} />
      <Tabs.Screen name="Wizard" component={WizardScreen} />
      <Tabs.Screen name="Profile" component={ProfileScreen} />
    </Tabs.Navigator>
  );
}

function AuthenticatedNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="MainTabs" component={TabsNavigator} />
      <Stack.Screen name="ActivityLog" component={ActivityLogScreen} />
      <Stack.Screen name="Confirm" component={ConfirmScreen} />
    </Stack.Navigator>
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
        <Stack.Screen name="Authenticated" component={AuthenticatedNavigator} />
      ) : (
        <Stack.Screen name="Login" component={LoginScreen} />
      )}
    </Stack.Navigator>
  );
}

export default function App() {
  const fontsLoaded = useAppFonts();

  if (!fontsLoaded) {
    return (
      <SafeAreaView style={styles.centered}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </SafeAreaView>
    );
  }

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
  screen: { 
    flex: 1, 
    backgroundColor: Colors.backgroundLight, 
    padding: 16,
    fontFamily: FontFamilies.body
  },
  centered: { 
    flex: 1, 
    backgroundColor: Colors.backgroundLight, 
    padding: 16, 
    justifyContent: "center",
    fontFamily: FontFamilies.body
  },
  profileScroll: { 
    padding: 16, 
    paddingBottom: 48,
    backgroundColor: Colors.backgroundLight,
    fontFamily: FontFamilies.body
  },
  title: { 
    ...TextStyles.h1,
    color: Colors.textDark,
    marginBottom: 24, 
    textAlign: "center",
    fontFamily: FontFamilies.heading
  },
  h1: { 
    ...TextStyles.h2,
    color: Colors.textDark,
    marginBottom: 12,
    fontFamily: FontFamilies.heading
  },
  h2: { 
    ...TextStyles.h3,
    color: Colors.textDark,
    marginBottom: 12,
    fontFamily: FontFamilies.body
  },
  formGroup: { 
    marginBottom: 16,
    fontFamily: FontFamilies.body
  },
  input: { 
    borderWidth: 1, 
    borderColor: Colors.input, 
    padding: 12, 
    borderRadius: 6,
    backgroundColor: Colors.backgroundLight,
    color: Colors.textDark,
    ...TextStyles.body,
    fontFamily: FontFamilies.body
  },
  muted: { 
    color: Colors.mutedForeground, 
    marginTop: 4,
    ...TextStyles.small,
    fontFamily: FontFamilies.body
  },
  smallMuted: { 
    color: Colors.mutedForeground, 
    ...TextStyles.small,
    fontFamily: FontFamilies.body
  },
  rowBetween: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 12,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    fontFamily: FontFamilies.body
  },
  card: { 
    borderWidth: 1, 
    borderColor: Colors.border, 
    borderRadius: 8, 
    padding: 16, 
    marginBottom: 16,
    backgroundColor: Colors.cardLight,
    fontFamily: FontFamilies.body
  },
  cardTitle: { 
    ...TextStyles.h3,
    color: Colors.textDark,
    marginBottom: 8,
    fontFamily: FontFamilies.body
  },
  alertBox: {
    borderWidth: 1,
    borderColor: Colors.warning,
    backgroundColor: Colors.backgroundLight,
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
    fontFamily: FontFamilies.body
  },
  alertTitle: { 
    ...TextStyles['body-bold'], 
    marginBottom: 4, 
    color: Colors.warning,
    fontFamily: FontFamilies.body
  },
  alertText: { 
    color: Colors.warning, 
    ...TextStyles.small,
    fontFamily: FontFamilies.body
  },
  methodBlock: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
    backgroundColor: Colors.cardLight,
    fontFamily: FontFamilies.body
  },
  methodLabel: { 
    ...TextStyles['body-bold'],
    color: Colors.textDark,
    fontFamily: FontFamilies.body
  },
  errorText: { 
    color: Colors.error, 
    textAlign: "center",
    ...TextStyles.small,
    fontFamily: FontFamilies.body
  },
  toggleRow: { 
    marginBottom: 16,
    fontFamily: FontFamilies.body
  },
  buttonContainer: {
    marginVertical: 8,
  }
});
