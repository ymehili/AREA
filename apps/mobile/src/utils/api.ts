// Shared API utilities and types for the mobile app

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
  if (explicit && typeof explicit === "string" && explicit.trim() !== "") {
    const url = explicit.replace(/\/$/, "");
    console.log('Using explicit API URL:', url);
    return url;
  }
  // Platform-specific defaults
  // Note: We need to import Platform from react-native at the top of the file
  const Platform = require('react-native').Platform;
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

export { requestJson, getExecutionLogsForUser, resolveApiBaseUrl };