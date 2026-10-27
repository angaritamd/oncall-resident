"use client";

import { useCallback, useMemo, useState } from "react";
import { api, type Activity, type Item, type Lang } from "@/lib/api";
import type { Dict } from "@/lib/i18n";
import { NextStudyCard, PriorityGrid, StudyRowButton } from "./cards";
import { Btn, ErrorNote, SectionLabel, Skeleton, SoonPill, StudyId } from "./ui";
import { useLoad } from "./useLoad";

type Busy = (b: boolean) => void;

function greeting(t: Dict) {
  const h = new Date().getHours();
  return h >= 5 && h < 12 ? t["greet.morning"] : h >= 12 && h < 19 ? t["greet.afternoon"] : t["greet.night"];
}

/** 01 · Inicio de turno. Every number comes from the live worklist. */
export function ShiftStart({ lang, t, onOpen, onAsk, onBusy }: { lang: Lang; t: Dict; onOpen: (id: string) => void; onAsk: (s: string) => void; onBusy: Busy }) {
  const fetcher = useCallback(() => api.worklist(lang), [lang]);
  const { data, error, load } = useLoad<{ items: Item[] }>(fetcher, onBusy);
  const items = data?.items ?? [];
  const q = t.queue(items.length);
  return (
    <section aria-labelledby="greeting" className="flex flex-col gap-3">
      <h2 id="greeting" className="pt-2 text-[38px] font-light leading-[1.05] tracking-[-0.03em] text-ink">
        {/* greeting uses the device clock, so it renders only client-side once data has arrived */}
        {data ? (
          <>
            {greeting(t)}{" "}
            {items.length ? (
              <>
                {q.pre}
                <span className="font-semibold text-blue">{q.num}</span>
                {q.post}
              </>
            ) : (
              t.queueEmpty
            )}
          </>
        ) : (
          <span aria-hidden className="inline-block h-[0.9em] w-3/4 animate-pulse rounded-btn bg-line-2 align-middle" />
        )}
      </h2>
      <p className="text-[14px] text-muted">{t.noAi}</p>

      {error && <ErrorNote text={t[`err.${error.kind}`]} retryLabel={t.retry} onRetry={load} />}
      {!data && !error && (
        <div role="status" aria-label={t.loading} className="flex flex-col gap-2.5">
          <Skeleton className="h-56" />
          <Skeleton className="h-28" />
        </div>
      )}
      {data && items.length > 0 && (
        <>
          <NextStudyCard item={items[0]} total={items.length} t={t} onOpen={onOpen} onAsk={onAsk} />
          <PriorityGrid critical={items.filter((i) => i.critical).length} urgent={items.filter((i) => !i.critical && i.priority === "urgent").length} t={t} />
        </>
      )}
      <div className="flex flex-wrap gap-2 pt-1">
        <Btn variant="pill" onClick={() => onAsk(t["prompt.pendingText"])}>
          {t["prompt.pending"]}
        </Btn>
        <SoonPill label={t["prompt.tomorrow"]} soon={t.soon} />
        <SoonPill label={t["prompt.summary"]} soon={t.soon} />
      </div>
    </section>
  );
}

type Filter = "all" | "critical" | "urgent" | "priority" | "routine";

/** 02 · Pendientes */
export function PendingView({ lang, t, onOpen, onBusy }: { lang: Lang; t: Dict; onOpen: (id: string) => void; onBusy: Busy }) {
  const fetcher = useCallback(() => api.worklist(lang), [lang]);
  const { data, error, load } = useLoad<{ items: Item[] }>(fetcher, onBusy);
  const [filter, setFilter] = useState<Filter>("all");

  const match = useCallback(
    (i: Item, f: Filter) => (f === "all" ? true : f === "critical" ? i.critical : !i.critical && i.priority === f),
    [],
  );
  const { critical, byArrival } = useMemo(() => {
    const rows = (data?.items ?? []).filter((i) => match(i, filter));
    return {
      critical: rows.filter((i) => i.critical),
      byArrival: rows
        .filter((i) => !i.critical)
        .sort((a, b) => (a.arrived_at && b.arrived_at ? a.arrived_at.localeCompare(b.arrived_at) : a.arrived_at ? -1 : 1)),
    };
  }, [data, filter, match]);

  const filters: Filter[] = ["all", "critical", "urgent", "priority", "routine"];
  return (
    <div className="flex flex-col gap-4">
      <h2 className="pt-2 text-[38px] font-light leading-[1.05] tracking-[-0.03em]">{t["pending.title"]}</h2>
      <div role="group" aria-label={t.filters} className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
        {filters.map((f) => {
          const n = (data?.items ?? []).filter((i) => match(i, f)).length;
          const on = filter === f;
          return (
            <button
              key={f}
              type="button"
              aria-pressed={on}
              onClick={() => setFilter(f)}
              className={`inline-flex min-h-11 shrink-0 items-center gap-1.5 rounded-pill px-4 text-[13px] font-medium ${on ? "bg-ink text-ink-text" : "border border-line bg-surface text-ink"}`}
            >
              {t[`filter.${f}`]}
              {data && <span className={on ? "text-muted-d" : "text-muted"}>{n}</span>}
            </button>
          );
        })}
      </div>

      {error && <ErrorNote text={t[`err.${error.kind}`]} retryLabel={t.retry} onRetry={load} />}
      {!data && !error && (
        <div role="status" aria-label={t.loading} className="flex flex-col gap-2.5">
          <Skeleton className="h-20" />
          <Skeleton className="h-64" />
        </div>
      )}
      {data && data.items.length === 0 && <p className="rounded-card bg-surface p-5 text-muted">{t["pending.empty"]}</p>}
      {data && data.items.length > 0 && critical.length + byArrival.length === 0 && <p className="rounded-card bg-surface p-5 text-muted">{t["pending.none"]}</p>}

      {critical.length > 0 && (
        <section aria-labelledby="sec-crit" className="flex flex-col gap-2">
          <h3 id="sec-crit" className="label flex items-center gap-1.5 text-crit-text">
            <span aria-hidden className="size-1.5 rounded-full bg-crit" />
            {t["pending.critical"]}
          </h3>
          <ol className="flex flex-col gap-2">
            {critical.map((i) => (
              <li key={i.study_uid} className="rounded-card-sm bg-ink px-4">
                <StudyRowButton item={i} t={t} onOpen={onOpen} tone="dark" />
              </li>
            ))}
          </ol>
        </section>
      )}
      {byArrival.length > 0 && (
        <section aria-labelledby="sec-arrival" className="flex flex-col gap-2">
          <SectionLabel as="h3">
            <span id="sec-arrival">{t["pending.arrival"]}</span>
          </SectionLabel>
          <ol className="rounded-card bg-surface px-4">
            {byArrival.map((i) => (
              <li key={i.study_uid} className="border-t border-line-2 first:border-t-0">
                <StudyRowButton item={i} t={t} onOpen={onOpen} />
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}

export function ActivityView({ lang, t, onBusy }: { lang: Lang; t: Dict; onBusy: Busy }) {
  const { data, error, load } = useLoad<{ items: Activity[] }>(api.activity, onBusy);
  const fmt = new Intl.DateTimeFormat(lang, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const label = (k: string) => (k === "worklist" ? t["activity.worklist"] : k === "open" ? t["activity.open"] : k === "why" ? t["activity.why"] : k);
  return (
    <div className="flex flex-col gap-4">
      <h2 className="pt-2 text-[38px] font-light leading-[1.05] tracking-[-0.03em]">{t["activity.title"]}</h2>
      {error && <ErrorNote text={t[`err.${error.kind}`]} retryLabel={t.retry} onRetry={load} />}
      {!data && !error && <Skeleton className="h-40" />}
      {data && data.items.length === 0 && <p className="rounded-card bg-surface p-5 text-muted">{t["activity.empty"]}</p>}
      {data && data.items.length > 0 && (
        <ul className="rounded-card bg-surface px-4">
          {data.items.map((a, i) => (
            <li key={i} className="flex min-h-12 flex-wrap items-center gap-x-3 border-t border-line-2 py-2.5 first:border-t-0">
              <time className="font-mono text-[12.5px] font-medium text-muted" dateTime={a.at}>
                {fmt.format(new Date(a.at))}
              </time>
              <span className="text-[15px]">
                {label(a.kind)}
                {!a.ok && <span className="text-muted"> · {t["activity.failed"]}</span>}
              </span>
              {a.case_id && <StudyId id={a.case_id} />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
