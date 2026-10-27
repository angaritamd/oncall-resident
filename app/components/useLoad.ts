"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/api";

export function useLoad<T>(fn: () => Promise<T>, onBusy: (b: boolean) => void) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  // time of the last successful fetch; kept on failure so stale data can be labelled as such
  const [loadedAt, setLoadedAt] = useState<Date | null>(null);
  // set when a fetch fails, cleared only by a later success (a retry in flight does not clear it)
  const [stale, setStale] = useState(false);
  const seq = useRef(0);
  const load = useCallback(async () => {
    // only the latest call may write state; an older response arriving late is dropped
    const id = ++seq.current;
    setError(null);
    onBusy(true);
    try {
      const result = await fn();
      if (id !== seq.current) return;
      setData(result);
      setLoadedAt(new Date());
      setStale(false);
    } catch (e) {
      if (id !== seq.current) return;
      setError(e instanceof ApiError ? e : new ApiError("x", "other"));
      setStale(true);
    } finally {
      onBusy(false);
    }
  }, [fn, onBusy]);
  useEffect(() => {
    // fetch on mount / when inputs change
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);
  return { data, error, load, loadedAt, stale };
}
