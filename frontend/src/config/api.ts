const getApiBase = (): string => {
  // Runtime override from window
  if (typeof window !== 'undefined' && (window as any).API_BASE) {
    return (window as any).API_BASE;
  }
  
  // Build-time environment variable
  return import.meta.env.VITE_API_BASE || 'http://localhost:8000';
};

export const API_BASE = getApiBase();

export const API_ENDPOINTS = {
  holdings: `${API_BASE}/holdings`,
  recommendations: `${API_BASE}/recommendations`,
} as const;