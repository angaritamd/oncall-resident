"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, api, type Activity, type Item, type Lang } from "@/lib/api";
import type { Dict } from "@/lib/i18n";
import { StudyRow } from "./blocks";
import { CaseId, ErrorNote } from "./ui";

function useLoad<T>(fn: () => Promise<T>, onBusy: (b: boolean) => void) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const load = useCallback(async () => {
    setError(null);
    onBusy(true);
    try {
      setData(await fn());
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
  return { data, error, load };
}

export function PendingView({ lang, t, onOpen, onBusy }: { lang: Lang; t: Dict; onOpen: (id: string) => void; onBusy: (b: boolean) => void }) {
  const fetcher = useCallback(() => api.worklist(lang), [lang]);
  const { data, error, load } = useLoad<{ items: Item[] }>(fetcher, onBusy);
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-4">
      <h2 className="text-[20px] font-semibold">{t["pending.title"]}</h2>
      <p className="mt-1 text-[14px] text-muted">{t.rule}</p>
      <div className="mt-3">
        {error && <ErrorNote text={t[`err.${error.kind}`]} retryLabel={t.retry} onRetry={load} />}
        {!data && !error && <p role="status" className="text-muted">{t.loading}</p>}
        {data && data.items.length === 0 && <p className="text-muted">{t["pending.empty"]}</p>}
        {data && data.items.length > 0 && (
          <ol className="rounded-xl border border-line bg-surface px-3">
            {data.items.map((i) => (
              <StudyRow key={i.study_uid} item={i} t={t} onOpen={onOpen} />
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}

export function ActivityView({ lang, t, onBusy }: { lang: Lang; t: Dict; onBusy: (b: boolean) => void }) {
  const { data, error, load } = useLoad<{ items: Activity[] }>(api.activity, onBusy);
  const fmt = new Intl.DateTimeFormat(lang, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const label = (k: string) => (k === "worklist" ? t["activity.worklist"] : k === "open" ? t["activity.open"] : k === "why" ? t["activity.why"] : k);
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-4">
      <h2 className="text-[20px] font-semibold">{t["activity.title"]}</h2>
      <div className="mt-3">
        {error && <ErrorNote text={t[`err.${error.kind}`]} retryLabel={t.retry} onRetry={load} />}
        {!data && !error && <p role="status" className="text-muted">{t.loading}</p>}
        {data && data.items.length === 0 && <p className="text-muted">{t["activity.empty"]}</p>}
        {data && data.items.length > 0 && (
          <ul className="rounded-xl border border-line bg-surface px-3.5">
            {data.items.map((a, i) => (
              <li key={i} className="flex flex-wrap items-baseline gap-x-3 border-t border-line py-2.5 first:border-t-0">
                <time className="font-mono text-[13px] text-muted" dateTime={a.at}>
                  {fmt.format(new Date(a.at))}
                </time>
                <span>
                  {label(a.kind)}
                  {!a.ok && <span className="text-review"> · {t["activity.failed"]}</span>}
                </span>
                {a.case_id && <CaseId id={a.case_id} />}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
