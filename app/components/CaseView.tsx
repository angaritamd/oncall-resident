"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api, type Case, type Lang } from "@/lib/api";
import type { Dict } from "@/lib/i18n";
import { Button, CaseId, ErrorNote, ReasonChip } from "./ui";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 border-t border-line py-3 first:border-t-0 sm:flex-row sm:gap-4">
      <dt className="shrink-0 text-[14px] text-muted sm:w-48">{label}</dt>
      <dd className="min-w-0 text-[15px]">{children}</dd>
    </div>
  );
}

export function CaseView({ id, lang, t, onBack, onBusy }: { id: string; lang: Lang; t: Dict; onBack: () => void; onBusy: (b: boolean) => void }) {
  const [data, setData] = useState<Case | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);

  const load = useCallback(async () => {
    setError(null);
    onBusy(true);
    try {
      setData(await api.case(id, lang));
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError("x", "other"));
    } finally {
      onBusy(false);
    }
  }, [id, lang, onBusy]);

  useEffect(() => {
    // fetch on mount / when inputs change
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  useEffect(() => {
    heading.current?.focus();
  }, []);

  const yn = (v: boolean | null) => (v == null ? t.unknown : v ? t.yes : t.no);

  return (
    <div className="mx-auto w-full max-w-3xl px-4 pb-6 pt-3">
      <Button variant="ghost" onClick={onBack}>
        <span aria-hidden>←</span> {t.back}
      </Button>
      <h2 ref={heading} tabIndex={-1} className="mt-2 flex flex-wrap items-baseline gap-x-2 text-[20px] font-semibold outline-none">
        {data?.exam ?? (data ? data.modalities.join("/") : "")}
        <CaseId id={id} />
      </h2>

      {!data && !error && <p className="mt-4 text-muted" role="status">{t.loading}</p>}
      {error && (
        <div className="mt-4">
          <ErrorNote text={error.kind === "notfound" ? error.message : t[`err.${error.kind}`]} retryLabel={t.retry} onRetry={error.kind === "notfound" ? undefined : load} />
        </div>
      )}

      {data && (
        <>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {data.reasons.map((r) => (
              <ReasonChip key={r.kind + r.source} r={r} />
            ))}
            {data.wait_minutes != null && (
              <span className="text-[14px] text-muted">
                {t.wait} {data.wait_minutes} {t.min}
              </span>
            )}
          </div>

          <dl className="mt-4 rounded-xl border border-line bg-surface px-3.5">
            <Row label={t.indication}>{data.reason ?? <span className="text-muted">{t.noMeta}</span>}</Row>
            <Row label={t.techNote}>
              {data.critical && <span className="mb-1 block font-medium text-critical">{t.techCritical}</span>}
              {data.tech_note ?? <span className="text-muted">{t.noMeta}</span>}
            </Row>
            <Row label={t.priors}>
              <span className="block">
                {t.priorsDeclared}: <strong className="font-medium">{yn(data.priors_declared)}</strong>
              </span>
              <span className="block">
                {t.priorsInPacs}: <strong className="font-medium">{data.priors_in_pacs ?? t.unknown}</strong>
              </span>
            </Row>
          </dl>

          <h3 className="mt-5 text-[13px] font-medium uppercase tracking-wide text-muted">{t.study}</h3>
          <dl className="mt-2 rounded-xl border border-line bg-surface px-3.5">
            <Row label={t.studyDate}>
              {data.study_date ? `${data.study_date.slice(0, 4)}-${data.study_date.slice(4, 6)}-${data.study_date.slice(6, 8)}` : t.unknown}
              <span className="block text-[13px] text-muted">{t.dateShifted}</span>
            </Row>
            <Row label={t.series}>{data.series_count ?? t.unknown}</Row>
            <Row label={t.instances}>{data.instance_count ?? t.unknown}</Row>
            <Row label={t.uid}>
              <span className="break-all font-mono text-[13px] text-muted">{data.study_uid}</span>
            </Row>
            <Row label={t.viewer}>
              <span className="inline-flex items-center rounded-md border border-line px-2 py-0.5 text-[13px] text-muted">{t.notAvailable}</span>
            </Row>
          </dl>

          <p className="mt-4 text-[13px] text-muted">{t.disclaimer}</p>
          <div className="mt-4">
            <Button variant="primary" onClick={onBack}>
              {t.back}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
