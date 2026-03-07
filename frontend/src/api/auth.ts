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

export async function apiForgotPassword(email: string): Promise<void> {
  const res = await fetch(`${USERS_API}/auth/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.detail ?? 'Error al enviar el correo');
  }
}

export async function apiResetPassword(token: string, new_password: string): Promise<void> {
  const res = await fetch(`${USERS_API}/auth/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, new_password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.detail ?? 'Error al restablecer la contraseña');
  }
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
