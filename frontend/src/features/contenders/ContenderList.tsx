// frontend/src/features/contenders/ContenderList.tsx
import { useEffect, useState } from "react";
import { fetchContenders, type Candidate, ping } from "../../lib/api";

function toAction(score: number) {
  if (score >= 75) return "Trade-ready breakout";
  if (score >= 70) return "Watchlist builder";
  return "Monitoring";
}

export default function ContenderList() {
  const [data, setData] = useState<Candidate[] | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    ping().then(setOnline);
    const ctrl = new AbortController();
    fetchContenders(ctrl.signal)
      .then((d) => setData(d.sort((a, b) => b.score - a.score))) // keep all, sort desc
      .catch(setError)
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <span className={`px-2 py-1 rounded-full text-sm ${online ? "bg-green-100 text-green-700" : online === false ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-600"}`}>
          {online === null ? "Checking…" : online ? "System Online" : "System Offline"}
        </span>
      </div>

      {loading && <div className="text-gray-600">Loading contenders…</div>}
      {error && <div className="text-red-600">Failed to load: {error.message}</div>}
      {!loading && !error && (!data || data.length === 0) && (
        <div className="text-gray-600">No contenders right now. Monitoring market…</div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data?.map((c) => (
          <article key={c.ticker} className="p-4 rounded-2xl shadow-sm border bg-white">
            <header className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">{c.ticker}</h3>
              <span className="text-sm px-2 py-0.5 rounded-full bg-blue-50 text-blue-700">
                {c.score.toFixed(1)}
              </span>
            </header>
            <p className="text-sm text-gray-600">{toAction(c.score)}</p>
            {c.subscores && (
              <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
                {Object.entries(c.subscores).map(([k, v]) => (
                  <div key={k} className="rounded-md bg-gray-50 p-2">
                    <div className="text-gray-500">{k}</div>
                    <div className="font-medium">{typeof v === "number" ? v.toFixed(1) : String(v)}</div>
                  </div>
                ))}
              </div>
            )}
            {c.reasons?.length ? (
              <ul className="mt-2 text-xs text-gray-700 list-disc pl-4">
                {c.reasons.slice(0, 4).map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            ) : null}
          </article>
        ))}
      </div>
    </div>
  );
}