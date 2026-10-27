"use client";

import { FileText, Lock, Mic, Pencil } from "lucide-react";
import { useState, type ReactNode } from "react";
import { ApiError, api, type Diff, type Lang, type QcItem, type Report } from "@/lib/api";
import type { Dict } from "@/lib/i18n";
import { ErrorNote, SectionLabel, StudyId } from "./ui";

type Section = "technique" | "findings" | "impression";

/** Wraps the exact conflicting fragments (from open, proven QC alerts) in a crit-dk chip. */
function highlight(text: string, marks: string[]): ReactNode {
  const terms = [...new Set(marks.filter(Boolean))].sort((a, b) => b.length - a.length);
  if (!terms.length) return text;
  const out: ReactNode[] = [];
  let rest = text;
  let k = 0;
  while (rest) {
    let best: { i: number; term: string } | null = null;
    for (const term of terms) {
      const i = rest.indexOf(term);
      if (i >= 0 && (!best || i < best.i)) best = { i, term };
    }
    if (!best) {
      out.push(rest);
      break;
    }
    if (best.i > 0) out.push(rest.slice(0, best.i));
    out.push(
      <mark key={k++} className="rounded-pill bg-crit-dk px-1.5 py-0.5 font-medium text-crit-dkt">
        {best.term}
      </mark>,
    );
    rest = rest.slice(best.i + best.term.length);
  }
  return out;
}

function DiffLine({ diff, t }: { diff: Diff; t: Dict }) {
  return (
    <p className="mt-3 rounded-btn bg-ink-2 px-3 py-2 text-[13px] leading-relaxed text-muted-d">
      <span className="mr-1.5 font-medium text-ink-text">{t.changedIn(t.sectionName[diff.section] ?? diff.section)}:</span>
      {diff.parts.map((p, i) =>
        p.op === "eq" ? (
          <span key={i}>{p.text} </span>
        ) : p.op === "del" ? (
          <del key={i} className="text-crit-dkt">
            {p.text}{" "}
          </del>
        ) : (
          <ins key={i} className="font-medium text-ink-text no-underline">
            {p.text}{" "}
          </ins>
        ),
      )}
    </p>
  );
}

function DraftCard({ r, diff, t, onSave, busy }: { r: Report; diff?: Diff; t: Dict; onSave: (s: Record<Section, string>) => void; busy: boolean }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState<Record<Section, string>>({ technique: r.technique, findings: r.findings, impression: r.impression });
  const marks = (section: "findings" | "impression") =>
    r.qc.filter((i) => i.status === "open" && i.severity === "error").flatMap((i) => i.marks.filter((m) => m.section === section).map((m) => m.text));
  const signed = r.status === "signed";
  const field = (s: Section, label: string, rows: number) => (
    <label className="mt-4 block">
      <SectionLabel tone="dark" as="p">
        {label}
      </SectionLabel>
      <textarea
        value={text[s]}
        rows={rows}
        onChange={(e) => setText({ ...text, [s]: e.target.value })}
        className="mt-1.5 w-full rounded-btn border border-ink-line bg-ink-2 p-3 text-[15px] leading-relaxed text-ink-text focus:border-blue focus:outline-none"
      />
    </label>
  );
  return (
    <section aria-label={`${t.draft} ${r.case_id}`} className="rounded-card bg-ink p-5 text-ink-text sm:p-6">
      <div className="flex items-center justify-between gap-2">
        <SectionLabel tone="dark" as="h3">
          {t.draft} · {t.version(r.version)}
        </SectionLabel>
        <StudyId id={r.case_id} tone="dark" />
      </div>
      {editing ? (
        <>
          {field("technique", t.technique, 2)}
          {field("findings", t.findings, 5)}
          {field("impression", t.impression, 3)}
          <div className="mt-4 flex gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                onSave(text);
                setEditing(false);
              }}
              className="h-[46px] rounded-btn bg-surface px-4 text-[15px] font-medium text-ink disabled:opacity-50"
            >
              {t.save}
            </button>
            <button type="button" onClick={() => setEditing(false)} className="h-[46px] rounded-btn border border-ink-line px-4 text-[15px] font-medium">
              {t.cancel}
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="mt-3 text-[13.5px] text-muted-d">{r.technique}</p>
          <div className="mt-4">
            <SectionLabel tone="dark" as="p">
              {t.findings}
            </SectionLabel>
            <p className="mt-1.5 text-[15.5px] leading-relaxed">{highlight(r.findings, marks("findings"))}</p>
          </div>
          <div className="mt-4">
            <SectionLabel tone="dark" as="p">
              {t.impression}
            </SectionLabel>
            <p className="mt-1.5 text-[15.5px] leading-relaxed">{highlight(r.impression, marks("impression"))}</p>
          </div>
          {diff && <DiffLine diff={diff} t={t} />}
          {!signed && (
            <div className="mt-5 grid grid-cols-2 gap-2.5">
              <button
                type="button"
                disabled
                aria-label={`${t.dictate} (${t.soon})`}
                className="flex min-h-[54px] cursor-not-allowed flex-col items-center justify-center rounded-btn border border-dashed border-ink-line px-2"
              >
                <span className="flex items-center gap-2 text-[15px] font-medium text-ink-text/70">
                  <Mic aria-hidden size={17} strokeWidth={1.8} /> {t.dictate}
                </span>
                <span className="text-[11px] text-muted-d">{t.soon}</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setText({ technique: r.technique, findings: r.findings, impression: r.impression });
                  setEditing(true);
                }}
                className="flex min-h-[54px] items-center justify-center gap-2 rounded-btn bg-surface px-2 text-[15px] font-medium text-ink"
              >
                <Pencil aria-hidden size={17} strokeWidth={1.8} /> {t.editText}
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function QcCard({ item, t, onApply, onDismiss, busy, locked }: { item: QcItem; t: Dict; onApply: () => void; onDismiss: (reason: string) => void; busy: boolean; locked: boolean }) {
  const [dismissing, setDismissing] = useState(false);
  const [reason, setReason] = useState("");
  const error = item.severity === "error";
  const open = item.status === "open";
  const box = (label: string, text: string | null, section: "findings" | "impression") => (
    <div className="min-w-0 flex-1 rounded-btn bg-line-2 p-3">
      <p className="label text-muted">{label}</p>
      <p className="mt-1 text-[14px] leading-relaxed text-ink">
        {text ? highlight(text, error ? item.marks.filter((m) => m.section === section).map((m) => m.text) : []) : "—"}
      </p>
    </div>
  );
  return (
    <section aria-label={`RAD·QC ${t.qcRule[item.rule] ?? item.rule}`} className={`rounded-card bg-surface p-5 ${open ? "" : "opacity-70"}`}>
      <div className="flex items-start justify-between gap-3">
        <h4 className={`flex items-center gap-2 text-[16px] font-semibold ${error ? "text-crit-text" : "text-ink"}`}>
          <span aria-hidden className={`size-2 shrink-0 rounded-full ${error ? "bg-crit" : "bg-urg"}`} />
          <span>
            {error ? t.qcError : t.qcVerify} · {t.qcRule[item.rule] ?? item.rule}
          </span>
        </h4>
        <span className="shrink-0 font-mono text-[12px] font-medium text-muted">RAD·QC</span>
      </div>
      {item.explanation && <p className="mt-2 text-[14px] text-muted">{item.explanation}</p>}
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        {box(item.body_label === "indication" ? t.indicationLabel : t.body, item.body_excerpt, "findings")}
        {box(t.impression, item.impression_excerpt, "impression")}
      </div>
      {item.fix_replace && open && (
        <p className="mt-3 text-[14px]">
          <span className="text-muted">{t.proposed}: </span>
          {item.fix_replace}
        </p>
      )}
      {item.status === "dismissed" && item.reason && <p className="mt-3 text-[13.5px] text-muted">{t.dismissedBecause(item.reason)}</p>}
      {open && !locked && (
        <div className="mt-4 flex flex-wrap gap-2">
          {item.fix_replace && (
            <button type="button" disabled={busy} onClick={onApply} className="h-[46px] rounded-btn bg-blue px-4 text-[15px] font-medium text-white disabled:opacity-50">
              {t.applyFix}
            </button>
          )}
          {!dismissing ? (
            <button type="button" disabled={busy} onClick={() => setDismissing(true)} className="h-[46px] rounded-btn border border-line bg-surface px-4 text-[15px] font-medium text-ink">
              {t.dismissWithReason}
            </button>
          ) : (
            <form
              className="flex w-full flex-wrap gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                if (reason.trim().length >= 3) onDismiss(reason.trim());
              }}
            >
              <label className="sr-only" htmlFor={`reason-${item.id}`}>
                {t.reasonLabel}
              </label>
              <input
                id={`reason-${item.id}`}
                autoFocus
                value={reason}
                maxLength={300}
                onChange={(e) => setReason(e.target.value)}
                placeholder={t.reasonPlaceholder}
                className="h-[46px] min-w-0 flex-1 rounded-btn border border-line bg-surface px-3 text-[15px] focus:border-blue focus:outline-none"
              />
              <button type="submit" disabled={busy || reason.trim().length < 3} className="h-[46px] rounded-btn bg-ink px-4 text-[15px] font-medium text-ink-text disabled:opacity-40">
                {t.confirmDismiss}
              </button>
            </form>
          )}
        </div>
      )}
    </section>
  );
}

function SignBar({ r, t, onSign, busy, lang }: { r: Report; t: Dict; onSign: () => void; busy: boolean; lang: Lang }) {
  if (r.status === "signed") {
    const at = r.signed_at ? new Intl.DateTimeFormat(lang, { dateStyle: "short", timeStyle: "short" }).format(new Date(r.signed_at)) : "";
    return (
      <div role="status" className="flex items-center gap-3 rounded-card bg-surface p-4">
        <Lock aria-hidden size={18} strokeWidth={1.8} className="shrink-0 text-ink" />
        <p className="text-[15px] font-medium">{t.signedBy(r.signed_by ?? "—", at)}</p>
      </div>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-card bg-surface p-4">
      <p className="flex min-w-0 flex-1 items-center gap-2 text-[14px] text-muted">
        <Lock aria-hidden size={16} strokeWidth={1.8} className="shrink-0" />
        {r.qc_pending ? t.qcRunning : r.signable ? t.signNote : t.signPending(r.open_alerts)}
      </p>
      <button
        type="button"
        disabled={!r.signable || busy}
        onClick={onSign}
        className="h-[46px] min-w-28 rounded-btn bg-ink px-5 text-[15px] font-semibold text-ink-text disabled:cursor-not-allowed disabled:opacity-35"
      >
        {t.sign}
      </button>
    </div>
  );
}

/** Pantalla 04: draft + RAD·QC + human-only signature. Every change re-runs QC on the server. */
export function ReportCard({ initial, diff: initialDiff, t, lang, stale = false }: { initial: Report; diff?: Diff; t: Dict; lang: Lang; stale?: boolean }) {
  const [r, setR] = useState(initial);
  const [diff, setDiff] = useState<Diff | undefined>(initialDiff);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (fn: () => Promise<Report & { diff?: Diff }>) => {
    setBusy(true);
    setError(null);
    try {
      const next = await fn();
      setR(next);
      setDiff(next.diff);
    } catch (e) {
      setError(e instanceof ApiError && e.kind === "conflict" ? e.message : t[`err.${e instanceof ApiError ? e.kind : "other"}`]);
    } finally {
      setBusy(false);
    }
  };

  if (stale) {
    // an older snapshot of a draft shown again further down the chat: read-only, so nobody acts on old state
    return (
      <section aria-label={`${t.draft} ${r.case_id} ${t.version(r.version)}`} className="rounded-card bg-ink-2 px-5 py-4 text-ink-text opacity-80">
        <p className="flex flex-wrap items-baseline gap-x-2 text-[14px]">
          <span className="font-medium">
            {t.draft} · {t.version(r.version)}
          </span>
          <StudyId id={r.case_id} tone="dark" />
          <span className="text-muted-d">· {t.olderVersion}</span>
        </p>
        {diff && <DiffLine diff={diff} t={t} />}
      </section>
    );
  }

  const visible = r.qc.filter((i) => i.status === "open" || i.status === "dismissed");
  return (
    <div className="flex flex-col gap-3" aria-busy={busy}>
      <DraftCard key={r.version} r={r} diff={diff} t={t} busy={busy} onSave={(s) => run(() => api.editReport(r.case_id, r.version, s, lang))} />
      {(r.qc_mode === "rules" || r.qc_mode === "seed") && r.status === "draft" && (
        <p className="flex items-center gap-1.5 px-1 text-[13px] text-muted">
          <FileText aria-hidden size={14} strokeWidth={1.8} /> {r.qc_mode === "seed" ? t.qcSeed : t.qcRules}
        </p>
      )}
      {visible.length === 0 && r.status === "draft" && <p className="px-1 text-[13.5px] text-muted">{t.qcClean}</p>}
      {visible.map((item) => (
        <QcCard
          key={item.id}
          item={item}
          t={t}
          busy={busy}
          locked={r.status === "signed"}
          onApply={() => run(() => api.applyFix(r.case_id, item.id, lang))}
          onDismiss={(reason) => run(() => api.dismiss(r.case_id, item.id, reason))}
        />
      ))}
      {error && <ErrorNote text={error} retryLabel={t.retry} />}
      <SignBar r={r} t={t} lang={lang} busy={busy} onSign={() => run(() => api.sign(r.case_id, r.version))} />
    </div>
  );
}
