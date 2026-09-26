import type { Tokens } from '../types';

const configured = String(process.env.EXPO_PUBLIC_API_URL || 'http://10.0.2.2:9090/api').replace(/\/$/, '');
export const API_URL = configured;
let session: Tokens | null = null;
let businessNumberId: number | null = null;
let onRefresh: ((tokens: Tokens) => Promise<void>) | null = null;
let onExpired: (() => Promise<void>) | null = null;

export class ApiError extends Error {
  constructor(message: string, public status: number, public body?: unknown) { super(message); }
}

export function configureApi(tokens: Tokens | null, refreshed: typeof onRefresh, expired: typeof onExpired) {
  session = tokens; onRefresh = refreshed; onExpired = expired;
}

/** Selects the WhatsApp workspace included with authenticated requests. */
export function configureWorkspace(id: number | null) {
  businessNumberId = id;
}

async function parse(response: Response) {
  const text = await response.text();
  if (!text) return null;
  try { return JSON.parse(text); } catch { return text; }
}

async function refreshAccess(): Promise<boolean> {
  if (!session?.refresh) return false;
  const response = await fetch(`${API_URL}/auth/refresh/`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh: session.refresh }),
  });
  if (!response.ok) return false;
  const data = await response.json();
  session = { access: data.access, refresh: data.refresh || session.refresh };
  await onRefresh?.(session);
  return true;
}

export async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  if (!API_URL) throw new ApiError('The mobile API URL is not configured.', 0);
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  if (session?.access) headers.set('Authorization', `Bearer ${session.access}`);
  if (businessNumberId !== null) headers.set('X-Business-Number-ID', String(businessNumberId));
  headers.set('Accept', 'application/json');
  let response: Response;
  try { response = await fetch(`${API_URL}${path}`, { ...init, headers }); }
  catch { throw new ApiError('Cannot reach the server. Check your connection and API URL.', 0); }
  if (response.status === 401 && retry && await refreshAccess()) return request<T>(path, init, false);
  const body = await parse(response);
  if (!response.ok) {
    if (response.status === 401) await onExpired?.();
    const message = typeof body === 'object' && body && 'detail' in body ? String((body as { detail: unknown }).detail) : `Request failed (${response.status})`;
    throw new ApiError(message, response.status, body);
  }
  return body as T;
}
