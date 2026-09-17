// Thin typed wrapper over fetch(). Cookies (the session) travel automatically
// since the UI and API share an origin in production and Vite proxies /api
// in dev -- credentials: "include" covers both cases.

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    credentials: "include",
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail ?? detail;
    } catch {
      // response wasn't JSON; fall back to statusText
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  del: <T>(path: string) => request<T>("DELETE", path),
};

// --- auth / setup ---

export interface SetupStatus {
  initialized: boolean;
}

export interface DefaultAdminInfo {
  username: string;
  password: string;
  note: string;
}

export interface LoginResponse {
  must_change_password: boolean;
  role: "admin" | "operator";
}

export interface ChangePasswordResponse {
  provisioning_uri: string;
}

export interface WhoAmI {
  role: "admin" | "operator";
  must_change_password: boolean;
}

export interface MigrateLegacyResponse {
  secrets_migrated: number;
  app_servers_migrated: number;
  users_migrated: number;
  skipped: number;
  failed: number;
  log: string[];
}

// --- servers ---

export interface ServerOut {
  id: number;
  system_id: string;
  label: string;
  is_active: boolean;
  active_until: string;
  ip_addresses: string[];
}

export interface PendingEnrollmentOut {
  id: number;
  system_id: string;
  ip_address: string;
  requested_at: string;
  attempts: number;
}

// --- users ---

export interface UserOut {
  id: number;
  email: string;
  role: "admin" | "operator";
  is_active: boolean;
  must_change_password: boolean;
  active_until: string;
}

export interface CreateUserResponse {
  provisioning_uri: string;
  temporary_password: string;
}

// --- secrets ---

export interface SecretOut {
  id: number;
  name: string;
  is_active: boolean;
  server_ids_with_access: number[];
}

// --- logs ---

export interface LogEntryOut {
  id: number;
  event_type: string;
  significant: boolean;
  details: string;
  timestamp: string;
}

// --- backup ---

export interface BackupExportResponse {
  data: Record<string, unknown>;
}
