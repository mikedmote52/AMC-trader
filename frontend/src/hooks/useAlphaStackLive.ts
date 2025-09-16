/**
 * AlphaStack Live Data Hook
 * Manages real-time WebSocket connection and data fetching
 */

import { useState, useEffect, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { getTop, getExplosive, getTelemetry, WS } from '../lib/alphastack';

interface AlphaStackData {
  top: any | null;
  explosive: any | null;
  telemetry: any | null;
  loading: boolean;
  safeToTrade: boolean;
  error: string | null;
}

interface TelemetryData {
  schema_version?: string;
  system_health?: {
    system_ready: boolean;
  };
  production_health?: {
    stale_data_detected: boolean;
  };
}

export function useAlphaStackLive(): AlphaStackData {
  const [top, setTop] = useState<any>(null);
  const [explosive, setExplosive] = useState<any>(null);
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<Socket | null>(null);
  const mountedRef = useRef(true);

  // Compute safeToTrade from telemetry
  const safeToTrade = Boolean(
    telemetry?.system_health?.system_ready === true &&
    telemetry?.production_health?.stale_data_detected !== true
  );

  // Refresh all data
  const refresh = async () => {
    if (!mountedRef.current) return;

    try {
      setLoading(true);
      setError(null);

      const [topData, explosiveData, telemetryData] = await Promise.all([
        getTop(50).catch(err => {
          console.warn('Failed to fetch top candidates:', err);
          return null;
        }),
        getExplosive().catch(err => {
          console.warn('Failed to fetch explosive candidates:', err);
          return null;
        }),
        getTelemetry().catch(err => {
          console.warn('Failed to fetch telemetry:', err);
          return null;
        })
      ]);

      if (mountedRef.current) {
        setTop(topData);
        setExplosive(explosiveData);
        setTelemetry(telemetryData);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : 'Unknown error occurred');
        console.error('AlphaStack refresh error:', err);
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  };

  // Refresh telemetry only
  const refreshTelemetry = async () => {
    if (!mountedRef.current) return;

    try {
      const telemetryData = await getTelemetry();
      if (mountedRef.current) {
        setTelemetry(telemetryData);
      }
    } catch (err) {
      console.warn('Failed to refresh telemetry:', err);
    }
  };

  // WebSocket connection setup
  useEffect(() => {
    mountedRef.current = true;

    // Initial data fetch
    refresh();

    // Set up WebSocket connection
    const connectWebSocket = () => {
      try {
        const socket = io(WS, {
          transports: ['websocket', 'polling'],
          timeout: 10000,
          reconnection: true,
          reconnectionAttempts: 5,
          reconnectionDelay: 2000,
        });

        socket.on('connect', () => {
          console.log('AlphaStack WebSocket connected');
        });

        socket.on('disconnect', (reason) => {
          console.log('AlphaStack WebSocket disconnected:', reason);
        });

        socket.on('connect_error', (error) => {
          console.warn('AlphaStack WebSocket connection error:', error);
        });

        // Listen for real-time events
        socket.on('candidate', () => {
          console.log('New candidate received, refreshing data...');
          refresh();
        });

        socket.on('explosive', () => {
          console.log('New explosive candidate received, refreshing data...');
          refresh();
        });

        socket.on('telemetry', () => {
          console.log('Telemetry update received, refreshing...');
          refreshTelemetry();
        });

        // Catch-all for any other events
        socket.onAny((eventName, data) => {
          console.log(`AlphaStack WebSocket event: ${eventName}`, data);
        });

        socketRef.current = socket;
      } catch (err) {
        console.error('Failed to initialize WebSocket:', err);
      }
    };

    // Connect with a small delay to let initial fetch complete
    const wsTimeout = setTimeout(connectWebSocket, 1000);

    // Cleanup
    return () => {
      mountedRef.current = false;
      clearTimeout(wsTimeout);

      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
      }
    };
  }, []);

  return {
    top,
    explosive,
    telemetry,
    loading,
    safeToTrade,
    error
  };
}