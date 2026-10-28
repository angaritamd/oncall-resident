"use client";

import { Activity as ActivityIcon, ArrowUp, ChevronLeft, List, MessageCircle, Mic, Plus } from "lucide-react";
import { useCallback, useEffect, useLayoutEffect, useRef, useState, useSyncExternalStore } from "react";
import { ApiError, api, type Block, type Case, type Lang, type Mode, type NextUp, type Report, type ResidentState, type Worklist } from "@/lib/api";
import { dict } from "@/lib/i18n";
import { CaseCard, EvidenceCard, NextStudyCard, SuggestedReplies } from "./cards";
import { ReportCard } from "./report";
import { StationContext, type StationApi } from "./stationContext";
import { ErrorNote, Monogram, StudyId } from "./ui";
import { useLoad } from "./useLoad";
import { ActivityView, ShiftStart, WorklistView } from "./views";

type Tab = "chat" | "list" | "activity";
type Choice = { caseId: string; state: "ask" | "ai" | "self" };
type Msg =
  | { id: number; role: "user"; text: string }
  | { id: number; role: "resident"; text: string; blocks: Block[]; steps: string[]; mode: Mode; local?: boolean; choice?: Choice }
  | { id: number; role: "error"; kind: ApiError["kind"]; detail: string; retry: string; retryDraft?: string; retryOpen?: string; retryPropose?: string };

const WORKLIST_POLL_MS = 30_000;
const quiet = () => {};

let seq = 0;

/** "1 paso · list_pending" under each answer; backup / basic mode are flagged discreetly, never by name. */
function StepsLine({ steps, mode, t }: { steps: string[]; mode: Mode; t: (typeof dict)["es"] }) {
  return (
    <p className="flex flex-wrap items-center gap-x-1.5 font-mono text-[12px] text-muted">
      <span>{steps.length ? t.steps(steps.length) : t.noSteps}</span>{" "}
      {steps.length > 0 && <span>· {steps.join(" → ")}</span>}{" "}
      {mode === "fallback" && <span className="font-sans">· {t.modeFallback}</span>}
      {mode === "basic" && (
        <span title={t.modeBasicHint} className="ml-1 rounded-pill bg-line-2 px-2 py-0.5 font-sans text-[11px] font-medium text-ink">
          {t.modeBasic}
        </span>
      )}
    </p>
  );
}

/** Programmatic scrolling ignores CSS scroll-behavior, so honour prefers-reduced-motion here. */
function scrollPane(el: HTMLElement, top: number) {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  el.scrollTo({ top, behavior: reduce ? "auto" : "smooth" });
}

/** "¿Lo leemos con IA?" — the resident never starts a reading on its own. */
function ReadChoice({ choice, t, onChoose }: { choice: Choice; t: (typeof dict)["es"]; onChoose: (s: "ai" | "self") => void }) {
  if (choice.state !== "ask") return null;
  return (
    <section aria-label={t.askAi} data-testid="read-choice" className="rounded-card bg-surface p-5">
      <p className="text-[17px] font-semibold">{t.askAi}</p>
      <p className="mt-1 text-[14px] leading-relaxed text-muted">{t.askAiHint}</p>
      <div className="mt-4 grid grid-cols-2 gap-2.5">
        <button type="button" onClick={() => onChoose("ai")} className="h-[54px] rounded-btn bg-blue text-[16px] font-semibold text-white">
          {t.yesAi}
        </button>
        <button type="button" onClick={() => onChoose("self")} className="h-[54px] rounded-btn border border-line bg-surface text-[16px] font-medium text-ink">
          {t.selfRead}
        </button>
      </div>
    </section>
  );
}

function subscribeOnline(cb: () => void) {
  window.addEventListener("online", cb);
  window.addEventListener("offline", cb);
  return () => {
    window.removeEventListener("online", cb);
    window.removeEventListener("offline", cb);
  };
}

export default function ResidentApp() {
  const [lang, setLang] = useState<Lang>("es");
  const t = dict[lang];
  const [tab, setTab] = useState<Tab>("chat");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [draft, setDraft] = useState("");
  const [busyCount, setBusyCount] = useState(0);
  const online = useSyncExternalStore(subscribeOnline, () => navigator.onLine, () => true);
  const [pacsDown, setPacsDown] = useState(false);
  const [resident, setResident] = useState<ResidentState>("ready");
  const [stationLinked, setStationLinked] = useState<boolean | null>(null);
  // the latest opened case and the anchor of the message that rendered it (a case can be opened more than once)
  const [activeCase, setActiveCase] = useState<(Case & { anchor: string }) | null>(null);
  const scroller = useRef<HTMLElement>(null);
  // the chat sends the case open on screen so "el nódulo mide 12 mm" applies to the right draft
  const activeCaseRef = useRef<string | null>(null);

  const onBusy = useCallback((b: boolean) => setBusyCount((c) => Math.max(0, c + (b ? 1 : -1))), []);

  // one worklist for the start screen and the Lista tab, refreshed quietly in the background
  const wlFetch = useCallback(() => api.worklist(lang), [lang]);
  const wl = useLoad<Worklist>(wlFetch, quiet);
  const wlData = useRef<Worklist | null>(null);
  useEffect(() => {
    wlData.current = wl.data;
  }, [wl.data]);
  const reloadWl = wl.load;
  useEffect(() => {
    const id = setInterval(() => {
      if (document.visibilityState === "visible") reloadWl();
    }, WORKLIST_POLL_MS);
    return () => clearInterval(id);
  }, [reloadWl]);
  // while a case is open the list is frozen; newer studies show as "N nuevos" until merged
  const [frozen, setFrozen] = useState<Worklist | null>(null);
  const shown = frozen ?? wl.data;
  const newCount = frozen && wl.data ? wl.data.items.filter((i) => !frozen.items.some((f) => f.case_id === i.case_id)).length : 0;
  const [nextUp, setNextUp] = useState<NextUp | null>(null);
  const chatScroll = useRef(0);
  const seenMsgs = useRef(0);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("lang");
      // restoring a per-device preference after hydration; server always renders "es"
      // eslint-disable-next-line react-hooks/set-state-in-effect
      if (saved === "en" || saved === "es") setLang(saved);
    } catch {}
    api.health().then((h) => setPacsDown(h.pacs !== "ok")).catch(() => setPacsDown(true));
    api.stationConfig().then((c) => setStationLinked(c.linked)).catch(() => setStationLinked(null));
  }, []);

  useEffect(() => {
    // opening the app wakes the scale-to-zero resident; poll while it loads
    let stop = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      try {
        const { state } = await api.resident();
        if (stop) return;
        setResident(state);
        if (state === "waking") timer = setTimeout(poll, 5000);
        else if (state === "unavailable") timer = setTimeout(poll, 60000);
      } catch {
        if (!stop) timer = setTimeout(poll, 15000);
      }
    };
    poll();
    return () => {
      stop = true;
      clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      localStorage.setItem("lang", lang);
    } catch {}
  }, [lang]);

  useLayoutEffect(() => {
    // switching tabs restores where the chat was; it never jumps to the bottom on its own
    const el = scroller.current;
    if (el) el.scrollTop = tab === "chat" ? chatScroll.current : 0;
  }, [tab]);

  const switchTab = useCallback(
    (next: Tab) => {
      if (tab === "chat" && scroller.current) chatScroll.current = scroller.current.scrollTop;
      setTab(next);
    },
    [tab],
  );

  useEffect(() => {
    // only a new message moves the chat (a card updating in place does not)
    if (tab !== "chat" || msgs.length === seenMsgs.current) return;
    seenMsgs.current = msgs.length;
    // a freshly opened case is read from its top; anything else follows the conversation
    const last = msgs[msgs.length - 1];
    const opened = last.role === "resident" && last.blocks.some((b) => b.type === "case");
    const target = opened ? document.getElementById(`case-msg-${last.id}`) : null;
    const el = scroller.current;
    if (!el) return;
    // scroll only the conversation pane; scrollIntoView would also move the page and hide the header
    const top = target ? target.getBoundingClientRect().top - el.getBoundingClientRect().top + el.scrollTop - 12 : el.scrollHeight;
    scrollPane(el, top);
  }, [msgs, tab]);

  const send = useCallback(
    async (text: string, opts: { echo?: boolean } = {}) => {
      const clean = text.trim();
      if (!clean) return;
      setTab("chat");
      if (opts.echo !== false) setMsgs((m) => [...m, { id: ++seq, role: "user", text: clean }]);
      onBusy(true);
      try {
        const r = await api.chat(clean, lang, activeCaseRef.current);
        setPacsDown(false);
        const id = ++seq;
        setMsgs((m) => [...m, { id, role: "resident", text: r.text, blocks: r.blocks, steps: r.steps, mode: r.mode }]);
        if (r.mode === "agent") setResident("ready");
        const opened = r.blocks.find((b) => b.type === "case");
        if (opened?.type === "case") {
          setFrozen((f) => f ?? wlData.current);
          setNextUp(null);
          setActiveCase({ ...opened.case, anchor: `case-msg-${id}` });
          if (!r.blocks.some((b) => b.type === "report")) {
            // no draft shown yet: show it if there is one, otherwise ask "¿Lo leemos con IA?"
            api.report(opened.case.case_id).then(
              (report) => setMsgs((m) => [...m, { id: ++seq, role: "resident", text: "", blocks: [{ type: "report", report }], steps: [], mode: "agent", local: true }]),
              (e) => {
                if (e instanceof ApiError && e.kind === "notfound" && opened.case.position !== 0)
                  setMsgs((m) => m.map((x) => (x.id === id && x.role === "resident" ? { ...x, choice: { caseId: opened.case.case_id, state: "ask" } } : x)));
              },
            );
          }
        }
      } catch (e) {
        const err = e instanceof ApiError ? e : new ApiError("x", "other");
        if (err.kind === "pacs") setPacsDown(true);
        setMsgs((m) => [...m, { id: ++seq, role: "error", kind: err.kind, detail: err.message, retry: clean }]);
      } finally {
        onBusy(false);
      }
    },
    [lang, onBusy],
  );

  /** Opening a case is a direct read (no model): the case card, its draft if any, and otherwise the question
   * "¿Lo leemos con IA?". Nothing starts on its own. */
  const openCase = useCallback(
    async (caseId: string) => {
      if (tab === "chat" && scroller.current) chatScroll.current = scroller.current.scrollTop;
      setTab("chat");
      setNextUp(null);
      onBusy(true);
      try {
        const c = await api.case(caseId, lang);
        const report = await api.report(c.case_id).catch((e) => {
          if (e instanceof ApiError && e.kind === "notfound") return null;
          throw e;
        });
        const id = ++seq;
        const blocks: Block[] = report ? [{ type: "case", case: c }, { type: "report", report }] : [{ type: "case", case: c }];
        const signed = c.position === 0;
        setMsgs((m) => [...m, { id, role: "resident", text: "", blocks, steps: [], mode: "agent", local: true, choice: report || signed ? undefined : { caseId: c.case_id, state: "ask" } }]);
        setFrozen((f) => f ?? wlData.current);
        setActiveCase({ ...c, anchor: `case-msg-${id}` });
      } catch (e) {
        const err = e instanceof ApiError ? e : new ApiError("x", "other");
        if (err.kind === "pacs") setPacsDown(true);
        setMsgs((m) => [...m, { id: ++seq, role: "error", kind: err.kind, detail: err.message, retry: "", retryOpen: caseId }]);
      } finally {
        onBusy(false);
      }
    },
    [lang, onBusy, tab],
  );

  const choose = useCallback(
    async (msgId: number, caseId: string, state: "ai" | "self") => {
      setMsgs((m) => m.map((x) => (x.id === msgId && x.role === "resident" && x.choice ? { ...x, choice: { ...x.choice, state } } : x)));
      if (state === "self") {
        setMsgs((m) => [...m, { id: ++seq, role: "resident", text: t.selfReadText(caseId), blocks: [], steps: [], mode: "agent", local: true }]);
        return;
      }
      onBusy(true);
      try {
        const report: Report = await api.propose(caseId, lang);
        setMsgs((m) => [...m, { id: ++seq, role: "resident", text: "", blocks: [{ type: "report", report }], steps: [], mode: "agent", local: true }]);
      } catch (e) {
        const err = e instanceof ApiError ? e : new ApiError("x", "other");
        setMsgs((m) => [...m, { id: ++seq, role: "error", kind: err.kind, detail: err.message, retry: "", retryPropose: caseId }]);
      } finally {
        onBusy(false);
      }
    },
    [lang, onBusy, t],
  );

  const leaveCase = useCallback(() => {
    // back to the list: the frozen snapshot is dropped and newer studies merge in rule order
    setActiveCase(null);
    setFrozen(null);
    reloadWl();
    switchTab("list");
  }, [reloadWl, switchTab]);

  const onSigned = useCallback(
    (next: NextUp) => {
      leaveCase();
      setNextUp(next);
    },
    [leaveCase],
  );

  useEffect(() => {
    activeCaseRef.current = activeCase?.case_id ?? null;
  }, [activeCase]);

  // opening a case on the phone opens it on the linked station (only its UID travels)
  const lastPushed = useRef<string | null>(null);
  useEffect(() => {
    const id = activeCase?.case_id;
    if (!id || stationLinked !== true || lastPushed.current === id) return;
    lastPushed.current = id;
    api.stationOpen(id).catch(() => {});
  }, [activeCase, stationLinked]);

  const showDraft = useCallback(
    async (id: string) => {
      onBusy(true);
      try {
        const report = await api.report(id);
        setMsgs((m) => [...m, { id: ++seq, role: "resident", text: "", blocks: [{ type: "report", report }], steps: [], mode: "agent", local: true }]);
      } catch (e) {
        const err = e instanceof ApiError ? e : new ApiError("x", "other");
        setMsgs((m) => [...m, err.kind === "notfound"
          ? { id: ++seq, role: "resident", text: t.noDraft(id), blocks: [], steps: [], mode: "agent", local: true }
          : { id: ++seq, role: "error", kind: err.kind, detail: err.message, retry: "", retryDraft: id }]);
      } finally {
        onBusy(false);
      }
    },
    [onBusy, t],
  );

  // only the newest report card of each case stays interactive
  const latestReportMsg: Record<string, number> = {};
  for (const m of msgs) {
    if (m.role === "resident") for (const b of m.blocks) if (b.type === "report") latestReportMsg[b.report.case_id] = m.id;
  }

  const errText = (e: unknown) =>
    e instanceof ApiError && (e.kind === "conflict" || e.kind === "pacs") ? e.message : t[`err.${e instanceof ApiError ? e.kind : "other"}`];
  const station: StationApi = {
    linked: stationLinked,
    refresh: () => {
      api.stationConfig().then((c) => setStationLinked(c.linked)).catch(() => setStationLinked(null));
    },
    open: async (caseId) => {
      try {
        await api.stationOpen(caseId);
        return { ok: true };
      } catch (e) {
        // only the core saying "no station linked" (409) changes the linked state
        if (e instanceof ApiError && e.kind === "conflict") setStationLinked(false);
        return { ok: false, message: errText(e) };
      }
    },
    link: async (code) => {
      try {
        await api.stationLink(code);
        setStationLinked(true);
        return null;
      } catch (e) {
        return errText(e);
      }
    },
    unlink: async () => {
      try {
        await api.stationUnlink();
        setStationLinked(false);
        return null;
      } catch (e) {
        return errText(e); // still linked on the core: keep showing it
      }
    },
  };

  const waking = resident === "waking";
  // data-source problems (offline, PACS down) always win over the resident's own state
  const status = !online
    ? t["status.offline"]
    : pacsDown
      ? t["status.pacsDown"]
      : waking
        ? t["status.waking"]
        : resident === "unavailable"
          ? t["status.unavailable"]
          : busyCount > 0
            ? t["status.querying"]
            : t["status.idle"];
  const dot = !online || pacsDown || resident === "unavailable" ? "bg-urg" : busyCount > 0 || waking ? "bg-blue animate-pulse" : "bg-neutral";

  const tabs = [
    { id: "chat" as const, label: t["tab.chat"], Icon: MessageCircle },
    { id: "list" as const, label: t["tab.list"], Icon: List },
    { id: "activity" as const, label: t["tab.activity"], Icon: ActivityIcon },
  ];

  return (
    <StationContext.Provider value={station}>
    <div className="flex h-dvh flex-col bg-ground">
      <header className="shrink-0 pt-[env(safe-area-inset-top)]">
        <p className="sr-only" role="status" aria-live="polite">
          {status}
        </p>
        {activeCase && tab === "chat" ? (
          <div className="mx-auto flex w-full max-w-2xl items-center gap-3 px-4 py-3">
            <button
              type="button"
              onClick={leaveCase}
              aria-label={t.back}
              className="flex size-12 shrink-0 items-center justify-center rounded-full border border-line bg-surface text-ink"
            >
              <ChevronLeft aria-hidden size={20} strokeWidth={2} />
            </button>
            <button
              type="button"
              onClick={() => {
                const el = scroller.current;
                const target = document.getElementById(activeCase.anchor);
                if (el && target) scrollPane(el, target.getBoundingClientRect().top - el.getBoundingClientRect().top + el.scrollTop - 12);
              }}
              aria-label={`${t.activeCase}: ${activeCase.case_id}`}
              className="flex min-h-12 min-w-0 flex-1 flex-col items-center justify-center text-center"
            >
              <StudyId id={activeCase.case_id} />
              <span className="max-w-full truncate text-[16px] font-semibold leading-tight">{activeCase.exam ?? activeCase.modalities.join(" / ")}</span>
            </button>
            {activeCase.critical ? (
              <span className="inline-flex h-11 shrink-0 items-center gap-2 rounded-pill bg-crit-bg px-4 text-[14px] font-medium text-crit-text">
                <span aria-hidden className="size-2 rounded-full bg-crit" />
                {t.criticalOne}
              </span>
            ) : (
              <span aria-hidden className="w-12 shrink-0" />
            )}
          </div>
        ) : (
          <div className="mx-auto flex w-full max-w-2xl items-center gap-3 px-4 py-3">
            <Monogram size={44} />
            <div className="min-w-0 flex-1">
              <h1 className="text-[17px] font-semibold leading-6 tracking-[-0.01em]">{t.resident}</h1>
              <p aria-hidden className="flex items-center gap-1.5 truncate text-[14px] leading-5 text-muted">
                {t.department} · <span className={`inline-block size-1.5 shrink-0 rounded-full ${dot}`} /> <span className="truncate">{status}</span>
              </p>
            </div>
            <button
              type="button"
              onClick={() => setLang(lang === "es" ? "en" : "es")}
              aria-label={t.language}
              className="flex size-12 shrink-0 items-center justify-center rounded-full border border-line bg-surface text-[13px] font-semibold text-ink"
            >
              {t.langShort}
            </button>
          </div>
        )}
      </header>

      <main ref={scroller} className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
        <div className="mx-auto w-full max-w-2xl px-4 pb-6">
          {tab === "list" ? (
            <WorklistView
              lang={lang}
              t={t}
              wl={wl}
              shown={shown}
              newCount={newCount}
              onMerge={() => setFrozen(wl.data)}
              reading={activeCase?.case_id ?? null}
              next={nextUp}
              onOpen={openCase}
            />
          ) : tab === "activity" ? (
            <ActivityView lang={lang} t={t} onBusy={onBusy} />
          ) : (
            <div className="flex flex-col gap-4" aria-live="polite">
              <ShiftStart wl={wl} t={t} onOpen={openCase} onPending={() => switchTab("list")} />
              {msgs.map((m) =>
                m.role === "user" ? (
                  <div key={m.id} className="flex justify-end">
                    <p className="max-w-[85%] rounded-[20px_20px_6px_20px] bg-blue px-4 py-2.5 text-[15px] leading-6 text-white">
                      <span className="sr-only">{t.you}: </span>
                      {m.text}
                    </p>
                  </div>
                ) : m.role === "resident" ? (
                  <div key={m.id} className="flex flex-col gap-3">
                    {m.blocks.map((b, i) => {
                      if (b.type === "case") return <CaseCard key={i} c={b.case} t={t} anchorId={`case-msg-${m.id}`} onDraft={showDraft} />;
                      if (b.type === "report")
                        return (
                          <ReportCard
                            key={`${b.report.case_id}-${b.report.version}-${i}`}
                            initial={b.report}
                            diff={b.diff}
                            t={t}
                            lang={lang}
                            stale={latestReportMsg[b.report.case_id] !== m.id}
                            onSigned={onSigned}
                            onUpdate={(report, diff) =>
                              setMsgs((all) =>
                                all.map((x) =>
                                  x.id === m.id && x.role === "resident"
                                    ? { ...x, blocks: x.blocks.map((y) => (y.type === "report" && y.report.case_id === report.case_id ? { ...y, report, diff } : y)) }
                                    : x,
                                ),
                              )
                            }
                          />
                        );
                      return null;
                    })}
                    {m.text && <p className="text-[16px] leading-relaxed">{m.text}</p>}
                    {m.choice && <ReadChoice choice={m.choice} t={t} onChoose={(s) => choose(m.id, m.choice!.caseId, s)} />}
                    {!m.local && <StepsLine steps={m.steps} mode={m.mode} t={t} />}
                    {m.blocks.map((b, i) => {
                      if (b.type === "next_study") {
                        const list = m.blocks.find((x) => x.type === "study_list");
                        return <NextStudyCard key={i} item={b.item} total={b.total} list={list?.type === "study_list" ? list.items : undefined} t={t} onOpen={openCase} />;
                      }
                      if (b.type === "evidence") return <EvidenceCard key={i} item={b.item} t={t} onOpen={openCase} />;
                      if (b.type === "case" && !m.choice)
                        return (
                          <SuggestedReplies
                            key={i}
                            items={[
                              { label: t.whyFirst, onClick: () => send(t.whyText(b.case.case_id)) },
                              { label: t["prompt.pending"], onClick: () => send(t["prompt.pendingText"]), primary: true },
                            ]}
                          />
                        );
                      return null;
                    })}
                  </div>
                ) : (
                  <ErrorNote
                    key={m.id}
                    text={m.kind === "pacs" && m.detail ? m.detail : t[`err.${m.kind}`]}
                    retryLabel={t.retry}
                    onRetry={() => {
                      setMsgs((all) => all.filter((x) => x.id !== m.id));
                      // a failed draft load retries the load itself, not a chat message
                      if (m.retryDraft) showDraft(m.retryDraft);
                      else if (m.retryOpen) openCase(m.retryOpen);
                      else if (m.retryPropose) choose(-1, m.retryPropose, "ai");
                      else send(m.retry, { echo: false });
                    }}
                  />
                ),
              )}
              {busyCount > 0 && msgs.length > 0 && (
                <p className="text-[14px] text-muted" role="status">
                  {t["status.querying"]}
                </p>
              )}
            </div>
          )}
        </div>
      </main>

      <footer className="shrink-0 bg-ground pb-[max(env(safe-area-inset-bottom),8px)]">
        <form
          className="mx-auto flex w-full max-w-2xl items-center gap-2 px-4 pt-2"
          onSubmit={(e) => {
            e.preventDefault();
            send(draft);
            setDraft("");
          }}
        >
          <button
            type="button"
            disabled
            aria-label={t.attach}
            title={t.attach}
            className="flex size-[46px] shrink-0 cursor-not-allowed items-center justify-center rounded-pill border border-line text-muted"
          >
            <Plus aria-hidden size={20} strokeWidth={1.8} />
          </button>
          <div className="flex h-[46px] min-w-0 flex-1 items-center rounded-pill border border-line bg-surface pl-4 focus-within:border-blue">
            <label htmlFor="composer" className="sr-only">
              {t.composerLabel}
            </label>
            <input
              id="composer"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={t.composer}
              autoComplete="off"
              enterKeyHint="send"
              maxLength={500}
              className="h-full min-w-0 flex-1 bg-transparent text-[16px] text-ink placeholder:text-muted focus:outline-none"
            />
            <button type="button" disabled aria-label={t.mic} title={t.mic} className="flex size-11 shrink-0 cursor-not-allowed items-center justify-center text-muted">
              <Mic aria-hidden size={18} strokeWidth={1.8} />
            </button>
          </div>
          <button
            type="submit"
            disabled={!draft.trim()}
            aria-label={t.send}
            className="flex size-[46px] shrink-0 items-center justify-center rounded-pill bg-blue text-white disabled:opacity-40"
          >
            <ArrowUp aria-hidden size={20} strokeWidth={2} />
          </button>
        </form>
        <nav aria-label={t.tabs} className="mx-auto flex w-full max-w-2xl px-2 pt-1.5">
          {tabs.map((x) => {
            const active = tab === x.id;
            return (
              <button
                key={x.id}
                type="button"
                aria-current={active ? "page" : undefined}
                onClick={() => switchTab(x.id)}
                className={`flex min-h-14 flex-1 flex-col items-center justify-center gap-0.5 text-[12.5px] ${active ? "font-semibold text-ink" : "font-medium text-muted hover:text-ink"}`}
              >
                <x.Icon aria-hidden size={22} strokeWidth={1.8} />
                {x.label}
              </button>
            );
          })}
        </nav>
      </footer>
    </div>
    </StationContext.Provider>
  );
}
