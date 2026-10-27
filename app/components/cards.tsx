"use client";

import { ArrowRight, ChevronRight, FileText, Image as ImageIcon } from "lucide-react";
import { useState } from "react";
import { useStation } from "./stationContext";
import type { Case, Item } from "@/lib/api";
import { fmtWait, type Dict } from "@/lib/i18n";
import { Btn, DOT, ReasonChip, SectionLabel, StudyId } from "./ui";

type Open = (id: string) => void;

const title = (i: Item) => i.exam ?? i.modalities.join(" / ");
const short = (s: string | null) => (s ? s.replace(/[.;]\s*$/, "") : null);

/** 01 · "Siguiente estudio" (ink). */
export function NextStudyCard({ item, total, list, t, onOpen }: { item: Item; total: number; list?: Item[]; t: Dict; onOpen: Open }) {
  const [expanded, setExpanded] = useState(false);
  const lead = item.reasons.find((r) => r.kind === "critical") ?? item.reasons[0];
  return (
    <section aria-label={`${t.next} ${item.case_id}`} className="rounded-card bg-ink p-5 text-ink-text sm:p-6">
      <div className="flex items-center justify-between gap-2">
        <SectionLabel tone="dark" as="h3">
          {t.next}
        </SectionLabel>
        {item.wait_minutes != null && (
          <span className="text-[13.5px] text-muted-d">
            {t.waiting} <strong className="font-semibold text-ink-text">{fmtWait(item.wait_minutes)}</strong>
          </span>
        )}
      </div>
      <p className="mt-4">
        <StudyId id={item.case_id} tone="dark" />
      </p>
      <p className="mt-0.5 text-[28px] font-medium leading-tight tracking-[-0.02em]">{title(item)}</p>
      <div className="mt-4 flex min-w-0 flex-wrap gap-1.5">
        {lead && <ReasonChip r={lead} tone="dark" />}
        {item.reason && (
          <span className="inline-flex h-7 max-w-full items-center truncate rounded-pill bg-ink-2 px-3 text-[12px] font-medium text-ink-text">
            <span className="truncate">{short(item.reason)}</span>
          </span>
        )}
      </div>
      <div className="mt-5 flex gap-2.5">
        <button
          type="button"
          onClick={() => onOpen(item.case_id)}
          aria-label={`${t.openStudy} ${item.case_id}`}
          className="inline-flex h-[54px] min-w-0 flex-1 items-center justify-center gap-2 rounded-btn bg-surface text-[16px] font-medium text-ink hover:bg-line-2"
        >
          {t.openStudy} <ArrowRight aria-hidden size={18} strokeWidth={2} />
        </button>
        <StationButton caseId={item.case_id} t={t} compact />
      </div>
      {total > 1 && (
        <p className="mt-3 text-[12.5px] text-muted-d">
          1 / {total}
        </p>
      )}
      {list && list.length > 1 && (
        <div className="mt-2 border-t border-ink-line pt-2">
          <button
            type="button"
            aria-expanded={expanded}
            onClick={() => setExpanded((v) => !v)}
            className="min-h-11 text-[14px] font-medium text-ink-text underline-offset-4 hover:underline"
          >
            {expanded ? t.hideAll : t.showAll(list.length)}
          </button>
          {expanded && (
            <ol className="mt-1">
              {list.map((i) => (
                <li key={i.study_uid} className="border-t border-ink-line first:border-t-0">
                  <ArrivalRow item={i} t={t} onOpen={onOpen} tone="dark" />
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </section>
  );
}

/** 02 · critical row (ink): ID, exam, "indication · technologist note", wait in red. */
export function CriticalRow({ item, t, onOpen }: { item: Item; t: Dict; onOpen: Open }) {
  const sub = [short(item.reason), short(item.tech_note)].filter(Boolean).join(" · ");
  return (
    <button
      type="button"
      onClick={() => onOpen(item.case_id)}
      aria-label={`${t.openCase} ${item.case_id}`}
      className="flex w-full items-center gap-3 rounded-card-sm bg-ink px-5 py-4 text-left text-ink-text"
    >
      <span className="min-w-0 flex-1">
        <StudyId id={item.case_id} tone="dark" />
        <span className="mt-0.5 block text-[19px] font-medium leading-snug tracking-[-0.01em]">{title(item)}</span>
        {sub && <span className="mt-1 line-clamp-2 text-[13.5px] leading-snug text-muted-d">{sub}</span>}
      </span>
      <span className="flex shrink-0 flex-col items-end gap-1">
        {item.wait_minutes != null && <span className="text-[14px] font-semibold text-crit-dkt">{fmtWait(item.wait_minutes)}</span>}
        <ChevronRight aria-hidden size={18} strokeWidth={1.8} className="text-muted-d" />
      </span>
    </button>
  );
}

/** 02 · compact row: priority dot, ID, exam, wait. */
export function ArrivalRow({ item, t, onOpen, tone = "light" }: { item: Item; t: Dict; onOpen: Open; tone?: "light" | "dark" }) {
  const dark = tone === "dark";
  const kind = item.critical ? "critical" : (item.priority ?? item.reasons[0]?.kind ?? "unknown");
  const dot = DOT[kind] ?? "bg-neutral";
  const prio = item.reasons.map((r) => `${r.label} · ${r.source}`).join(", ");
  return (
    <button
      type="button"
      onClick={() => onOpen(item.case_id)}
      aria-label={`${t.openCase} ${item.case_id} (${prio})`}
      className={`flex min-h-14 w-full items-center gap-3 py-3 text-left ${dark ? "text-ink-text" : "text-ink"}`}
    >
      <span aria-hidden className={`size-2 shrink-0 rounded-full ${dot}`} />
      <span className="w-[86px] shrink-0">
        <StudyId id={item.case_id} tone={tone} />
      </span>
      <span className="min-w-0 flex-1 text-[15.5px] font-medium leading-snug">{title(item)}</span>
      {item.wait_minutes != null && <span className={`shrink-0 text-[13.5px] ${dark ? "text-muted-d" : "text-muted"}`}>{fmtWait(item.wait_minutes)}</span>}
    </button>
  );
}

export function PriorityGrid({ critical, urgent, t }: { critical: number; urgent: number; t: Dict }) {
  const cell = (label: string, n: number, dot: string) => (
    <div className="rounded-card-sm bg-surface px-5 py-4">
      <p className="flex items-center gap-2 text-[15px] text-muted">
        <span aria-hidden className={`size-2 rounded-full ${dot}`} />
        {label}
      </p>
      <p className="mt-2 text-[40px] font-light leading-none tracking-[-0.02em] text-ink">{n}</p>
    </div>
  );
  return (
    <div className="grid grid-cols-2 gap-2.5">
      {cell(t.critical, critical, critical ? "bg-crit" : "bg-neutral")}
      {cell(t.urgent, urgent, urgent ? "bg-urg" : "bg-neutral")}
    </div>
  );
}

/** 01 · quick prompts as a white list; only real actions are enabled. */
export function QuickPrompts({ pending, t, onPending }: { pending: number | null; t: Dict; onPending: () => void }) {
  const soon = (label: string) => (
    <li className="border-t border-line-2">
      <button type="button" disabled aria-label={`${label} (${t.soon})`} className="flex min-h-14 w-full cursor-not-allowed items-center justify-between gap-3 px-5 text-left">
        <span className="text-[16px] text-muted">{label}</span>
        <span className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted">{t.soon}</span>
      </button>
    </li>
  );
  return (
    <ul className="rounded-card bg-surface">
      <li>
        <button type="button" onClick={onPending} className="flex min-h-14 w-full items-center justify-between gap-3 px-5 text-left">
          <span className="text-[16px] font-medium">{t.viewAllPending}</span>
          {pending != null ? <span className="text-[15px] text-muted">{pending}</span> : <ChevronRight aria-hidden size={18} strokeWidth={1.8} className="text-muted" />}
        </button>
      </li>
      <li className="border-t border-line-2">
        <StationLink t={t} />
      </li>
      {soon(t["prompt.tomorrow"])}
      {soon(t["prompt.summary"])}
    </ul>
  );
}

export function EvidenceCard({ item, t, onOpen }: { item: Item; t: Dict; onOpen: Open }) {
  return (
    <section aria-label={`${t.evidence} ${item.case_id}`} className="rounded-card bg-surface p-5">
      <div className="flex items-center justify-between gap-2">
        <SectionLabel as="h3">{t.evidence}</SectionLabel>
        <StudyId id={item.case_id} />
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {item.reasons.map((r) => (
          <ReasonChip key={r.kind + r.source} r={r} />
        ))}
      </div>
      <p className="mt-3 text-[14px] leading-relaxed text-muted">{t.rule}</p>
      <Btn variant="primary" className="mt-4" onClick={() => onOpen(item.case_id)} aria-label={`${t.openCase} ${item.case_id}`}>
        {t.openCase} <ChevronRight aria-hidden size={18} strokeWidth={2} />
      </Btn>
    </section>
  );
}

function fmtDate(d: string | null) {
  return d && d.length === 8 ? `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6)}` : null;
}

/** 03 · case card (ink). */
export function CaseCard({ c, t, anchorId, onDraft }: { c: Case; t: Dict; anchorId: string; onDraft?: (id: string) => void }) {
  const date = fmtDate(c.study_date);
  const meta = [c.sex ? (t.sex[c.sex] ?? c.sex) : t.unknown, c.age != null ? t.years(c.age) : t.unknown, date ? `${t.dicomDate} ${date}` : t.unknown];
  const yn = (v: boolean | null) => (v == null ? t.unknown : v ? t.yes : t.no);
  const priors = `${t.priorsDeclared}: ${yn(c.priors_declared)}. ${t.priorsInPacs}: ${c.priors_in_pacs ?? t.unknown}.`;
  return (
    <section id={anchorId} aria-label={`${t.caseLabel} ${c.case_id}`} className="scroll-mt-4 rounded-card bg-ink p-5 text-ink-text sm:p-6">
      <p className="text-[25px] font-medium leading-tight tracking-[-0.02em]">{c.exam ?? c.modalities.join(" / ")}</p>
      <p className="mt-1.5 flex flex-wrap gap-x-1.5 text-[13.5px] text-muted-d">
        {[c.case_id, ...meta].map((m, i) => (
          <span key={i} className={`whitespace-nowrap ${i === 0 ? "font-mono font-medium" : ""}`}>
            {i > 0 && "· "}
            {m}
          </span>
        ))}
      </p>
      {c.reasons.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {c.reasons.map((r) => (
            <ReasonChip key={r.kind + r.source} r={r} tone="dark" />
          ))}
        </div>
      )}
      <hr className="my-5 border-ink-line" />

      <SectionLabel tone="dark" as="p">
        {t.indication}
      </SectionLabel>
      <p className="mt-1 text-[15.5px] leading-relaxed">{c.reason ?? <span className="text-muted-d">{t.noMeta}</span>}</p>

      <p className={`label mt-4 ${c.critical ? "text-crit-dkt" : "text-muted-d"}`}>
        {t.techNote}
      </p>
      {c.critical && <p className="mt-1 text-[13px] font-medium text-crit-dkt">{t.techCritical}</p>}
      <p className="mt-1 text-[15.5px] leading-relaxed">{c.tech_note ?? <span className="text-muted-d">{t.noMeta}</span>}</p>

      <SectionLabel tone="dark" as="p">
        <span className="mt-4 block">{t.priors}</span>
      </SectionLabel>
      <p className="mt-1 text-[15.5px] leading-relaxed">{priors}</p>

      <div className="mt-5 grid grid-cols-2 gap-2.5">
        <StationButton caseId={c.case_id} t={t} />
        <button
          type="button"
          disabled
          aria-label={`${t.searchPrior} (${t.soon})`}
          className="flex min-h-[54px] cursor-not-allowed flex-col items-center justify-center rounded-btn border border-ink-line bg-ink-2 px-2 text-ink-text"
        >
          <span className="flex items-center gap-2 text-[15px] font-medium">
            <FileText aria-hidden size={18} strokeWidth={1.8} /> {t.searchPrior}
          </span>
          <span className="text-[11px] text-muted-d">{t.soon}</span>
        </button>
      </div>
      {onDraft && (
        <button
          type="button"
          onClick={() => onDraft(c.case_id)}
          aria-label={`${t.viewDraft} ${c.case_id}`}
          className="mt-2.5 flex min-h-[48px] w-full items-center justify-center gap-2 rounded-btn border border-ink-line text-[15px] font-medium text-ink-text hover:bg-ink-2"
        >
          <FileText aria-hidden size={17} strokeWidth={1.8} /> {t.viewDraft}
        </button>
      )}
      <p className="mt-4 text-[12px] leading-relaxed text-muted-d">{t.synthetic}</p>
    </section>
  );
}

export function SuggestedReplies({ items }: { items: { label: string; onClick: () => void; primary?: boolean }[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((s) => (
        <button
          key={s.label}
          type="button"
          onClick={s.onClick}
          className={`inline-flex min-h-12 items-center rounded-pill px-5 text-[15px] font-medium ${s.primary ? "bg-ink text-ink-text" : "border border-line bg-surface text-ink hover:border-muted"}`}
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}

/** Images are read on the linked reading station, never on the phone ("Pronto" until one is linked). */
function StationButton({ caseId, t, compact = false }: { caseId: string; t: Dict; compact?: boolean }) {
  const station = useStation();
  const [sent, setSent] = useState(false);
  const label = station.linked ? `${t.openInStation} ${caseId}` : `${t.openInStation} (${t.noStation})`;
  const go = async () => {
    if (await station.open(caseId)) {
      setSent(true);
      setTimeout(() => setSent(false), 2500);
    }
  };
  if (compact) {
    return (
      <button
        type="button"
        disabled={!station.linked}
        onClick={go}
        aria-label={label}
        title={label}
        className="flex h-[54px] w-[76px] shrink-0 flex-col items-center justify-center gap-0.5 rounded-btn bg-ink-2 text-ink-text disabled:cursor-not-allowed disabled:text-muted-d"
      >
        <ImageIcon aria-hidden size={18} strokeWidth={1.8} />
        <span aria-hidden className="text-[10.5px] leading-none">{sent ? "✓" : station.linked ? t.station : t.soonShort}</span>
      </button>
    );
  }
  return (
    <button
      type="button"
      disabled={!station.linked}
      onClick={go}
      aria-label={label}
      className="flex min-h-[54px] flex-col items-center justify-center rounded-btn bg-surface px-2 text-ink disabled:cursor-not-allowed disabled:bg-surface/85"
    >
      <span className="flex items-center gap-2 text-[15px] font-medium">
        <ImageIcon aria-hidden size={18} strokeWidth={1.8} /> {t.openInStation}
      </span>
      <span role="status" className="text-[11px] text-muted">{sent ? t.sentToStation : station.linked ? "" : t.noStation}</span>
    </button>
  );
}

function StationLink({ t }: { t: Dict }) {
  const station = useStation();
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  if (station.linked) {
    return (
      <div className="flex min-h-14 items-center justify-between gap-3 px-5">
        <span className="flex items-center gap-2 text-[16px] font-medium">
          <span aria-hidden className="size-2 rounded-full bg-blue" /> {t.stationLinked}
        </span>
        <button
          type="button"
          onClick={async () => {
            await station.unlink();
            setOpen(false); // back to the "Vincular estación" entry, not the old code form
            setCode("");
            setError(null);
          }}
          className="min-h-11 text-[14px] text-muted underline-offset-4 hover:underline"
        >
          {t.unlink}
        </button>
      </div>
    );
  }
  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)} className="flex min-h-14 w-full items-center justify-between gap-3 px-5 text-left">
        <span className="text-[16px] font-medium">{t.linkStation}</span>
        <ChevronRight aria-hidden size={18} strokeWidth={1.8} className="text-muted" />
      </button>
    );
  }
  return (
    <form
      className="flex flex-col gap-2 px-5 py-3"
      onSubmit={async (e) => {
        e.preventDefault();
        setError(await station.link(code));
      }}
    >
      <label htmlFor="station-code" className="text-[14px] text-muted">
        {t.linkStationHint}
      </label>
      <div className="flex gap-2">
        <input
          id="station-code"
          inputMode="numeric"
          autoComplete="one-time-code"
          pattern="[0-9]{4}"
          maxLength={4}
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          aria-label={t.stationCode}
          className="h-[46px] w-32 rounded-btn border border-line bg-surface px-3 text-center font-mono text-[20px] tracking-[0.3em] focus:border-blue focus:outline-none"
        />
        <button type="submit" disabled={code.length !== 4} className="h-[46px] rounded-btn bg-blue px-4 text-[15px] font-medium text-white disabled:opacity-40">
          {t.link}
        </button>
      </div>
      {error && <p role="alert" className="text-[14px] text-ink">{error}</p>}
    </form>
  );
}
