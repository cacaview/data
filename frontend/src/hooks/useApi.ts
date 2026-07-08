// Generic data-fetching hook with loading/error state.
// Eliminates the "useState<any>(null)" + manual loading flag pattern.

import { useEffect, useState, useCallback } from 'react';
import { formatApiError } from '../utils/api';

export interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useApi<T>(fetcher: () => Promise<T>, deps: ReadonlyArray<unknown> = []): UseApiResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetcher()
      .then(d => { if (!cancelled) setData(d); })
      .catch(e => { if (!cancelled) setError(formatApiError(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const refetch = useCallback(() => setTick(t => t + 1), []);
  return { data, loading, error, refetch };
}
