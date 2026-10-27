"use client";

import { Monitor, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { dict } from "@/lib/i18n";
import { ErrorNote, Monogram } from "./ui";

const t = dict.es;

/** Desktop reading station: OHIF in a frame, opened on whatever study the linked phone opens. */
export default function StationView() {
  const [viewer, setViewer] = useState<string | null>(null);
  const [station, setStation] = useState<{ id: string; code: string } | null>(null);
  const [linked, setLinked] = useState(false);
  const [uid, setUid] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lost, setLost] = useState(false);
  const events = useRef<EventSource | null>(null);

  const pair = useCallback(async () => {
    setError(null);
    try {
      const [cfg, p] = await Promise.all([api.stationConfig(), api.stationPair()]);
      setViewer(cfg.viewer_url || "");
      setStation({ id: p.station_id, code: p.code });
      setLinked(false);
      setLost(false);
    } catch (e) {
      setError(t[`err.${e instanceof ApiError ? e.kind : "other"}`]);
    }
  }, []);

  useEffect(() => {
    // pairing on load: the station gets a fresh single-use code
    // eslint-disable-next-line react-hooks/set-state-in-effect
    pair();
  }, [pair]);

  useEffect(() => {
    if (!station) return;
    const es = new EventSource(`/api/station/events?station=${encodeURIComponent(station.id)}`);
    events.current = es;
    es.addEventListener("open", (ev) => {
      try {
        const data = JSON.parse((ev as MessageEvent).data) as { study_uid?: string };
        if (data.study_uid && /^[0-2](\.\d+)+$/.test(data.study_uid)) setUid(data.study_uid);
      } catch {}
    });
    es.onerror = () => {
      // EventSource retries on its own; a closed stream (e.g. the core restarted and forgot the station) is lost
      if (es.readyState === EventSource.CLOSED) setLost(true);
    };
    const poll = setInterval(async () => {
      try {
        const st = await api.stationState(station.id);
        setLinked(st.linked);
        setLost(false);
        if (!st.linked) {
          setUid(null); // unlinked: the study leaves the screen
        } else if (st.last_study_uid && /^[0-2](\.\d+)+$/.test(st.last_study_uid)) {
          // recover a study whose event was missed while the stream was reconnecting
          setUid((u) => u ?? st.last_study_uid);
        }
      } catch (e) {
        if (e instanceof ApiError && e.kind === "notfound") setLost(true);
      }
    }, 3000);
    return () => {
      es.close();
      clearInterval(poll);
    };
  }, [station]);

  const src = viewer && uid ? `${viewer.replace(/\/$/, "")}/viewer?StudyInstanceUIDs=${encodeURIComponent(uid)}` : null;
  return (
    <div className="flex h-dvh flex-col bg-ground">
      <header className="flex flex-wrap items-center gap-4 px-5 py-3">
        <Monogram size={40} />
        <div className="min-w-0 flex-1">
          <h1 className="text-[18px] font-semibold">{t["station.title"]}</h1>
          <p className="text-[13.5px] text-muted">{t["station.subtitle"]}</p>
        </div>
        {station && !linked && (
          <div className="flex items-center gap-4 rounded-card-sm bg-surface px-5 py-3" aria-live="polite">
            <div>
              <p className="label text-muted">{t["station.code"]}</p>
              <p data-testid="station-code" className="font-mono text-[34px] font-medium leading-none tracking-[0.18em]">
                {station.code}
              </p>
            </div>
            <p className="max-w-60 text-[12.5px] text-muted">{t["station.codeHint"]}</p>
          </div>
        )}
        <p role="status" className="flex items-center gap-2 text-[14px] text-muted">
          <span aria-hidden className={`size-2 rounded-full ${linked ? "bg-blue" : "bg-neutral"}`} />
          {linked ? t["station.linked"] : t["station.waiting"]}
          {uid && <span className="font-mono text-[12.5px]">· {t["station.opened"](uid)}</span>}
        </p>
        <button type="button" onClick={pair} className="flex h-11 items-center gap-2 rounded-btn border border-line bg-surface px-3 text-[14px]">
          <RefreshCw aria-hidden size={16} strokeWidth={1.8} /> {t["station.newCode"]}
        </button>
      </header>
      {lost && (
        <div className="px-5">
          <ErrorNote text={t["station.lost"]} retryLabel={t["station.newCode"]} onRetry={pair} />
        </div>
      )}
      {error && (
        <div className="px-5">
          <ErrorNote text={error} retryLabel={t.retry} onRetry={pair} />
        </div>
      )}
      <main className="min-h-0 flex-1 px-5 pb-5">
        {viewer === "" ? (
          <p className="rounded-card bg-surface p-5 text-muted">{t["station.noViewer"]}</p>
        ) : src ? (
          <iframe
            key={src}
            title={`OHIF · ${uid}`}
            src={src}
            className="size-full rounded-card bg-ink"
            referrerPolicy="no-referrer"
            allow="fullscreen"
          />
        ) : (
          <div className="flex size-full flex-col items-center justify-center gap-3 rounded-card bg-ink text-ink-text">
            <Monitor aria-hidden size={40} strokeWidth={1.5} className="text-muted-d" />
            <p className="text-[15px] text-muted-d">{t["station.empty"]}</p>
          </div>
        )}
      </main>
    </div>
  );
}
