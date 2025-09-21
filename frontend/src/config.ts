export const API_BASE =
  (import.meta as any)?.env?.VITE_API_BASE ||
  (window as any).__API_BASE__ ||
  (window.location.hostname === 'localhost' ? '/api' : "https://amc-trader.onrender.com");

export const WS_URL = "wss://amc-trader.onrender.com/v1/stream";