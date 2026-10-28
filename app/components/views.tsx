"use client";

import { ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";
import { api, type Activity, type ApiError, type Item, type Lang, type NextUp, type Worklist } from "@/lib/api";
import type { Dict } from "@/lib/i18n";
import { ArrivalRow, CriticalRow, NextStudyCard, PriorityGrid, QuickPrompts } from "./cards";
import { Btn, ErrorNote, SectionLabel, Skeleton, StudyId } from "./ui";
import { useLoad } from "./useLoad";

type Busy = (b: boolean) => void;

function greeting(t: Dict) {
  const h = new Date().getHours();
  return h >= 5 && h < 12 ? t["greet.morning"] : h >= 12 && h < 19 ? t["greet.afternoon"] : t["greet.night"];
}

const HEADLINE = "text-[40px] font-light leading-[1.05] tracking-[-0.03em] text-ink";

type Load = { data: Worklist | null; error: ApiError | null; load: () => void };

/** 01 · Inicio de turno. Every number comes from the live worklist (shared with the Lista tab). */
export function ShiftStart({ wl, t, onOpen, onPending }: { wl: Load; t: Dict; onOpen: (id: string) => void; onPending: () => void }) {
  const { data, error, load } = wl;
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

      {error && !data && <ErrorNote text={t[`err.${error.kind}`]} retryLabel={t.retry} onRetry={load} />}
      {!data && !error && (
        <div role="status" aria-label={t.loading} className="flex flex-col gap-2.5">
          <Skeleton className="h-56" />
          <Skeleton className="h-28" />
        </div>
      )}
      {data && items.length > 0 && (
        <>
          <NextStudyCard item={items[0]} total={items.length} t={t} onOpen={onOpen} />
          <PriorityGrid critical={crit} urgent={items.filter(isUrgent).length} t={t} />
        </>
      )}
      <QuickPrompts pending={data ? items.length : null} t={t} onPending={onPending} />
      <p className="px-1 text-[13px] text-muted">{t.noAi}</p>
    </section>
  );
}

type Filter = "all" | "critical" | "urgent" | "rx" | "ct" | "signed";

/** STAT and urgente orders without a technologist critical flag. */
const isUrgent = (i: Item) => !i.critical && (i.priority === "stat" || i.priority === "urgent");
const isCt = (i: Item) => i.modalities.includes("CT");
const MATCH: Record<Exclude<Filter, "signed">, (i: Item) => boolean> = {
  all: () => true,
  critical: (i) => i.critical,
  urgent: isUrgent,
  ct: isCt,
  rx: (i) => !isCt(i) && i.modalities.some((m) => m === "CR" || m === "DX"),
};

/** Lista · always in the core's reading order (never re-sorted here). While a case is open the list is a frozen
 * snapshot: studies that arrive meanwhile show as an "N nuevos" chip and merge when tapped or on leaving the case. */
export function WorklistView({
  lang, t, wl, shown, newCount, onMerge, reading, next, onOpen,
}: {
  lang: Lang; t: Dict; wl: Load & { loadedAt: Date | null; stale: boolean }; shown: Worklist | null; newCount: number;
  onMerge: () => void; reading: string | null; next: NextUp | null; onOpen: (id: string) => void;
}) {
  const [filter, setFilter] = useState<Filter>("all");
  const pending = useMemo(() => shown?.items ?? [], [shown]);
  const signed = shown?.signed_today ?? [];
  const current = reading ? pending.find((i) => i.case_id === reading) : undefined;
  const rows = filter === "signed" ? [] : pending.filter((i) => i.case_id !== reading && MATCH[filter](i));
  const count = (f: Filter) => (f === "signed" ? signed.length : pending.filter(MATCH[f]).length);
  const filters: { id: Filter; dot?: string }[] = [
    { id: "all" }, { id: "critical", dot: "bg-crit" }, { id: "urgent", dot: "bg-urg" }, { id: "rx" }, { id: "ct" }, { id: "signed" },
  ];
  const time = wl.loadedAt ? new Intl.DateTimeFormat(lang, { hour: "2-digit", minute: "2-digit" }).format(wl.loadedAt) : null;
  const fmt = new Intl.DateTimeFormat(lang, { hour: "2-digit", minute: "2-digit" });
  return (
    <div className="flex flex-col gap-4">
      <div className="pt-3">
        <p className="h-5 text-[14px] text-muted">{time && `${t.updated} · ${time}${wl.stale ? ` · ${t.stale}` : ""}`}</p>
        <h2 className={HEADLINE}>
          {t["list.title"]} {shown && <span className="font-semibold text-blue">{pending.length}</span>}
        </h2>
      </div>

      {next && filter !== "signed" && (
        <section aria-label={t.nextTitle} data-testid="next-up" className="rounded-card bg-ink p-5 text-ink-text">
          <SectionLabel tone="dark" as="h3">{t.nextTitle}</SectionLabel>
          <p className="mt-2 text-[15.5px] leading-relaxed">{next.why}</p>
          {next.item && (
            <Btn variant="primary" className="mt-4 w-full" onClick={() => onOpen(next.item!.case_id)} aria-label={`${t.openCase} ${next.item.case_id}`}>
              {t.openCase} {next.item.case_id} <ChevronRight aria-hidden size={18} strokeWidth={2} />
            </Btn>
          )}
        </section>
      )}

      <div role="group" aria-label={t.filters} className="flex flex-wrap gap-1.5">
        {filters.map(({ id, dot }) => {
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
              {shown && <span className={on ? "text-muted-d" : "text-muted"}>{count(id)}</span>}
            </button>
          );
        })}
      </div>

      {newCount > 0 && (
        <button type="button" onClick={onMerge} data-testid="new-chip" title={t["list.newHint"]}
          className="inline-flex min-h-11 items-center gap-2 self-start rounded-pill bg-blue px-4 text-[14px] font-medium text-white">
          <span aria-hidden className="size-2 rounded-full bg-white" /> {t["list.new"](newCount)}
        </button>
      )}

      {wl.error && <ErrorNote text={t[`err.${wl.error.kind}`]} retryLabel={t.retry} onRetry={wl.load} />}
      {!shown && !wl.error && (
        <div role="status" aria-label={t.loading} className="flex flex-col gap-2.5">
          <Skeleton className="h-24" />
          <Skeleton className="h-64" />
        </div>
      )}

      {current && filter !== "signed" && (
        <section aria-labelledby="sec-reading" className="flex flex-col gap-2.5">
          <SectionLabel as="h3"><span id="sec-reading">{t["list.reading"]}</span></SectionLabel>
          <div className="rounded-card border-2 border-blue bg-surface px-5" data-testid="reading-now">
            <ArrivalRow item={current} t={t} onOpen={onOpen} />
          </div>
          <p className="px-1 text-[13px] text-muted">{t["list.frozen"]}</p>
        </section>
      )}

      {shown && filter !== "signed" && pending.length === 0 && <p className="rounded-card bg-surface p-5 text-muted">{t["pending.empty"]}</p>}
      {shown && filter !== "signed" && pending.length > 0 && rows.length === 0 && !current && <p className="rounded-card bg-surface p-5 text-muted">{t["pending.none"]}</p>}

      {rows.length > 0 && (
        <section aria-labelledby="sec-order" className="flex flex-col gap-2.5">
          <SectionLabel as="h3"><span id="sec-order">{t["pending.arrival"]}</span></SectionLabel>
          <ol className="flex flex-col gap-2.5" data-testid="worklist">
            {rows.map((i) =>
              i.critical ? (
                <li key={i.study_uid} data-case={i.case_id}>
                  <CriticalRow item={i} t={t} onOpen={onOpen} />
                </li>
              ) : (
                <li key={i.study_uid} data-case={i.case_id} className="rounded-card-sm bg-surface px-5">
                  <ArrivalRow item={i} t={t} onOpen={onOpen} />
                </li>
              ),
            )}
          </ol>
        </section>
      )}

      {filter === "signed" && shown && (
        signed.length === 0 ? (
          <p className="rounded-card bg-surface p-5 text-muted">{t["list.signedEmpty"]}</p>
        ) : (
          <ol className="rounded-card bg-surface px-5" data-testid="signed-list">
            {signed.map((i) => (
              <li key={i.study_uid} className="flex items-center gap-3 border-t border-line-2 first:border-t-0">
                <span className="min-w-0 flex-1"><ArrivalRow item={{ ...i, wait_minutes: null }} t={t} onOpen={onOpen} /></span>
                <time className="shrink-0 font-mono text-[12.5px] text-muted" dateTime={i.signed_at}>{fmt.format(new Date(i.signed_at))}</time>
              </li>
            ))}
          </ol>
        )
      )}
    </div>
  );
}

export function ActivityView({ lang, t, onBusy }: { lang: Lang; t: Dict; onBusy: Busy }) {
  const { data, error, load } = useLoad<{ items: Activity[] }>(api.activity, onBusy);
  const fmt = new Intl.DateTimeFormat(lang, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const kindLabel: Record<string, string> = { tool: t["activity.tool"], view: t["activity.view"], chat: t["activity.chat"], llm: t["activity.llm"], qc: t["activity.qc"], sign: t["activity.sign"], voice: t["activity.voice"] };
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
              {a.kind === "llm" && a.tokens_in != null && (
                <p className="mt-1 font-mono text-[12px] text-muted">
                  {t["activity.tokens"]}: {a.tokens_in} → {a.tokens_out ?? 0}
                  {a.cost_usd != null && ` · ${t["activity.cost"]}: US$ ${a.cost_usd.toFixed(4)}`}
                  {a.model && ` · ${a.model}`}
                </p>
              )}
              {(a.kind === "qc" || a.kind === "sign" || a.kind === "voice") && a.output && <p className="mt-1 text-[13px] text-muted">{a.output}</p>}
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
