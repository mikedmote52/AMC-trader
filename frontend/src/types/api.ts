export interface Holding {
  symbol: string;
  qty: number;
  market_value: number;
  unrealized_pl: number;
  unrealized_plpc: number;
  current_price: number;
  avg_entry_price: number;
}

export interface Recommendation {
  symbol: string;
  action: 'BUY_MORE' | 'HOLD' | 'SELL';
  confidence: number;
  vigl_score?: number;
  thesis: string;
  price_target?: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
}

export interface ApiError {
  message: string;
  timestamp: number;
}