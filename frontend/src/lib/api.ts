import { API_BASE } from '../config';

// Reduced timeouts for emergency fix - UI should not hang
const DEFAULT_TIMEOUT = 30000; // 30 seconds
const DISCOVERY_TIMEOUT = 30000; // 30 seconds for discovery calls

function getFullUrl(url: string): string {
  if (url.startsWith('http')) return url;
  return `${API_BASE}${url.startsWith('/') ? '' : '/'}${url}`;
}

function getTimeoutForUrl(url: string): number {
  if (url.includes('/discovery/')) {
    return DISCOVERY_TIMEOUT;
  }
  return DEFAULT_TIMEOUT;
}

async function fetchWithTimeout(url: string, options: RequestInit): Promise<Response> {
  const timeout = getTimeoutForUrl(url);
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error(`Request timeout after ${timeout}ms for ${url}`);
    }
    throw error;
  }
}

export async function getJSON<T>(url: string): Promise<T> {
  const fullUrl = getFullUrl(url);
  const r = await fetchWithTimeout(fullUrl, {
    method: "GET",
    cache: "no-cache",
    headers: {
      "Cache-Control": "no-cache, no-store, must-revalidate",
      "Pragma": "no-cache",
      "Expires": "0"
    }
  });
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    throw new Error(`GET ${fullUrl} ${r.status}: ${text}`);
  }
  return r.json() as Promise<T>;
}

export async function postJSON<T>(url: string, body: any): Promise<T> {
  const fullUrl = getFullUrl(url);
  const r = await fetchWithTimeout(fullUrl, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await r.text().catch(() => "");
  if (!r.ok) throw new Error(`POST ${fullUrl} ${r.status}: ${text}`);
  try { return JSON.parse(text) as T; } catch { return text as any; }
}

// Position-specific trade functions
export async function executePositionTrade(symbol: string, action: string, percentage?: number, notional?: number): Promise<any> {
  return postJSON("/trades/position", {
    symbol,
    action,
    mode: "live",
    percentage,
    notional_usd: notional
  });
}

export async function previewPositionTrade(symbol: string): Promise<any> {
  return getJSON(`/trades/position/${symbol}/preview`);
}