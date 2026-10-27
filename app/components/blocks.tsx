"use client";

import { useState } from "react";
import type { Block, Item } from "@/lib/api";
import type { Dict } from "@/lib/i18n";
import { Button, Card, CaseId, ReasonChip } from "./ui";

type Actions = { onOpen: (id: string) => void; onAsk: (text: string) => void };

function Wait({ item, t }: { item: Item; t: Dict }) {
  if (item.wait_minutes == null) return null;
  return (
    <span className="text-[14px] text-muted">
      {t.wait} {item.wait_minutes} {t.min}
    </span>
  );
}

export function StudyRow({ item, t, onOpen }: { item: Item; t: Dict; onOpen: (id: string) => void }) {
  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-2 border-t border-line py-3 first:border-t-0">
      <span className="w-6 shrink-0 text-right font-mono text-[13px] text-muted">{item.position}</span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-2">
          <span className="font-medium">{item.exam ?? item.modalities.join("/")}</span>
          <CaseId id={item.case_id} />
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          {item.reasons.map((r) => (
            <ReasonChip key={r.kind + r.source} r={r} />
          ))}
          <Wait item={item} t={t} />
        </div>
      </div>
      <Button onClick={() => onOpen(item.case_id)} aria-label={`${t.openCase} ${item.case_id}`}>
        {t.openCase}
      </Button>
    </li>
  );
}

function NextStudy({ item, total, list, t, onOpen, onAsk }: { item: Item; total: number; list?: Item[]; t: Dict } & Actions) {
  const [expanded, setExpanded] = useState(false);
  return (
    <Card label={`${t.next} ${item.case_id}`} tone={item.critical ? "critical" : undefined}>
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="text-[13px] font-medium uppercase tracking-wide text-muted">{t.next}</h3>
        <span className="text-[13px] text-muted">
          1 {t.ofTotal} {total}
        </span>
      </div>
      <div className="mt-2 flex flex-wrap items-baseline gap-x-2">
        <span className="text-[17px] font-semibold">{item.exam ?? item.modalities.join("/")}</span>
        <CaseId id={item.case_id} />
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        {item.reasons.map((r) => (
          <ReasonChip key={r.kind + r.source} r={r} />
        ))}
        <Wait item={item} t={t} />
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button variant="primary" onClick={() => onOpen(item.case_id)} aria-label={`${t.openCase} ${item.case_id}`}>
          {t.openCase} {item.case_id}
        </Button>
        <Button onClick={() => onAsk(`${t.whyFirst.replace("?", "")} ${item.case_id}?`)}>{t.whyFirst}</Button>
      </div>
      {list && list.length > 1 && (
        <div className="mt-3 border-t border-line pt-2">
          <Button variant="ghost" aria-expanded={expanded} onClick={() => setExpanded((v) => !v)}>
            {expanded ? t.hideAll : t.showAll(list.length)}
          </Button>
          {expanded && (
            <ol className="mt-1">
              {list.map((i) => (
                <StudyRow key={i.study_uid} item={i} t={t} onOpen={onOpen} />
              ))}
            </ol>
          )}
        </div>
      )}
    </Card>
  );
}

function Evidence({ item, t, onOpen }: { item: Item; t: Dict } & Actions) {
  return (
    <Card label={`${t.evidence} ${item.case_id}`}>
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="text-[13px] font-medium uppercase tracking-wide text-muted">{t.evidence}</h3>
        <CaseId id={item.case_id} />
      </div>
      <ul className="mt-2 flex flex-wrap gap-1.5">
        {item.reasons.map((r) => (
          <li key={r.kind + r.source}>
            <ReasonChip r={r} />
          </li>
        ))}
      </ul>
      <p className="mt-2 text-[14px] text-muted">{t.rule}</p>
      <div className="mt-3">
        <Button variant="primary" onClick={() => onOpen(item.case_id)} aria-label={`${t.openCase} ${item.case_id}`}>
          {t.openCase} {item.case_id}
        </Button>
      </div>
    </Card>
  );
}

export function Blocks({ blocks, t, onOpen, onAsk }: { blocks: Block[]; t: Dict } & Actions) {
  const list = blocks.find((b) => b.type === "study_list");
  return (
    <div className="flex flex-col gap-2">
      {blocks.map((b, i) => {
        if (b.type === "next_study")
          return (
            <NextStudy
              key={i}
              item={b.item}
              total={b.total}
              list={list?.type === "study_list" ? list.items : undefined}
              t={t}
              onOpen={onOpen}
              onAsk={onAsk}
            />
          );
        if (b.type === "evidence") return <Evidence key={i} item={b.item} t={t} onOpen={onOpen} onAsk={onAsk} />;
        if (b.type === "case")
          return (
            <Card key={i} label={b.case.case_id}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-baseline gap-x-2">
                  <span className="font-medium">{b.case.exam ?? b.case.modalities.join("/")}</span>
                  <CaseId id={b.case.case_id} />
                </div>
                <Button onClick={() => onOpen(b.case.case_id)} aria-label={`${t.reopen} ${b.case.case_id}`}>
                  {t.reopen}
                </Button>
              </div>
            </Card>
          );
        return null;
      })}
    </div>
  );
}
