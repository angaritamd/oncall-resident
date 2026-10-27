"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { ApiError, api, type Block, type Lang } from "@/lib/api";
import { dict } from "@/lib/i18n";
import { Blocks } from "./blocks";
import { CaseView } from "./CaseView";
import { ActivityView, PendingView } from "./Lists";
import { Button, ErrorNote, Monogram } from "./ui";

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
  const [caseOpen, setCaseOpen] = useState<string | null>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);

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
    if (tab === "chat" && !caseOpen) scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [msgs, tab, caseOpen]);

  const send = useCallback(
    async (text: string, opts: { echo?: boolean } = {}) => {
      const clean = text.trim();
      if (!clean) return;
      if (opts.echo !== false) setMsgs((m) => [...m, { id: ++seq, role: "user", text: clean }]);
      onBusy(true);
      try {
        const r = await api.chat(clean, lang);
        setPacsDown(false);
        setMsgs((m) => [...m, { id: ++seq, role: "resident", text: r.text, blocks: r.blocks }]);
        const opened = r.blocks.find((b) => b.type === "case");
        if (opened?.type === "case") {
          setActiveCase(opened.case.case_id);
          setCaseOpen(opened.case.case_id);
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

  const openCase = useCallback(
    (id: string) => {
      setTab("chat");
      send(`${lang === "es" ? "Abrir" : "Open"} ${id}`);
    },
    [lang, send],
  );

  const back = () => {
    setCaseOpen(null);
    requestAnimationFrame(() => input.current?.focus());
  };

  const status = !online ? t["status.offline"] : busyCount > 0 ? t["status.querying"] : pacsDown ? t["status.pacsDown"] : t["status.idle"];
  const statusTone = !online || pacsDown ? "bg-review" : busyCount > 0 ? "bg-action animate-pulse" : "bg-muted";
  const suggestions = [t["suggest.pending"], t["suggest.why"], t["suggest.open"]];

  const tabs: { id: Tab; label: string }[] = [
    { id: "chat", label: t["tab.chat"] },
    { id: "activity", label: t["tab.activity"] },
    { id: "pending", label: t["tab.pending"] },
  ];

  return (
    <div className="flex h-dvh flex-col bg-bg">
      <header className="shrink-0 border-b border-line bg-bg pt-[env(safe-area-inset-top)]">
        <div className="mx-auto flex w-full max-w-3xl items-center gap-3 px-4 py-2.5">
          <Monogram />
          <div className="min-w-0 flex-1">
            <h1 className="text-[17px] font-semibold leading-6">{t.resident}</h1>
            <p className="flex items-center gap-1.5 text-[13px] leading-5 text-muted" role="status" aria-live="polite">
              <span aria-hidden className={`inline-block size-2 rounded-full ${statusTone}`} />
              <span className="truncate">{status}</span>
            </p>
          </div>
          {activeCase && (
            <span className="inline-flex max-w-[45%] items-center rounded-full border border-line bg-surface pl-3 text-[13px]">
              <button type="button" onClick={() => setCaseOpen(activeCase)} className="truncate py-1.5 font-mono" aria-label={`${t.activeCase}: ${activeCase}`}>
                {activeCase}
              </button>
              <button type="button" onClick={() => setActiveCase(null)} aria-label={t.clearCase} className="flex size-9 shrink-0 items-center justify-center rounded-full text-muted hover:text-fg">
                <span aria-hidden>×</span>
              </button>
            </span>
          )}
          <button
            type="button"
            onClick={() => setLang(lang === "es" ? "en" : "es")}
            aria-label={t.language}
            className="flex min-h-11 min-w-11 items-center justify-center rounded-lg border border-line text-[13px] font-medium text-muted hover:text-fg"
          >
            {lang === "es" ? "EN" : "ES"}
          </button>
        </div>
      </header>

      <main ref={scroller} className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
        {caseOpen ? (
          <CaseView key={caseOpen + lang} id={caseOpen} lang={lang} t={t} onBack={back} onBusy={onBusy} />
        ) : tab === "pending" ? (
          <PendingView lang={lang} t={t} onOpen={openCase} onBusy={onBusy} />
        ) : tab === "activity" ? (
          <ActivityView lang={lang} t={t} onBusy={onBusy} />
        ) : (
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-3 px-4 py-4" aria-live="polite">
            <div className="flex items-start gap-2.5">
              <Monogram size={28} />
              <p className="max-w-[85%] pt-0.5 text-[15px] leading-6">{t.welcome}</p>
            </div>
            {msgs.length === 0 && (
              <div className="flex flex-wrap gap-2 pl-9">
                {suggestions.map((s) => (
                  <Button key={s} onClick={() => send(s)}>
                    {s}
                  </Button>
                ))}
              </div>
            )}
            {msgs.map((m) =>
              m.role === "user" ? (
                <div key={m.id} className="flex justify-end">
                  <p className="max-w-[85%] rounded-2xl rounded-br-md border border-action/30 bg-action/15 px-3.5 py-2 text-[15px] leading-6">
                    <span className="sr-only">{t.you}: </span>
                    {m.text}
                  </p>
                </div>
              ) : m.role === "resident" ? (
                <div key={m.id} className="flex items-start gap-2.5">
                  <Monogram size={28} />
                  <div className="flex min-w-0 flex-1 flex-col gap-2">
                    <p className="pt-0.5 text-[15px] leading-6">{m.text}</p>
                    {m.blocks.length > 0 && <Blocks blocks={m.blocks} t={t} onOpen={openCase} onAsk={send} />}
                  </div>
                </div>
              ) : (
                <div key={m.id} className="pl-9">
                  <ErrorNote
                    text={m.kind === "pacs" && m.detail ? m.detail : t[`err.${m.kind}`]}
                    retryLabel={t.retry}
                    onRetry={() => {
                      setMsgs((all) => all.filter((x) => x.id !== m.id));
                      send(m.retry, { echo: false });
                    }}
                  />
                </div>
              ),
            )}
            {busyCount > 0 && (
              <p className="pl-9 text-[14px] text-muted" role="status">
                {t["status.querying"]}
              </p>
            )}
          </div>
        )}
      </main>

      <footer className="shrink-0 border-t border-line bg-bg pb-[env(safe-area-inset-bottom)]">
        {tab === "chat" && !caseOpen && (
          <form
            className="mx-auto flex w-full max-w-3xl items-center gap-2 px-3 pt-2.5"
            onSubmit={(e) => {
              e.preventDefault();
              send(draft);
              setDraft("");
            }}
          >
            <label htmlFor="composer" className="sr-only">
              {t.composerLabel}
            </label>
            <input
              id="composer"
              ref={input}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={t.composer}
              autoComplete="off"
              maxLength={500}
              className="min-h-11 min-w-0 flex-1 rounded-xl border border-line bg-surface px-3.5 text-[16px] text-fg placeholder:text-muted focus:border-action focus:outline-none"
            />
            <button
              type="button"
              disabled
              aria-label={t.mic}
              title={t.mic}
              className="flex size-11 shrink-0 cursor-not-allowed items-center justify-center rounded-xl border border-dashed border-line text-muted/60"
            >
              <svg aria-hidden width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <rect x="9" y="3" width="6" height="11" rx="3" />
                <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
                <path d="M4 4l16 16" />
              </svg>
            </button>
            <button
              type="submit"
              disabled={!draft.trim()}
              aria-label={t.send}
              className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-action text-on-action disabled:opacity-40"
            >
              <svg aria-hidden width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 19V5M5 12l7-7 7 7" />
              </svg>
            </button>
          </form>
        )}
        <nav aria-label="Main" className="mx-auto flex w-full max-w-3xl px-2 pt-1.5">
          {tabs.map((x) => {
            const active = tab === x.id && !caseOpen;
            return (
              <button
                key={x.id}
                type="button"
                aria-current={active ? "page" : undefined}
                onClick={() => {
                  setCaseOpen(null);
                  setTab(x.id);
                }}
                className={`flex min-h-12 flex-1 items-center justify-center rounded-lg text-[14px] font-medium ${active ? "text-fg" : "text-muted hover:text-fg"}`}
              >
                <span className={`border-b-2 pb-0.5 ${active ? "border-action" : "border-transparent"}`}>{x.label}</span>
              </button>
            );
          })}
        </nav>
      </footer>
    </div>
  );
}
