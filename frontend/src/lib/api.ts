// frontend/src/lib/api.ts
export const API_BASE =
  (import.meta.env.VITE_API_BASE as string) ??
  (window.location.hostname === 'localhost' ? '/api' : "https://amc-trader.onrender.com");

const api = (p: string) => {
  // Handle relative URLs for proxy correctly
  if (API_BASE.startsWith('/')) {
    return `${API_BASE}${p}`;
  }
  return new URL(p, API_BASE).toString();
};

/** ---- Generic helpers kept for legacy components ---- */
export async function getJSON<T = unknown>(path: string, signal?: AbortSignal): Promise<T> {
  const url = api(path);
  const r = await fetch(url, { signal });
  if (!r.ok) throw new Error(`HTTP ${r.status} for ${url}`);
  return r.json() as Promise<T>;
}

export async function postJSON<T = unknown, B = unknown>(
  path: string,
  body: B,
  signal?: AbortSignal
): Promise<T> {
  const url = api(path);
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!r.ok) throw new Error(`HTTP ${r.status} for ${url}`);
  return r.json() as Promise<T>;
}

/** ---- Domain types & specific endpoints ---- */
export type Subscores = {
  volume: number; squeeze: number; catalyst: number;
  options: number; technical: number; sentiment: number;
};

export type Candidate = {
  ticker: string;
  score: number;
  status?: string;
  updated_at?: string;
  reasons?: string[];
  tags?: string[];
  subscores?: Subscores;
};

export async function fetchContenders(signal?: AbortSignal): Promise<Candidate[]> {
  return getJSON<Candidate[]>("/discovery/contenders-v2", signal);
}

export async function ping(): Promise<boolean> {
  try {
    const r = await fetch(api("/health"));
    return r.ok;
  } catch {
    return false;
  }
}

/** Execute a position trade */
export async function executePositionTrade(symbol: string, action: string) {
  try {
    const response = await fetch(api(`/trades/position/${symbol}/preview`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });

    const data = await response.json();

    if (!response.ok) {
      return {
        success: false,
        error: { message: data.detail || `HTTP ${response.status}` }
      };
    }

    return {
      success: true,
      message: data.message || `${action} executed for ${symbol}`,
      ...data
    };
  } catch (error: any) {
    return {
      success: false,
      error: { message: error.message || 'Network error' }
    };
  }
}