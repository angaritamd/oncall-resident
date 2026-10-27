"use client";

import { ChevronRight, Image as ImageIcon, History } from "lucide-react";
import { useState } from "react";
import type { Case, Item } from "@/lib/api";
import type { Dict } from "@/lib/i18n";
import { Btn, ReasonChip, SectionLabel, StudyId } from "./ui";

type Open = (id: string) => void;
type Ask = (text: string) => void;

const title = (i: Item) => i.exam ?? i.modalities.join(" / ");

export function NextStudyCard({ item, total, list, t, onOpen, onAsk }: { item: Item; total: number; list?: Item[]; t: Dict; onOpen: Open; onAsk: Ask }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <section aria-label={`${t.next} ${item.case_id}`} className="rounded-card bg-ink p-5 text-ink-text">
      <div className="flex items-center justify-between gap-2">
        <SectionLabel tone="dark" as="h3">
          {t.next}
        </SectionLabel>
        <span className="text-[12px] text-muted-d">1 / {total}</span>
      </div>
      <p className="mt-3 text-[24px] font-medium leading-tight tracking-[-0.01em]">{title(item)}</p>
      <div className="mt-1 flex flex-wrap items-center gap-x-2">
        <StudyId id={item.case_id} tone="dark" />
        {item.wait_minutes != null && <span className="text-[13px] text-muted-d">· {t.wait(item.wait_minutes)}</span>}
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {item.reasons.map((r) => (
          <ReasonChip key={r.kind + r.source} r={r} tone="dark" />
        ))}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Btn variant="primary" onClick={() => onOpen(item.case_id)} aria-label={`${t.openCase} ${item.case_id}`}>
          {t.openCase} <ChevronRight aria-hidden size={18} strokeWidth={2} />
        </Btn>
        <Btn variant="dark-outline" onClick={() => onAsk(t.whyText(item.case_id))}>
          {t.whyFirst}
        </Btn>
      </div>
      {list && list.length > 1 && (
        <div className="mt-4 border-t border-ink-line pt-2">
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
                  <StudyRowButton item={i} t={t} onOpen={onOpen} tone="dark" />
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </section>
  );
}

export function StudyRowButton({ item, t, onOpen, tone = "light" }: { item: Item; t: Dict; onOpen: Open; tone?: "light" | "dark" }) {
  const dark = tone === "dark";
  return (
    <button
      type="button"
      onClick={() => onOpen(item.case_id)}
      aria-label={`${t.openCase} ${item.case_id}`}
      className={`flex min-h-16 w-full items-center gap-3 py-3 text-left ${dark ? "text-ink-text" : "text-ink"}`}
    >
      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-baseline gap-x-2">
          <span className="text-[15px] font-medium">{title(item)}</span>
          <StudyId id={item.case_id} tone={tone} />
        </span>
        <span className="mt-1.5 flex flex-wrap items-center gap-1.5">
          {item.reasons.map((r) => (
            <ReasonChip key={r.kind + r.source} r={r} tone={tone} />
          ))}
          {item.wait_minutes != null && <span className={`text-[12.5px] ${dark ? "text-muted-d" : "text-muted"}`}>{t.wait(item.wait_minutes)}</span>}
        </span>
      </span>
      <ChevronRight aria-hidden size={18} strokeWidth={1.8} className={dark ? "text-muted-d" : "text-muted"} />
    </button>
  );
}

export function PriorityGrid({ critical, urgent, t }: { critical: number; urgent: number; t: Dict }) {
  const cell = (label: string, n: number, sub: string, crit: boolean) => (
    <div className="rounded-card-sm bg-surface p-4">
      <p className="label flex items-center gap-1.5 text-muted">
        <span aria-hidden className={`size-1.5 rounded-full ${crit ? (n > 0 ? "bg-crit" : "bg-neutral") : n > 0 ? "bg-urg" : "bg-neutral"}`} />
        {label}
      </p>
      <p className={`mt-2 text-[30px] font-light leading-none tracking-[-0.02em] ${crit && n > 0 ? "text-crit-text" : "text-ink"}`}>{n}</p>
      <p className="mt-1.5 text-[12.5px] text-muted">{sub}</p>
    </div>
  );
  return (
    <div className="grid grid-cols-2 gap-2.5">
      {cell(t.critical, critical, t.criticalSub, true)}
      {cell(t.urgent, urgent, t.urgentSub, false)}
    </div>
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

export function CaseCard({ c, t }: { c: Case; t: Dict }) {
  const meta = [c.sex ? (t.sex[c.sex] ?? c.sex) : t.unknown, c.age != null ? t.years(c.age) : t.unknown, fmtDate(c.study_date) ? `${t.dicomDate} ${fmtDate(c.study_date)}` : t.unknown];
  const yn = (v: boolean | null) => (v == null ? t.unknown : v ? t.yes : t.no);
  return (
    <section id={`case-${c.case_id}`} aria-label={`${t.caseLabel} ${c.case_id}`} className="scroll-mt-4 rounded-card bg-ink p-5 text-ink-text">
      <div className="flex items-center justify-between gap-2">
        <SectionLabel tone="dark" as="h3">
          {t.caseLabel}
        </SectionLabel>
        <StudyId id={c.case_id} tone="dark" />
      </div>
      <p className="mt-3 text-[24px] font-medium leading-tight tracking-[-0.01em]">{c.exam ?? c.modalities.join(" / ")}</p>
      <p className="mt-1 flex flex-wrap gap-x-1.5 text-[13.5px] text-muted-d">
        {[c.modalities.join("/"), ...meta].map((m, i) => (
          <span key={i} className="whitespace-nowrap">
            {i > 0 && "· "}
            {m}
          </span>
        ))}
      </p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {c.reasons.map((r) => (
          <ReasonChip key={r.kind + r.source} r={r} tone="dark" />
        ))}
        {c.wait_minutes != null && <span className="self-center text-[12.5px] text-muted-d">{t.wait(c.wait_minutes)}</span>}
      </div>

      <div className="mt-5">
        <SectionLabel tone="dark" as="p">
          {t.indication}
        </SectionLabel>
        <p className="mt-1.5 text-[15px] leading-relaxed">{c.reason ?? <span className="text-muted-d">{t.noMeta}</span>}</p>
      </div>

      <div className={`mt-4 rounded-card-sm p-4 ${c.critical ? "bg-crit-dk" : "bg-ink-2"}`}>
        <p className={`label flex items-center gap-1.5 ${c.critical ? "text-crit-dkt" : "text-muted-d"}`}>
          {c.critical && <span aria-hidden className="size-1.5 rounded-full bg-crit-dkt" />}
          {t.techNote}
        </p>
        {c.critical && <p className="mt-1.5 text-[13px] font-medium text-crit-dkt">{t.techCritical}</p>}
        <p className="mt-1.5 text-[15px] leading-relaxed">{c.tech_note ?? <span className="text-muted-d">{t.noMeta}</span>}</p>
      </div>

      <div className="mt-4">
        <SectionLabel tone="dark" as="p">
          {t.priors}
        </SectionLabel>
        <dl className="mt-1.5 grid grid-cols-[1fr_auto] gap-y-1 text-[15px]">
          <dt className="text-muted-d">{t.priorsDeclared}</dt>
          <dd className="font-medium">{yn(c.priors_declared)}</dd>
          <dt className="text-muted-d">{t.priorsInPacs}</dt>
          <dd className="font-medium">{c.priors_in_pacs ?? t.unknown}</dd>
        </dl>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-2">
        {[
          { label: t.viewImages, Icon: ImageIcon },
          { label: t.viewPrior, Icon: History },
        ].map(({ label, Icon }) => (
          <button
            key={label}
            type="button"
            disabled
            aria-label={`${label} (${t.soon})`}
            className="flex min-h-[54px] cursor-not-allowed flex-col items-center justify-center rounded-btn border border-dashed border-ink-line px-2 text-ink-text/70"
          >
            <span className="flex items-center gap-1.5 text-[14px] font-medium">
              <Icon aria-hidden size={16} strokeWidth={1.8} /> {label}
            </span>
            <span className="text-[11px] text-muted-d">{t.soon}</span>
          </button>
        ))}
      </div>
      <p className="mt-4 break-all font-mono text-[11px] text-muted-d">{c.study_uid}</p>
      <p className="mt-2 text-[12px] leading-relaxed text-muted-d">{t.synthetic}</p>
    </section>
  );
}

export function SuggestedReplies({ items }: { items: { label: string; onClick: () => void }[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((s) => (
        <Btn key={s.label} variant="pill" onClick={s.onClick}>
          {s.label}
        </Btn>
      ))}
    </div>
  );
}
