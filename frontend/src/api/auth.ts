const USERS_API = import.meta.env.VITE_USERS_API ?? 'http://localhost:8001';

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export async function apiLogin(username: string, password: string): Promise<LoginResponse> {
  const body = new URLSearchParams({ username, password });
  const res = await fetch(`${USERS_API}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.detail ?? 'Credenciales incorrectas');
  }
  return res.json();
}

// Decode JWT payload (no verification — only for reading role/username client-side)
export function decodeJwtPayload(token: string): Record<string, unknown> {
  try {
    const payload = token.split('.')[1];
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
  } catch {
    return {};
  }
}
