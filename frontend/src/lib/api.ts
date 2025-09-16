// frontend/src/lib/api.ts
export const API_BASE =
  (import.meta.env.VITE_API_BASE as string) ?? "https://amc-trader.onrender.com";

function api(path: string) {
  // Always build absolute URL, regardless of current route (e.g. /squeeze)
  return new URL(path, API_BASE).toString();
}

export type Subscores = {
  volume: number; squeeze: number; catalyst: number;
  options: number; technical: number; sentiment: number;
};

export type Candidate = {
  ticker: string;
  score: number;
  status?: string;
  subscores?: Subscores;
  updated_at?: string;
  reasons?: string[];
  tags?: string[];
};

export async function fetchContenders(signal?: AbortSignal): Promise<Candidate[]> {
  const res = await fetch(api("/discovery/contenders"), { signal });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function ping(): Promise<boolean> {
  try {
    const r = await fetch(api("/health"));
    return r.ok;
  } catch {
    return false;
  }
}