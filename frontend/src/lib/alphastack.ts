/**
 * AlphaStack 4.1 API Client
 * Provides direct interface to AlphaStack discovery endpoints
 */

const API = import.meta.env.VITE_API_BASE ?? (window as any).__API_BASE__ ?? "https://amc-trader.onrender.com";
const WS = import.meta.env.VITE_WS_URL ?? (API.replace(/^http/, 'ws') + '/v1/stream');

export { API, WS };

interface AlphaStackResponse<T> {
  items?: T[];
  explosive_top?: T[];
  schema_version?: string;
  system_health?: {
    system_ready: boolean;
  };
  production_health?: {
    stale_data_detected: boolean;
  };
}

/**
 * Fetch wrapper with error handling
 */
async function fetchApi<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API}${endpoint}`, {
    cache: 'no-store',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) {
    throw new Error(`AlphaStack API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get top discovery candidates
 */
export async function getTop(limit: number = 50): Promise<AlphaStackResponse<any>> {
  return fetchApi<AlphaStackResponse<any>>(`/v1/candidates/top?limit=${limit}`);
}

/**
 * Get explosive/urgent candidates
 */
export async function getExplosive(): Promise<AlphaStackResponse<any>> {
  return fetchApi<AlphaStackResponse<any>>('/v1/explosive');
}

/**
 * Get system telemetry and health status
 */
export async function getTelemetry(): Promise<AlphaStackResponse<any>> {
  return fetchApi<AlphaStackResponse<any>>('/v1/telemetry');
}

/**
 * Place order with AlphaStack
 */
export async function placeOrder(orderData: {
  symbol: string;
  action: 'buy' | 'sell';
  quantity?: number;
  notional?: number;
  accountMode?: string;
  clientId?: string;
}): Promise<any> {
  const payload = {
    accountMode: 'paper',
    clientId: crypto.randomUUID(),
    ...orderData
  };

  const response = await fetch(`${API}/v1/orders`, {
    method: 'POST',
    cache: 'no-store',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`Order placement failed: ${response.status} ${response.statusText}`);
  }

  return response.json();
}