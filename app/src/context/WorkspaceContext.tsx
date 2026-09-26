import * as SecureStore from 'expo-secure-store';
import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { configureWorkspace, request } from '../services/api';
import { useAuth } from './AuthContext';

const WORKSPACE_KEY = 'wavely.workspace.id.v1';

export type BusinessNumber = {
  id: number;
  number: string;
  label: string;
  default_team: string;
};

type WorkspaceValue = {
  numbers: BusinessNumber[];
  selected: BusinessNumber | null;
  loading: boolean;
  error: string;
  select: (number: BusinessNumber) => Promise<void>;
  refresh: () => Promise<void>;
};

const WorkspaceContext = createContext<WorkspaceValue | null>(null);

export function WorkspaceProvider({ children }: React.PropsWithChildren) {
  const { user } = useAuth();
  const [numbers, setNumbers] = useState<BusinessNumber[]>([]);
  const [selected, setSelected] = useState<BusinessNumber | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const select = useCallback(async (number: BusinessNumber) => {
    configureWorkspace(number.id);
    setSelected(number);
    await SecureStore.setItemAsync(WORKSPACE_KEY, String(number.id));
  }, []);

  const refresh = useCallback(async () => {
    if (!user) {
      configureWorkspace(null); setNumbers([]); setSelected(null); setError(''); setLoading(false);
      return;
    }
    setLoading(true); setError('');
    try {
      const available = await request<BusinessNumber[]>('/whatsapp/business-numbers/');
      setNumbers(available);
      const saved = await SecureStore.getItemAsync(WORKSPACE_KEY);
      const savedId = saved ? Number(saved) : null;
      const restored = available.find(item => item.id === savedId) || (available.length === 1 ? available[0] : null);
      configureWorkspace(restored?.id ?? null);
      setSelected(restored);
      if (!available.length) setError('No WhatsApp business numbers are available for this account.');
    } catch (error) {
      configureWorkspace(null); setSelected(null);
      setError(error instanceof Error ? error.message : 'Unable to load WhatsApp workspaces.');
    } finally { setLoading(false); }
  }, [user]);

  useEffect(() => { refresh(); }, [refresh]);
  const value = useMemo(() => ({ numbers, selected, loading, error, select, refresh }), [numbers, selected, loading, error, select, refresh]);
  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error('useWorkspace must be inside WorkspaceProvider');
  return value;
}
