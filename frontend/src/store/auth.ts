import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Role = 'manufacturer' | 'reviewer' | 'admin';

interface AuthState {
  token: string | null;
  role: Role | null;
  username: string | null;
  setAuth: (token: string, role: Role, username: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      role: null,
      username: null,
      setAuth: (token, role, username) => set({ token, role, username }),
      clearAuth: () => set({ token: null, role: null, username: null }),
    }),
    { name: 'packopt-auth' }
  )
);
