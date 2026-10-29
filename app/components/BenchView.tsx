"use client";

import { Check, X } from "lucide-react";
import { useCallback, useState } from "react";
import { api, type Bench, type BenchCase } from "@/lib/api";
import { dict } from "@/lib/i18n";
import { highlight } from "./report";
import { Btn, ErrorNote, SectionLabel, Skeleton, StudyId } from "./ui";
import { useLoad } from "./useLoad";

const t = dict.es;
const noop = () => {};

// subtype ids from radqc/radqc/taxonomy.py
const SUBTYPE: Record<string, string> = {
  measure_number: "Medida distinta",
  measure_unit: "Medida: unidad cambiada",
  laterality: "Lateralidad",
  omission_total: "Omisión total",
  omission_partial: "Omisión parcial",
  normal_template: "Plantilla normal firmada",
  indication_unanswered: "Indicación sin responder",
  clean: "Sin error",
  clean_tricky: "Sin error (trampa)",
};

/** RAD·QC v5 benchmark: the radiologist validates each synthetic case (ANG-174) before it scores any model. */
export default function BenchView() {
  const { data, error, load } = useLoad<Bench>(api.bench, noop);
  const [only, setOnly] = useState<"todo" | "all">("todo");
  const [local, setLocal] = useState<Record<string, BenchCase>>({});
  const cases = (data?.cases ?? []).map((c) => local[c.id] ?? c);
  const shown = only === "todo" ? cases.filter((c) => !c.verdict) : cases;
  const done = cases.filter((c) => c.verdict).length;
  const valid = cases.filter((c) => c.verdict?.verdict === "valid").length;
  const onSaved = useCallback((c: BenchCase) => setLocal((m) => ({ ...m, [c.id]: c })), []);

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[640px] flex-col gap-4 px-4 pb-10 pt-6">
      <header>
        <h1 className="text-[32px] font-light leading-[1.1] tracking-[-0.02em] text-ink">Benchmark RAD·QC</h1>
        <p className="mt-2 text-[15px] leading-snug text-muted">
          Casos sintéticos generados con Muse Wonder. Solo evalúan: nunca entran al entrenamiento. Marca si el error
          plantado es real y está bien citado.
        </p>
        {data && (
          <p data-testid="bench-progress" className="mt-3 text-[15px] text-ink">
            <span className="font-semibold">{done}</span> de {cases.length} revisados · {valid} válidos
          </p>
        )}
      </header>
      <div role="group" aria-label="Filtro" className="flex gap-2">
        {(["todo", "all"] as const).map((k) => (
          <button
            key={k}
            type="button"
            aria-pressed={only === k}
            onClick={() => setOnly(k)}
            className={`min-h-11 rounded-pill border px-4 text-[14px] font-medium ${only === k ? "border-ink bg-ink text-white" : "border-line bg-surface text-ink"}`}
          >
            {k === "todo" ? `Por revisar (${cases.length - done})` : `Todos (${cases.length})`}
          </button>
        ))}
      </div>
      {error && <ErrorNote text={t[`err.${error.kind}`]} retryLabel={t.retry} onRetry={load} />}
      {!data && !error && <Skeleton className="h-64" />}
      {data && !shown.length && <p className="rounded-card bg-surface p-5 text-[15px] text-muted">{cases.length ? "Todo revisado." : "No hay casos cargados."}</p>}
      {shown.map((c) => (
        <BenchCard key={c.id} c={c} onSaved={onSaved} />
      ))}
    </div>
  );
}

function BenchCard({ c, onSaved }: { c: BenchCase; onSaved: (c: BenchCase) => void }) {
  const [note, setNote] = useState(c.verdict?.note ?? "");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const e = c.expected;
  const body = e && e.type !== "indication_unanswered" ? [e.body_excerpt] : [];
  const ind = e?.type === "indication_unanswered" ? [e.body_excerpt] : [];
  const imp = e?.impression_excerpt ? [e.impression_excerpt] : [];

  async function save(verdict: "valid" | "invalid") {
    setBusy(true);
    setFailed(false);
    try {
      const v = await api.benchVerdict(c.id, verdict, note);
      onSaved({ ...c, verdict: v });
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <article data-testid="bench-case" aria-label={c.id} className="rounded-card bg-surface p-5">
      <div className="flex flex-wrap items-center gap-2">
        <StudyId id={c.id} />
        <span className="text-[14px] font-medium text-ink">{c.exam}</span>
        <span className="text-[13px] text-muted">
          · {c.sex === "F" ? "Mujer" : "Hombre"}, {c.age} años
        </span>
      </div>
      <p className="mt-2 flex flex-wrap gap-2">
        <span className="inline-flex h-7 items-center rounded-pill bg-line-2 px-2.5 text-[12px] font-medium text-ink">{SUBTYPE[c.subtype] ?? c.subtype}</span>
        {c.hard && <span className="inline-flex h-7 items-center rounded-pill bg-crit-bg px-2.5 text-[12px] font-medium text-crit-text">Difícil</span>}
        {c.verdict && (
          <span className="inline-flex h-7 items-center rounded-pill bg-ink px-2.5 text-[12px] font-medium text-white">
            {c.verdict.verdict === "valid" ? "Válido" : "No válido"}
          </span>
        )}
      </p>
      {(
        [
          ["Indicación", c.indication, ind],
          ["Hallazgos", c.findings, body],
          ["Impresión", c.impression, imp],
        ] as const
      ).map(([label, text, marks]) => (
        <div key={label} className="mt-4">
          <SectionLabel as="h3">{label}</SectionLabel>
          <p className="mt-1 text-[16px] leading-relaxed text-ink">{highlight(text, [...marks])}</p>
        </div>
      ))}
      <div className="mt-4 rounded-btn bg-line-2 p-3 text-[14px] leading-relaxed text-ink">
        <span className="font-medium">Error plantado: </span>
        {e ? e.explanation || e.type : "ninguno (el caso debe pasar limpio)"}
      </div>
      <label className="mt-4 block text-[13px] text-muted" htmlFor={`note-${c.id}`}>
        Nota (opcional)
      </label>
      <textarea
        id={`note-${c.id}`}
        value={note}
        maxLength={500}
        rows={2}
        onChange={(ev) => setNote(ev.target.value)}
        className="mt-1 w-full rounded-btn border border-line bg-surface p-3 text-[15px] text-ink"
      />
      {failed && <p role="alert" className="mt-2 text-[14px] text-crit-text">{t["err.other"]}</p>}
      <div className="mt-3 grid grid-cols-2 gap-2">
        <Btn variant="primary" disabled={busy} onClick={() => save("valid")}>
          <Check size={18} aria-hidden /> Válido
        </Btn>
        <Btn variant="light-outline" disabled={busy} onClick={() => save("invalid")}>
          <X size={18} aria-hidden /> No válido
        </Btn>
      </div>
    </article>
  );
}
