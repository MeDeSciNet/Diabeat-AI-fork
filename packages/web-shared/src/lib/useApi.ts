import { useCallback, useEffect, useRef, useState } from 'react';

/** Minimal data-fetching hook: enough for a prototype, no query library. */
export function useApi<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const alive = useRef(true);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  const reload = useCallback(() => {
    setLoading(true);
    setError(null);
    fnRef
      .current()
      .then((value: T) => {
        if (alive.current) setData(value);
      })
      .catch((err: unknown) => {
        if (alive.current) setError(err instanceof Error ? err : new Error(String(err)));
      })
      .finally(() => {
        if (alive.current) setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    alive.current = true;
    reload();
    return () => {
      alive.current = false;
    };
  }, [reload]);

  return { data, error, loading, reload };
}

/** Polls while the tab is visible. Used by the station wall display. */
export function usePolling(fn: () => void, intervalMs: number) {
  useEffect(() => {
    const id = setInterval(() => {
      if (document.visibilityState === 'visible') fn();
    }, intervalMs);
    return () => clearInterval(id);
  }, [fn, intervalMs]);
}
