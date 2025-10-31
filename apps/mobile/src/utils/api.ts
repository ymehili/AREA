// Shared API utilities and types for the mobile app
import { Platform } from 'react-native';

export type ExecutionLog = {
  id: string;
  area_id: string;
  status: string;
  output: string | null;
  error_message: string | null;
  step_details: Record<string, unknown> | null;
  timestamp: string;
  created_at: string;
};

export type UserActivityLog = {
  id: string;
  timestamp: string;
  action_type: string;
  service_name: string | null;
  details: string | null;
  status: "success" | "failed" | "pending";
  created_at: string;
};

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
  }
}

export async function parseError(response: Response): Promise<string> {
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
  const API_BASE_URL = resolveApiBaseUrl();
  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  console.log('Making API request to:', url);
  console.log('Method:', options.method || 'GET');
  console.log('Body:', options.body);
  
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
    console.log('Response status:', response.status);
  } catch (networkError) {
    console.log('Network error:', networkError);
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
    const errorMessage = await parseError(response);
    console.log('API error:', response.status, errorMessage);
    throw new ApiError(response.status, errorMessage);
  }
  return (await response.json()) as T;
}

function resolveApiBaseUrl(): string {
  const explicit = process.env.EXPO_PUBLIC_API_URL;
  console.log('EXPO_PUBLIC_API_URL:', explicit);
  
  // Platform-specific handling
  const Platform = require('react-native').Platform;
  
  if (explicit && typeof explicit === "string" && explicit.trim() !== "") {
    let url = explicit.replace(/\/$/, "");
    console.log('Using explicit API URL:', url);
    
    // If the explicit URL uses localhost, adjust it for the platform
    // This ensures Android uses 10.0.2.2 and iOS uses localhost
    if (Platform.OS === "android" && url.includes("localhost")) {
      url = url.replace("localhost", "10.0.2.2");
      console.log('Adjusted for Android:', url);
    } else if (Platform.OS === "ios" && url.includes("10.0.2.2")) {
      url = url.replace("10.0.2.2", "localhost");
      console.log('Adjusted for iOS:', url);
    }
    
    return url;
  }
  
  // Platform-specific defaults
  // Emulators
  if (Platform.OS === "android") {
    // Android emulator maps host loopback to 10.0.2.2
    const url = "http://10.0.2.2:8080/api/v1";
    console.log('Using Android default API URL:', url);
    return url;
  }
  // iOS Simulator usually reaches host via localhost
  const url = "http://localhost:8080/api/v1";
  console.log('Using iOS default API URL:', url);
  return url;
}

async function getExecutionLogsForUser(token: string): Promise<ExecutionLog[]> {
  return requestJson<ExecutionLog[]>(
    "/execution-logs",
    {
      method: "GET",
    },
    token,
  );
}

async function getUserActivities(token: string): Promise<UserActivityLog[]> {
  return requestJson<UserActivityLog[]>(
    "/user-activities",
    {
      method: "GET",
    },
    token,
  );
}

export { requestJson, getExecutionLogsForUser, getUserActivities, resolveApiBaseUrl };