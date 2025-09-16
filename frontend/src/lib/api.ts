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
  // Try new endpoint first, fallback to emergency populate if not available
  try {
    const res = await fetch(api("/discovery/contenders"), { signal });
    if (res.ok) {
      const data = await res.json();
      // Handle both response formats
      if (data.success && Array.isArray(data.data)) {
        return data.data;
      }
      return Array.isArray(data) ? data : [];
    }
  } catch (e) {
    console.warn("Primary endpoint failed, trying emergency populate:", e);
  }

  // Fallback: try to populate cache and get results
  try {
    await fetch(api("/discovery/emergency/populate-cache"), {
      method: "POST",
      signal
    });

    // Wait a moment for cache to populate
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Try emergency enhanced discovery
    const res = await fetch(api("/discovery/emergency/enhanced-discovery"), {
      method: "POST",
      signal
    });

    if (res.ok) {
      const data = await res.json();
      if (data.candidates && Array.isArray(data.candidates)) {
        return data.candidates;
      }
    }
  } catch (e) {
    console.warn("Emergency endpoints failed:", e);
  }

  // Last resort: return empty array to prevent UI crash
  return [];
}

export async function ping(): Promise<boolean> {
  try {
    const r = await fetch(api("/health"));
    return r.ok;
  } catch {
    return false;
  }
}