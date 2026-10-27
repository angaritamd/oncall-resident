"use client";

import { useCallback, useMemo, useState } from "react";
import { api, type Activity, type Item, type Lang } from "@/lib/api";
import type { Dict } from "@/lib/i18n";
import { ArrivalRow, CriticalRow, NextStudyCard, PriorityGrid, QuickPrompts } from "./cards";
import { ErrorNote, SectionLabel, Skeleton, StudyId } from "./ui";
import { useLoad } from "./useLoad";

type Busy = (b: boolean) => void;

function greeting(t: Dict) {
  const h = new Date().getHours();
  return h >= 5 && h < 12 ? t["greet.morning"] : h >= 12 && h < 19 ? t["greet.afternoon"] : t["greet.night"];
}

const HEADLINE = "text-[40px] font-light leading-[1.05] tracking-[-0.03em] text-ink";

/** 01 · Inicio de turno. Every number comes from the live worklist. */
export function ShiftStart({ lang, t, onOpen, onPending, onBusy }: { lang: Lang; t: Dict; onOpen: (id: string) => void; onPending: () => void; onBusy: Busy }) {
  const fetcher = useCallback(() => api.worklist(lang), [lang]);
  const { data, error, load } = useLoad<{ items: Item[] }>(fetcher, onBusy);
  const items = data?.items ?? [];
  const crit = items.filter((i) => i.critical).length;
  const q = t.queue(items.length);
  return (
    <section aria-labelledby="greeting" className="flex flex-col gap-3">
      <h2 id="greeting" className={`pt-3 ${HEADLINE}`}>
        {/* greeting uses the device clock, so it renders only client-side once data has arrived */}
        {data ? (
          <>
            <span className="block">{greeting(t)}</span>
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
      {data && items.length > 0 && <p className="mb-2 text-[17px] leading-snug text-muted">{t.critSummary(crit)}</p>}

      {error && <ErrorNote text={t[`err.${error.kind}`]} retryLabel={t.retry} onRetry={load} />}
      {!data && !error && (
        <div role="status" aria-label={t.loading} className="flex flex-col gap-2.5">
          <Skeleton className="h-56" />
          <Skeleton className="h-28" />
        </div>
      )}
      {data && items.length > 0 && (
        <>
          <NextStudyCard item={items[0]} total={items.length} t={t} onOpen={onOpen} />
          <PriorityGrid critical={crit} urgent={items.filter((i) => !i.critical && i.priority === "urgent").length} t={t} />
        </>
      )}
      <QuickPrompts pending={data ? items.length : null} t={t} onPending={onPending} />
      <p className="px-1 text-[13px] text-muted">{t.noAi}</p>
    </section>
  );
}

type Filter = "all" | "critical" | "urgent";

/** 02 · Pendientes */
export function PendingView({ lang, t, onOpen, onBusy }: { lang: Lang; t: Dict; onOpen: (id: string) => void; onBusy: Busy }) {
  const fetcher = useCallback(() => api.worklist(lang), [lang]);
  const { data, error, load, loadedAt, stale } = useLoad<{ items: Item[] }>(fetcher, onBusy);
  const [filter, setFilter] = useState<Filter>("all");

  const match = useCallback((i: Item, f: Filter) => (f === "all" ? true : f === "critical" ? i.critical : !i.critical && i.priority === "urgent"), []);
  const all = useMemo(() => data?.items ?? [], [data]);
  const { critical, byArrival, noPriority } = useMemo(() => {
    const rows = all.filter((i) => i.has_metadata && match(i, filter));
    return {
      critical: rows.filter((i) => i.critical),
      // oldest arrival first
      byArrival: rows.filter((i) => !i.critical).sort((a, b) => (a.arrived_at ?? "").localeCompare(b.arrived_at ?? "")),
      // studies in the PACS without order metadata are listed too, never hidden
      noPriority: filter === "all" ? all.filter((i) => !i.has_metadata) : [],
    };
  }, [all, filter, match]);

  const filters: { id: Filter; dot?: string }[] = [{ id: "all" }, { id: "critical", dot: "bg-crit" }, { id: "urgent", dot: "bg-urg" }];
  const time = loadedAt ? new Intl.DateTimeFormat(lang, { hour: "2-digit", minute: "2-digit" }).format(loadedAt) : null;
  return (
    <div className="flex flex-col gap-4">
      <div className="pt-3">
        <p className="h-5 text-[14px] text-muted">{time && `${t.updated} · ${time}${stale ? ` · ${t.stale}` : ""}`}</p>
        <h2 className={HEADLINE}>
          {t["pending.title"]} {data && <span className="font-semibold text-blue">{all.length}</span>}
        </h2>
      </div>
      <div role="group" aria-label={t.filters} className="flex flex-wrap gap-1.5">
        {filters.map(({ id, dot }) => {
          const n = all.filter((i) => match(i, id)).length;
          const on = filter === id;
          return (
            <button
              key={id}
              type="button"
              aria-pressed={on}
              onClick={() => setFilter(id)}
              className={`inline-flex min-h-11 items-center gap-1.5 rounded-pill px-3.5 text-[14px] font-medium ${on ? "bg-ink text-ink-text" : "border border-line bg-surface text-ink"}`}
            >
              {dot && <span aria-hidden className={`size-2 rounded-full ${dot}`} />}
              {t[`filter.${id}`]}
              {data && <span className={on ? "text-muted-d" : "text-muted"}>{n}</span>}
            </button>
          );
        })}
      </div>

      {error && <ErrorNote text={t[`err.${error.kind}`]} retryLabel={t.retry} onRetry={load} />}
      {!data && !error && (
        <div role="status" aria-label={t.loading} className="flex flex-col gap-2.5">
          <Skeleton className="h-24" />
          <Skeleton className="h-64" />
        </div>
      )}
      {data && all.length === 0 && <p className="rounded-card bg-surface p-5 text-muted">{t["pending.empty"]}</p>}
      {data && all.length > 0 && critical.length + byArrival.length + noPriority.length === 0 && <p className="rounded-card bg-surface p-5 text-muted">{t["pending.none"]}</p>}

      {critical.length > 0 && (
        <section aria-labelledby="sec-crit" className="flex flex-col gap-2.5">
          <SectionLabel as="h3">
            <span id="sec-crit">{t["pending.critical"]}</span>
          </SectionLabel>
          <ol className="flex flex-col gap-2.5">
            {critical.map((i) => (
              <li key={i.study_uid}>
                <CriticalRow item={i} t={t} onOpen={onOpen} />
              </li>
            ))}
          </ol>
        </section>
      )}
      {byArrival.length > 0 && (
        <section aria-labelledby="sec-arrival" className="flex flex-col gap-2.5">
          <SectionLabel as="h3">
            <span id="sec-arrival">{t["pending.arrival"]}</span>
          </SectionLabel>
          <ol className="rounded-card bg-surface px-5">
            {byArrival.map((i) => (
              <li key={i.study_uid} className="border-t border-line-2 first:border-t-0">
                <ArrivalRow item={i} t={t} onOpen={onOpen} />
              </li>
            ))}
          </ol>
        </section>
      )}
      {noPriority.length > 0 && (
        <section aria-labelledby="sec-nometa" className="flex flex-col gap-2.5">
          <SectionLabel as="h3">
            <span id="sec-nometa">
              {t["pending.noPriority"]} · {noPriority.length}
            </span>
          </SectionLabel>
          <ol className="rounded-card bg-surface px-5">
            {noPriority.map((i) => (
              <li key={i.study_uid} className="border-t border-line-2 first:border-t-0">
                <ArrivalRow item={i} t={t} onOpen={onOpen} />
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
  const kindLabel = { tool: t["activity.tool"], view: t["activity.view"], chat: t["activity.chat"] } as const;
  return (
    <div className="flex flex-col gap-4">
      <h2 className={`pt-3 ${HEADLINE}`}>{t["activity.title"]}</h2>
      {error && <ErrorNote text={t[`err.${error.kind}`]} retryLabel={t.retry} onRetry={load} />}
      {!data && !error && <Skeleton className="h-40" />}
      {data && data.items.length === 0 && <p className="rounded-card bg-surface p-5 text-muted">{t["activity.empty"]}</p>}
      {data && data.items.length > 0 && (
        <ul className="rounded-card bg-surface px-5">
          {data.items.map((a, i) => (
            <li key={i} className="border-t border-line-2 py-3 first:border-t-0">
              <div className="flex flex-wrap items-baseline gap-x-2.5">
                <time className="font-mono text-[12.5px] font-medium text-muted" dateTime={a.at}>
                  {fmt.format(new Date(a.at))}
                </time>
                <span className="text-[12px] font-medium uppercase tracking-[0.08em] text-muted">{kindLabel[a.kind] ?? a.kind}</span>
                <span className={`font-mono text-[14px] font-medium ${a.kind === "tool" ? "text-ink" : "text-muted"}`}>{a.name}</span>
                {a.case_id && <StudyId id={a.case_id} />}
                {!a.ok && <span className="text-[13px] text-muted">· {t["activity.failed"]}</span>}
                {a.mode === "fallback" && <span className="text-[12px] text-muted">· {t.modeFallback}</span>}
                {a.mode === "basic" && <span className="text-[12px] text-muted">· {t.modeBasic}</span>}
              </div>
              {a.kind === "tool" && (
                <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[13px]">
                  <dt className="text-muted">{t["activity.input"]}</dt>
                  <dd className="min-w-0 break-all font-mono text-[12px]">{JSON.stringify(a.input ?? {})}</dd>
                  <dt className="text-muted">{t["activity.output"]}</dt>
                  <dd className="min-w-0">{a.output ?? "—"}</dd>
                  {a.model && (
                    <>
                      <dt className="text-muted">{t["activity.model"]}</dt>
                      <dd className="min-w-0 break-all font-mono text-[12px]">{a.model}</dd>
                    </>
                  )}
                </dl>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
