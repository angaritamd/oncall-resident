"use client";

import { ArrowUp, Mic, Plus, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { ApiError, api, type Block, type Lang } from "@/lib/api";
import { dict } from "@/lib/i18n";
import { CaseCard, EvidenceCard, NextStudyCard, SuggestedReplies } from "./cards";
import { ErrorNote, Monogram } from "./ui";
import { ActivityView, PendingView, ShiftStart } from "./views";

type Tab = "chat" | "activity" | "pending";
type Msg =
  | { id: number; role: "user"; text: string }
  | { id: number; role: "resident"; text: string; blocks: Block[] }
  | { id: number; role: "error"; kind: ApiError["kind"]; detail: string; retry: string };

let seq = 0;

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
  const [activeCase, setActiveCase] = useState<string | null>(null);
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
    document.documentElement.lang = lang;
    try {
      localStorage.setItem("lang", lang);
    } catch {}
  }, [lang]);

  useEffect(() => {
    if (tab !== "chat" || !msgs.length) return;
    // a freshly opened case is read from its top; anything else follows the conversation
    const last = msgs[msgs.length - 1];
    const opened = last.role === "resident" ? last.blocks.find((b) => b.type === "case") : undefined;
    const target = opened?.type === "case" ? document.getElementById(`case-${opened.case.case_id}`) : null;
    if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
    else scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
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
        setMsgs((m) => [...m, { id: ++seq, role: "resident", text: r.text, blocks: r.blocks }]);
        const opened = r.blocks.find((b) => b.type === "case");
        if (opened?.type === "case") setActiveCase(opened.case.case_id);
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

  const status = !online ? t["status.offline"] : busyCount > 0 ? t["status.querying"] : pacsDown ? t["status.pacsDown"] : t["status.idle"];
  const dot = !online || pacsDown ? "bg-urg" : busyCount > 0 ? "bg-blue animate-pulse" : "bg-neutral";

  const tabs: { id: Tab; label: string }[] = [
    { id: "chat", label: t["tab.chat"] },
    { id: "activity", label: t["tab.activity"] },
    { id: "pending", label: t["tab.pending"] },
  ];

  return (
    <div className="flex h-dvh flex-col bg-ground">
      <header className="shrink-0 pt-[env(safe-area-inset-top)]">
        <div className="mx-auto flex w-full max-w-2xl items-center gap-3 px-4 py-3">
          <Monogram />
          <div className="min-w-0 flex-1">
            <h1 className="text-[17px] font-semibold leading-6 tracking-[-0.01em]">{t.resident}</h1>
            <p className="flex items-center gap-1.5 text-[12.5px] leading-5 text-muted" role="status" aria-live="polite">
              <span aria-hidden className={`inline-block size-1.5 rounded-full ${dot}`} />
              <span className="truncate">{status}</span>
            </p>
          </div>
          {activeCase && (
            <span className="inline-flex max-w-[44%] items-center rounded-pill bg-surface pl-3">
              <button
                type="button"
                onClick={() => {
                  setTab("chat");
                  requestAnimationFrame(() => document.getElementById(`case-${activeCase}`)?.scrollIntoView({ behavior: "smooth" }));
                }}
                className="min-h-11 truncate font-mono text-[12.5px] font-medium"
                aria-label={`${t.activeCase}: ${activeCase}`}
              >
                {activeCase}
              </button>
              <button type="button" onClick={() => setActiveCase(null)} aria-label={t.clearCase} className="flex size-11 shrink-0 items-center justify-center rounded-pill text-muted hover:text-ink">
                <X aria-hidden size={16} strokeWidth={2} />
              </button>
            </span>
          )}
          <button
            type="button"
            onClick={() => setLang(lang === "es" ? "en" : "es")}
            aria-label={t.language}
            className="flex size-11 shrink-0 items-center justify-center rounded-btn border border-line bg-surface text-[12.5px] font-semibold text-ink"
          >
            {t.langShort}
          </button>
        </div>
      </header>

      <main ref={scroller} className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
        <div className="mx-auto w-full max-w-2xl px-4 pb-6">
          {tab === "pending" ? (
            <PendingView lang={lang} t={t} onOpen={openCase} onBusy={onBusy} />
          ) : tab === "activity" ? (
            <ActivityView lang={lang} t={t} onBusy={onBusy} />
          ) : (
            <div className="flex flex-col gap-4" aria-live="polite">
              <ShiftStart key={lang} lang={lang} t={t} onOpen={openCase} onAsk={send} onBusy={onBusy} />
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
                    <div className="flex items-start gap-2.5">
                      <Monogram size={26} />
                      <p className="min-w-0 flex-1 pt-0.5 text-[15px] leading-6">{m.text}</p>
                    </div>
                    {m.blocks.map((b, i) => {
                      if (b.type === "next_study") {
                        const list = m.blocks.find((x) => x.type === "study_list");
                        return <NextStudyCard key={i} item={b.item} total={b.total} list={list?.type === "study_list" ? list.items : undefined} t={t} onOpen={openCase} onAsk={send} />;
                      }
                      if (b.type === "evidence") return <EvidenceCard key={i} item={b.item} t={t} onOpen={openCase} />;
                      if (b.type === "case")
                        return (
                          <div key={i} className="flex flex-col gap-3">
                            <CaseCard c={b.case} t={t} />
                            <SuggestedReplies
                              items={[
                                { label: t.whyFirst, onClick: () => send(t.whyText(b.case.case_id)) },
                                { label: t["prompt.pending"], onClick: () => send(t["prompt.pendingText"]) },
                              ]}
                            />
                          </div>
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
        {tab === "chat" && (
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
        )}
        <nav aria-label={t.tabs} className="mx-auto flex w-full max-w-2xl px-2 pt-1">
          {tabs.map((x) => {
            const active = tab === x.id;
            return (
              <button
                key={x.id}
                type="button"
                aria-current={active ? "page" : undefined}
                onClick={() => setTab(x.id)}
                className={`flex min-h-12 flex-1 items-center justify-center text-[14px] ${active ? "font-semibold text-ink" : "font-medium text-muted hover:text-ink"}`}
              >
                {x.label}
              </button>
            );
          })}
        </nav>
      </footer>
    </div>
  );
}
