import { API_BASE } from '../config';

export { API_BASE };

export const API_ENDPOINTS = {
  holdings: `${API_BASE}/portfolio/holdings`,
  recommendations: `${API_BASE}/discovery/contenders`,
} as const;