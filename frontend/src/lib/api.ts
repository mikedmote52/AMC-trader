// frontend/src/lib/api.ts
export const API_BASE =
  (import.meta.env.VITE_API_BASE as string) ?? "https://amc-trader.onrender.com";

const api = (p: string) => new URL(p, API_BASE).toString();

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
  const r = await fetch(api("/discovery/contenders"), { signal });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function ping(): Promise<boolean> {
  try {
    const r = await fetch(api("/health"));
    return r.ok;
  } catch {
    return false;
  }
}