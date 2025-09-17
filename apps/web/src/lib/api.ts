"use client";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8080/api/v1";

const SESSION_STORAGE_KEY = "area_auth_session";

type StoredSession = {
  token: string;
  email?: string;
};

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export class UnauthorizedError extends ApiError {
  constructor(message = "Unauthorized") {
    super(401, message);
    this.name = "UnauthorizedError";
  }
}

export function loadStoredSession(): StoredSession | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(SESSION_STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as StoredSession;
  } catch {
    window.localStorage.removeItem(SESSION_STORAGE_KEY);
    return null;
  }
}

export function saveStoredSession(session: StoredSession | null): void {
  if (typeof window === "undefined") {
    return;
  }
  if (!session) {
    window.localStorage.removeItem(SESSION_STORAGE_KEY);
  } else {
    window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
  }
}

function resolveUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  if (!path.startsWith("/")) {
    return `${API_BASE_URL}/${path}`;
  }
  return `${API_BASE_URL}${path}`;
}

function buildHeaders(initHeaders?: HeadersInit): Headers {
  const headers = new Headers(initHeaders);
  return headers;
}

export async function authFetch(
  path: string,
  init: RequestInit = {},
  token?: string | null,
): Promise<Response> {
  const url = resolveUrl(path);
  const headers = buildHeaders(init.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const bodyIsJson = init.body && !(init.body instanceof FormData) && !headers.has("Content-Type");
  if (bodyIsJson) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(url, {
    ...init,
    headers,
  });
  if (response.status === 401) {
    throw new UnauthorizedError();
  }
  return response;
}

async function parseErrorMessage(response: Response): Promise<string> {
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
        const firstDetail = data.detail[0];
        if (typeof firstDetail === "string") {
          return firstDetail;
        }
        if (firstDetail?.msg) {
          return firstDetail.msg as string;
        }
      }
    }
  } catch {
    // ignore parsing errors
  }
  return `Request failed with status ${response.status}`;
}

export async function requestJson<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const response = await authFetch(path, options, token);
  if (!response.ok) {
    const message = await parseErrorMessage(response);
    throw new ApiError(response.status, message);
  }
  return (await response.json()) as T;
}

export type LoginResponse = {
  access_token: string;
  token_type: string;
};

export type UserResponse = {
  id: string;
  email: string;
  created_at: string;
  updated_at: string;
};

export type LoginMethodStatus = {
  provider: string;
  linked: boolean;
  identifier?: string | null;
};

export type UserProfile = {
  email: string;
  full_name?: string | null;
  is_confirmed: boolean;
  has_password: boolean;
  login_methods: LoginMethodStatus[];
};

export type UserProfileUpdatePayload = {
  full_name?: string | null;
  email?: string;
};

export type PasswordChangePayload = {
  current_password: string;
  new_password: string;
};

export async function fetchProfile(token: string): Promise<UserProfile> {
  return requestJson<UserProfile>("/users/me", {}, token);
}

export async function updateProfile(
  token: string,
  payload: UserProfileUpdatePayload,
): Promise<UserProfile> {
  return requestJson<UserProfile>(
    "/users/me",
    {
      method: 'PATCH',
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function changePassword(
  token: string,
  payload: PasswordChangePayload,
): Promise<UserProfile> {
  return requestJson<UserProfile>(
    "/users/me/password",
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function linkLoginMethod(
  token: string,
  provider: string,
  identifier: string,
): Promise<LoginMethodStatus> {
  return requestJson<LoginMethodStatus>(
    `/users/me/login-methods/${provider}`,
    {
      method: 'POST',
      body: JSON.stringify({ identifier }),
    },
    token,
  );
}

// Areas
export type AreaCreatePayload = {
  name: string;
  trigger_service: string;
  trigger_action: string;
  reaction_service: string;
  reaction_action: string;
};

export type AreaResponse = {
  id: string;
  user_id: string;
  name: string;
  trigger_service: string;
  trigger_action: string;
  reaction_service: string;
  reaction_action: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
};

export async function createArea(
  token: string,
  payload: AreaCreatePayload,
): Promise<AreaResponse> {
  return requestJson<AreaResponse>(
    "/areas",
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function deleteArea(
  token: string,
  areaId: string,
): Promise<boolean> {
  return requestJson<boolean>(
    `/areas/${areaId}`,
    {
      method: 'DELETE',
    },
    token,
  );
}

export async function unlinkLoginMethod(
  token: string,
  provider: string,
): Promise<LoginMethodStatus> {
  return requestJson<LoginMethodStatus>(
    `/users/me/login-methods/${provider}`,
    {
      method: 'DELETE',
    },
    token,
  );
}
