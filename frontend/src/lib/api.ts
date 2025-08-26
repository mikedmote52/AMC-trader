export async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url);
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