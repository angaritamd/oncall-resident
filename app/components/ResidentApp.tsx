"use client";

import { Activity as ActivityIcon, ArrowUp, ChevronLeft, List, MessageCircle, Mic, Plus } from "lucide-react";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { ApiError, api, type Block, type Case, type Lang, type Mode, type ResidentState } from "@/lib/api";
import { dict } from "@/lib/i18n";
import { CaseCard, EvidenceCard, NextStudyCard, SuggestedReplies } from "./cards";
import { ErrorNote, Monogram, StudyId } from "./ui";
import { ActivityView, PendingView, ShiftStart } from "./views";

type Tab = "chat" | "activity" | "pending";
type Msg =
  | { id: number; role: "user"; text: string }
  | { id: number; role: "resident"; text: string; blocks: Block[]; steps: string[]; mode: Mode }
  | { id: number; role: "error"; kind: ApiError["kind"]; detail: string; retry: string };

let seq = 0;

/** "1 paso · list_pending" under each answer; backup / basic mode are flagged discreetly, never by name. */
function StepsLine({ steps, mode, t }: { steps: string[]; mode: Mode; t: (typeof dict)["es"] }) {
  return (
    <p className="flex flex-wrap items-center gap-x-1.5 font-mono text-[12px] text-muted">
      <span>{steps.length ? t.steps(steps.length) : t.noSteps}</span>
      {steps.length > 0 && <span>· {steps.join(" → ")}</span>}
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
  // the latest opened case and the anchor of the message that rendered it (a case can be opened more than once)
  const [activeCase, setActiveCase] = useState<(Case & { anchor: string }) | null>(null);
  const scroller = useRef<HTMLElement>(null);

  const onBusy = useCallback((b: boolean) => setBusyCount((c) => Math.max(0, c + (b ? 1 : -1))), []);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("lang");
      // restoring a per-device preference after hydration; server always renders "es"
      // eslint-disable-next-line react-hooks/set-state-in-effect
      if (saved === "en" || saved === "es") setLang(saved);
    } catch {}
    api.health().then((h) => setPacsDown(h.pacs !== "ok")).catch(() => setPacsDown(true));
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

  useEffect(() => {
    if (tab !== "chat" || !msgs.length) return;
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
        const r = await api.chat(clean, lang);
        setPacsDown(false);
        const id = ++seq;
        setMsgs((m) => [...m, { id, role: "resident", text: r.text, blocks: r.blocks, steps: r.steps, mode: r.mode }]);
        if (r.mode === "agent") setResident("ready");
        const opened = r.blocks.find((b) => b.type === "case");
        if (opened?.type === "case") setActiveCase({ ...opened.case, anchor: `case-msg-${id}` });
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

  const openCase = useCallback((id: string) => send(t.openText(id)), [send, t]);

  const waking = resident === "waking";
  const status = !online
    ? t["status.offline"]
    : waking
      ? t["status.waking"]
      : busyCount > 0
        ? t["status.querying"]
        : pacsDown
          ? t["status.pacsDown"]
          : t["status.idle"];
  const dot = !online || pacsDown ? "bg-urg" : busyCount > 0 || waking ? "bg-blue animate-pulse" : "bg-neutral";

  const tabs = [
    { id: "chat" as const, label: t["tab.chat"], Icon: MessageCircle },
    { id: "activity" as const, label: t["tab.activity"], Icon: ActivityIcon },
    { id: "pending" as const, label: t["tab.pending"], Icon: List },
  ];

  return (
    <div className="flex h-dvh flex-col bg-ground">
      <header className="shrink-0 pt-[env(safe-area-inset-top)]">
        <p className="sr-only" role="status" aria-live="polite">
          {status}
        </p>
        {activeCase && tab === "chat" ? (
          <div className="mx-auto flex w-full max-w-2xl items-center gap-3 px-4 py-3">
            <button
              type="button"
              onClick={() => {
                setActiveCase(null);
                if (scroller.current) scrollPane(scroller.current, 0);
              }}
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
          {tab === "pending" ? (
            <PendingView lang={lang} t={t} onOpen={openCase} onBusy={onBusy} />
          ) : tab === "activity" ? (
            <ActivityView lang={lang} t={t} onBusy={onBusy} />
          ) : (
            <div className="flex flex-col gap-4" aria-live="polite">
              <ShiftStart key={lang} lang={lang} t={t} onOpen={openCase} onPending={() => setTab("pending")} onBusy={onBusy} />
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
                      if (b.type === "case") return <CaseCard key={i} c={b.case} t={t} anchorId={`case-msg-${m.id}`} />;
                      return null;
                    })}
                    <p className="text-[16px] leading-relaxed">{m.text}</p>
                    <StepsLine steps={m.steps} mode={m.mode} t={t} />
                    {m.blocks.map((b, i) => {
                      if (b.type === "next_study") {
                        const list = m.blocks.find((x) => x.type === "study_list");
                        return <NextStudyCard key={i} item={b.item} total={b.total} list={list?.type === "study_list" ? list.items : undefined} t={t} onOpen={openCase} />;
                      }
                      if (b.type === "evidence") return <EvidenceCard key={i} item={b.item} t={t} onOpen={openCase} />;
                      if (b.type === "case")
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
                      send(m.retry, { echo: false });
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
                onClick={() => setTab(x.id)}
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
  );
}
