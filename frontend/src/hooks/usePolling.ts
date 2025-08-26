import { useState, useEffect, useRef } from 'react';
import type { ApiError } from '../types/api';

interface UsePollingResult<T> {
  data: T | null;
  error: ApiError | null;
  isLoading: boolean;
  refresh: () => void;
}

export function usePolling<T>(
  url: string,
  interval: number = 15000
): UsePollingResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const intervalRef = useRef<number | null>(null);

  const fetchData = async () => {
    try {
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      const apiError: ApiError = {
        message: err instanceof Error ? err.message : 'Unknown error',
        timestamp: Date.now()
      };
      setError(apiError);
      setData(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Initial fetch
    fetchData();

    // Set up polling
    intervalRef.current = setInterval(fetchData, interval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [url, interval]);

  return { data, error, isLoading, refresh: fetchData };
}