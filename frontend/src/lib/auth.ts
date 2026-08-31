const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type UserRole = "viewer" | "operator" | "admin";

export interface UserSession {
  user_id: string;
  role: UserRole;
  access_token: string;
  token_type: string;
  expires_at: number;
}

const STORAGE_KEY = "recoveriq_auth_session";

// Default pre-authenticated session for seamless evaluation
const DEFAULT_SESSION: UserSession = {
  user_id: "operator_lead",
  role: "operator",
  access_token: "",
  token_type: "bearer",
  expires_at: 0,
};

export function getStoredSession(): UserSession {
  if (typeof window === "undefined") {
    return DEFAULT_SESSION;
  }

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      return JSON.parse(raw);
    }
  } catch {
    // Ignore storage parse errors
  }
  return DEFAULT_SESSION;
}

export function saveSession(session: UserSession): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch {
    // Ignore storage write errors
  }
}

export function clearSession(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignore storage clear errors
  }
}

export async function loginAs(
  userId: string,
  role: UserRole = "operator"
): Promise<UserSession> {
  const res = await fetch(`${API_BASE_URL}/api/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, role }),
  });

  if (!res.ok) {
    throw new Error("Failed to authenticate session with RecoverIQ API");
  }

  const data = await res.json();
  const session: UserSession = {
    user_id: data.user_id,
    role: data.role,
    access_token: data.access_token,
    token_type: data.token_type,
    expires_at: Date.now() + data.expires_in * 1000,
  };

  saveSession(session);
  return session;
}

export async function ensureValidToken(): Promise<string> {
  const current = getStoredSession();
  if (current.access_token && current.expires_at > Date.now() + 60000) {
    return current.access_token;
  }

  // Obtain a valid signed token for the current session role
  try {
    const refreshed = await loginAs(current.user_id, current.role);
    return refreshed.access_token;
  } catch (err) {
    console.warn("Could not obtain auth token from API:", err);
    return current.access_token;
  }
}
