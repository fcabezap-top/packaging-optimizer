import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Role = 'manufacturer' | 'reviewer' | 'admin';

interface AuthState {
  token: string | null;
  role: Role | null;
  username: string | null;
  fullName: string | null;
  _hasHydrated: boolean;
  setAuth: (token: string, role: Role, username: string, fullName: string) => void;
  clearAuth: () => void;
  setHasHydrated: (v: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      role: null,
      username: null,
      fullName: null,
      _hasHydrated: false,
      setAuth: (token, role, username, fullName) => set({ token, role, username, fullName }),
      clearAuth: () => set({ token: null, role: null, username: null, fullName: null }),
      setHasHydrated: (v) => set({ _hasHydrated: v }),
    }),
    {
      name: 'packopt-auth',
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
