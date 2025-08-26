export const API_BASE =
  (import.meta as any)?.env?.VITE_API_BASE ||
  (window as any).__API_BASE__ ||
  "https://amc-trader.onrender.com";