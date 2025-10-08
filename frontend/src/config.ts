// Determine API base URL based on environment
const getApiBase = () => {
  const viteEnv = (import.meta as any)?.env?.VITE_API_BASE;
  const windowBase = (window as any).__API_BASE__;
  const isLocalhost = window.location.hostname === 'localhost';

  // Priority: VITE_API_BASE > window.__API_BASE__ > auto-detect
  if (viteEnv && viteEnv.trim()) {
    console.log('[CONFIG] Using VITE_API_BASE:', viteEnv);
    return viteEnv;
  }

  if (windowBase && windowBase.trim()) {
    console.log('[CONFIG] Using window.__API_BASE__:', windowBase);
    return windowBase;
  }

  // Auto-detect based on hostname
  const autoDetected = isLocalhost ? '/api' : 'https://amc-trader.onrender.com';
  console.log('[CONFIG] Auto-detected API_BASE:', autoDetected, '(hostname:', window.location.hostname, ')');
  return autoDetected;
};

export const API_BASE = getApiBase();
export const WS_URL = "wss://amc-trader.onrender.com/v1/stream";

// Force redeploy - Oct 8, 2025