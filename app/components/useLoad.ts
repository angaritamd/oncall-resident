"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api";

export function useLoad<T>(fn: () => Promise<T>, onBusy: (b: boolean) => void) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  // time of the last successful fetch; kept on failure so stale data can be labelled as such
  const [loadedAt, setLoadedAt] = useState<Date | null>(null);
  const load = useCallback(async () => {
    setError(null);
    onBusy(true);
    try {
      setData(await fn());
      setLoadedAt(new Date());
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError("x", "other"));
    } finally {
      onBusy(false);
    }
  }, [fn, onBusy]);
  useEffect(() => {
    // fetch on mount / when inputs change
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);
  return { data, error, load, loadedAt };
}
