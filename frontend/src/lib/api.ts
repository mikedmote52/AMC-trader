export async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url, {
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
    throw new Error(`GET ${url} ${r.status}: ${text}`);
  }
  return r.json() as Promise<T>;
}

export async function postJSON<T>(url: string, body: any): Promise<T> {
  const r = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await r.text().catch(() => "");
  if (!r.ok) throw new Error(`POST ${url} ${r.status}: ${text}`);
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