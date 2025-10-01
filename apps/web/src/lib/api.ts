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

export class ExecutionLogError extends ApiError {
  constructor(status: number, message: string) {
    super(status, message);
    this.name = "ExecutionLogError";
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
  is_admin: boolean;
  created_at: string;
  updated_at: string;
};

export type LoginMethodStatus = {
  provider: string;
  linked: boolean;
  identifier?: string | null;
};

export type UserProfile = {
  id: string;
  email: string;
  full_name?: string | null;
  is_confirmed: boolean;
  is_admin: boolean;
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

// Execution Logs
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

export type ExecutionLogCreatePayload = {
  area_id: string;
  status: string;
  output?: string | null;
  error_message?: string | null;
  step_details?: Record<string, unknown> | null;
};

export type ExecutionLogUpdatePayload = {
  status?: string;
  output?: string | null;
  error_message?: string | null;
  step_details?: Record<string, unknown> | null;
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
  description?: string;
  is_active?: boolean;
};

export type AreaResponse = {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  trigger_service: string;
  trigger_action: string;
  reaction_service: string;
  reaction_action: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
};

// Area Steps
export type AreaStepType = 'trigger' | 'action' | 'reaction' | 'condition' | 'delay';

export type AreaStepCreatePayload = {
  area_id: string;
  step_type: AreaStepType;
  order: number;
  service?: string | null;
  action?: string | null;
  config?: Record<string, unknown>;
};

export type AreaStepUpdatePayload = {
  step_type?: AreaStepType;
  order?: number;
  service?: string | null;
  action?: string | null;
  config?: Record<string, unknown>;
};

export type AreaStepResponse = {
  id: string;
  area_id: string;
  step_type: AreaStepType;
  order: number;
  service?: string | null;
  action?: string | null;
  config?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AreaWithStepsResponse = AreaResponse & {
  steps: AreaStepResponse[];
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

export async function createAreaWithSteps(
  token: string,
  payload: AreaCreatePayload & { steps: Omit<AreaStepCreatePayload, 'area_id'>[] },
): Promise<AreaWithStepsResponse> {
  return requestJson<AreaWithStepsResponse>(
    "/areas/with-steps",
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function getAreaWithSteps(
  token: string,
  areaId: string,
): Promise<AreaWithStepsResponse> {
  return requestJson<AreaWithStepsResponse>(
    `/areas/${areaId}`,
    {
      method: 'GET',
    },
    token,
  );
}

export async function updateArea(
  token: string,
  areaId: string,
  payload: Partial<AreaCreatePayload>,
): Promise<AreaResponse> {
  return requestJson<AreaResponse>(
    `/areas/${areaId}`,
    {
      method: 'PATCH',
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

// Area Steps API
export async function createAreaStep(
  token: string,
  payload: AreaStepCreatePayload,
): Promise<AreaStepResponse> {
  return requestJson<AreaStepResponse>(
    "/areas/steps",
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function getAreaSteps(
  token: string,
  areaId: string,
): Promise<AreaStepResponse[]> {
  return requestJson<AreaStepResponse[]>(
    `/areas/${areaId}/steps`,
    {
      method: 'GET',
    },
    token,
  );
}

export async function getAreaStep(
  token: string,
  stepId: string,
): Promise<AreaStepResponse> {
  return requestJson<AreaStepResponse>(
    `/areas/steps/${stepId}`,
    {
      method: 'GET',
    },
    token,
  );
}

export async function updateAreaStep(
  token: string,
  stepId: string,
  payload: AreaStepUpdatePayload,
): Promise<AreaStepResponse> {
  return requestJson<AreaStepResponse>(
    `/areas/steps/${stepId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function deleteAreaStep(
  token: string,
  stepId: string,
): Promise<boolean> {
  return requestJson<boolean>(
    `/areas/steps/${stepId}`,
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

// Execution Logs API Functions
export async function getExecutionLogsForUser(token: string): Promise<ExecutionLog[]> {
  return requestJson<ExecutionLog[]>(
    "/execution-logs",
    {
      method: "GET",
    },
    token,
  );
}

export async function getExecutionLogsByArea(token: string, areaId: string): Promise<ExecutionLog[]> {
  return requestJson<ExecutionLog[]>(
    `/areas/${areaId}/execution-logs`,
    {
      method: "GET",
    },
    token,
  );
}

export async function getExecutionLogById(token: string, logId: string): Promise<ExecutionLog> {
  return requestJson<ExecutionLog>(
    `/execution-logs/${logId}`,
    {
      method: "GET",
    },
    token,
  );
}

// Admin API Functions
export type AdminUserResponse = {
  id: string;
  email: string;
  is_admin: boolean;
  created_at: string;
  is_confirmed: boolean;
};

export type PaginatedUsersResponse = {
  users: AdminUserResponse[];
  total_count: number;
  skip: number;
  limit: number;
};

export async function getAdminUsers(
  token: string,
  skip: number = 0,
  limit: number = 100,
  search?: string,
  sort_field: string = "created_at",
  sort_direction: string = "desc"
): Promise<PaginatedUsersResponse> {
  const params = new URLSearchParams({
    skip: skip.toString(),
    limit: limit.toString(),
    search: search || "",
    sort_field,
    sort_direction,
  });

  return requestJson<PaginatedUsersResponse>(
    `/admin/users?${params.toString()}`,
    {
      method: "GET",
    },
    token,
  );
}

export async function updateAdminStatus(
  token: string,
  userId: string,
  isAdmin: boolean,
): Promise<AdminUserResponse> {
  return requestJson<AdminUserResponse>(
    `/admin/users/${userId}/admin-status`,
    {
      method: "PUT",
      body: JSON.stringify({ is_admin: isAdmin }),
    },
    token,
  );
}

// New admin API functions for user management
export type ServiceConnectionForUserDetail = {
  id: string;
  service_name: string;
  created_at: string;
};

export type AreaForUserDetail = {
  id: string;
  name: string;
  trigger_service: string;
  reaction_service: string;
  enabled: boolean;
  created_at: string;
};

export type UserDetailAdminResponse = {
  id: string;
  email: string;
  full_name: string | null;
  is_confirmed: boolean;
  is_admin: boolean;
  is_suspended: boolean;
  created_at: string;
  confirmed_at: string | null;
  service_connections: ServiceConnectionForUserDetail[];
  areas: AreaForUserDetail[];
};

export type AdminActionResponse = {
  id?: string;
  email?: string;
  is_confirmed?: boolean;
  is_suspended?: boolean;
  message: string;
};

export async function getUserDetail(
  token: string,
  userId: string,
): Promise<UserDetailAdminResponse> {
  return requestJson<UserDetailAdminResponse>(
    `/admin/users/${userId}`,
    {
      method: "GET",
    },
    token,
  );
}

export async function confirmUserEmail(
  token: string,
  userId: string,
): Promise<AdminActionResponse> {
  return requestJson<AdminActionResponse>(
    `/admin/users/${userId}/confirm-email`,
    {
      method: "POST",
    },
    token,
  );
}

export async function suspendUserAccount(
  token: string,
  userId: string,
): Promise<AdminActionResponse> {
  return requestJson<AdminActionResponse>(
    `/admin/users/${userId}/suspend`,
    {
      method: "PUT",
    },
    token,
  );
}

export async function deleteUserAccount(
  token: string,
  userId: string,
): Promise<AdminActionResponse> {
  return requestJson<AdminActionResponse>(
    `/admin/users/${userId}`,
    {
      method: "DELETE",
    },
    token,
  );
}
