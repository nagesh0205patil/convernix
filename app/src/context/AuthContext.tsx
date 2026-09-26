import * as SecureStore from 'expo-secure-store';
import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { configureApi, request } from '../services/api';
import type { Tokens, User } from '../types';

const TOKEN_KEY = 'wavely.auth.tokens.v1';
type AuthValue = { user: User | null; loading: boolean; signIn: (username: string, password: string) => Promise<void>; signOut: () => Promise<void> };
const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: React.PropsWithChildren) {
  const [user, setUser] = useState<User | null>(null);
  const [tokens, setTokens] = useState<Tokens | null>(null);
  const [loading, setLoading] = useState(true);
  const persist = useCallback(async (next: Tokens) => { setTokens(next); await SecureStore.setItemAsync(TOKEN_KEY, JSON.stringify(next)); }, []);
  const signOut = useCallback(async () => { setTokens(null); setUser(null); await SecureStore.deleteItemAsync(TOKEN_KEY); }, []);

  useEffect(() => { configureApi(tokens, persist, signOut); }, [tokens, persist, signOut]);
  useEffect(() => {
    (async () => {
      try {
        const raw = await SecureStore.getItemAsync(TOKEN_KEY);
        if (!raw) return;
        const saved = JSON.parse(raw) as Tokens;
        configureApi(saved, persist, signOut);
        setTokens(saved);
        setUser(await request<User>('/auth/me/'));
      } catch { await signOut(); } finally { setLoading(false); }
    })();
  }, [persist, signOut]);

  const signIn = useCallback(async (username: string, password: string) => {
    const data = await request<Tokens & { user: User }>('/auth/login/', { method: 'POST', body: JSON.stringify({ username: username.trim(), password }) });
    await persist({ access: data.access, refresh: data.refresh });
    setUser(data.user);
  }, [persist]);
  const value = useMemo(() => ({ user, loading, signIn, signOut }), [user, loading, signIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error('useAuth must be inside AuthProvider'); return value; }
