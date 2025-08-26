export interface Holding {
  symbol: string;
  qty: number;
  quantity: number;
  market_value: number;
  unrealized_pl: number;
  unrealized_plpc: number;
  unrealized_pl_pct: number;
  current_price: number;
  last_price: number;
  avg_entry_price: number;
  avg_price: number;
  suggestion?: string;
  thesis?: string;
  confidence?: number;
  score?: number;
  target_price?: number;
  stop_price?: number;
}

export interface Recommendation {
  symbol: string;
  action?: 'BUY_MORE' | 'HOLD' | 'SELL';
  confidence?: number;
  score?: number;
  vigl_score?: number;
  thesis?: string;
  price_target?: number;
  price?: number;
  last_price?: number;
  target_price?: number;
  stop_price?: number;
  take_profit_price?: number;
  risk_level?: 'LOW' | 'MEDIUM' | 'HIGH';
  
  // Sector and momentum fields
  sector?: string;
  sector_etf?: string;
  rs_5d?: number;
  rs_20d?: number;
  
  // Volume and technical fields
  rel_vol_30m?: number;
  relative_volume?: number;
  atr_pct?: number;
  atr_abs?: number;
  dollar_vol?: number;
}

export interface AuditData {
  volume?: {
    score: number;
    rel_vol_30m: number;
    float: number;
  };
  short?: {
    score: number;
    si: number;
  };
  catalyst?: {
    score: number;
  };
  sentiment?: {
    score: number;
  };
  options?: {
    score: number;
    pcr: number;
    iv_pctl: number;
  };
  technicals?: {
    score: number;
    ema_cross: boolean;
    rsi: number;
    above_vwap: boolean;
    atr_pct: number;
  };
  sector?: {
    score: number;
    rs_20d: number;
    rs_5d: number;
    ema_20: number;
    ema_50: number;
    sector_etf: string;
  };
}

export interface ApiError {
  message: string;
  timestamp: number;
}