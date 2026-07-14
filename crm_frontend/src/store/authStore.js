import { create } from 'zustand';

export const useAuthStore = create((set) => ({
  agent: null,
  token: null,
  isAuthenticated: false,
  setAuth: (agent, token) => set({ agent, token, isAuthenticated: true }),
  logoutAgent: () => set({ agent: null, token: null, isAuthenticated: false }),
}));