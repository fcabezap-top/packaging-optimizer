/**
 * Wrapper sobre fetch que intercepta respuestas 401.
 * Si el token ha expirado o es inválido, limpia la sesión y redirige al login.
 */
import { useAuthStore } from '../store/auth';

export async function safeFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const res = await fetch(input, init);
  if (res.status === 401) {
    useAuthStore.getState().clearAuth();
    window.location.href = '/login';
  }
  return res;
}
