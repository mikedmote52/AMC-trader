/**
 * AlphaStack 4.1 Data Adapter
 * Normalizes AlphaStack API responses to UI-expected format
 */

export interface SqueezeOpportunity {
  symbol: string;
  squeeze_score: number;     // 0–1 normalized
  action?: string;
  pattern_type?: string;
  price?: number | null;
  entry?: number | null;
  stop?: number | null;
  tp1?: number | null;
  tp2?: number | null;
  volume_spike?: number | null;
  confidence?: number | null;  // 0–1
  detected_at: string;
}

/**
 * Robustly normalize a single AlphaStack 4.1 candidate to UI format
 */
export function toUiCandidate(c4: any): SqueezeOpportunity {
  // Handle both symbol/ticker variations
  const symbol = c4.symbol ?? c4.ticker ?? 'UNKNOWN';

  // Handle various score field names and normalize to 0-1 range
  const rawScore = c4.total_score ?? c4.score ?? 0;
  const score = typeof rawScore === 'number' ? rawScore : 0;
  const squeeze_score = score >= 1 ? score / 100 : score; // Normalize 0-100 to 0-1

  // Action and pattern mapping
  const action = c4.action_tag ?? c4.action ?? undefined;
  const pattern_type = action;

  // Price from various possible locations
  const price = c4.price ?? c4.snapshot?.price ?? null;

  // Entry/exit levels
  const entry = c4.entry ?? c4.entry_price ?? null;
  const stop = c4.stop ?? c4.stop_loss ?? null;
  const tp1 = c4.tp1 ?? c4.target_1 ?? c4.take_profit_1 ?? null;
  const tp2 = c4.tp2 ?? c4.target_2 ?? c4.take_profit_2 ?? null;

  // Volume metrics
  const volume_spike = c4.snapshot?.intraday_relvol ?? c4.intradayRelVol ?? c4.volume_spike ?? null;

  // Confidence score (0-1 range)
  const rawConfidence = c4.confidence ?? score;
  const confidence = rawConfidence ? Math.min(1, Math.max(0, rawConfidence >= 1 ? rawConfidence / 100 : rawConfidence)) : null;

  return {
    symbol,
    squeeze_score,
    action,
    pattern_type,
    price,
    entry,
    stop,
    tp1,
    tp2,
    volume_spike,
    confidence,
    detected_at: new Date().toISOString()
  };
}

/**
 * Map an array of AlphaStack candidates to UI format
 */
export function mapList(arr: any[]): SqueezeOpportunity[] {
  if (!Array.isArray(arr)) {
    console.warn('mapList received non-array:', typeof arr);
    return [];
  }

  return arr.map(toUiCandidate).filter(item => item.symbol !== 'UNKNOWN');
}

/**
 * Filter candidates by action tag for different UI sections
 */
export function filterByAction(candidates: SqueezeOpportunity[], action: string): SqueezeOpportunity[] {
  return candidates.filter(c => c.action === action);
}

/**
 * Sort candidates by score (highest first)
 */
export function sortByScore(candidates: SqueezeOpportunity[]): SqueezeOpportunity[] {
  return [...candidates].sort((a, b) => (b.squeeze_score || 0) - (a.squeeze_score || 0));
}