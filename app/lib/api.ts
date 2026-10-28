export type Lang = "es" | "en";

export type Reason = { kind: string; label: string; source: string };

export type Item = {
  position: number;
  case_id: string;
  study_uid: string;
  exam: string | null;
  modalities: string[];
  wait_minutes: number | null;
  arrived_at: string | null;
  critical: boolean;
  priority: string | null;
  reasons: Reason[];
  has_metadata: boolean;
  reason: string | null;
  tech_note: string | null;
};

export type Case = Item & {
  sex: string | null;
  age: number | null;
  priors_declared: boolean | null;
  priors_in_pacs: number | null;
  study_date: string | null;
  series_count: number | null;
  instance_count: number | null;
};

export type QcItem = {
  id: number;
  rule: string;
  severity: "error" | "verify";
  source: "rules" | "model";
  body_label: "findings" | "indication";
  body_excerpt: string | null;
  impression_excerpt: string | null;
  explanation: string | null;
  fix_find: string | null;
  fix_replace: string | null;
  marks: { section: "findings" | "impression"; text: string }[];
  status: "open" | "applied" | "dismissed";
  reason: string | null;
};

export type Report = {
  case_id: string;
  version: number;
  technique: string;
  findings: string;
  impression: string;
  status: "draft" | "signed";
  qc_mode: "agent" | "fallback" | "rules" | "seed" | null;
  signed_by: string | null;
  signed_at: string | null;
  qc: QcItem[];
  open_alerts: number;
  qc_pending: boolean;
  signable: boolean;
  proposal: "pending" | "accepted" | null; // template proposal ("Propuesta · verificar") until the radiologist accepts it
  template: string | null;
  blanks: string[]; // "[Dictar: …]" fields still to dictate
  proposal_pending: boolean;
};

export type NextUp = { item: Item | null; why: string };
export type PendingItem = {
  id: number;
  case_id: string;
  kind: "repeat_series" | "late_phase" | "missing_priors" | "second_review";
  label: string;
  note: string | null;
  source: "metadata" | "radiologist";
  source_label: string;
  status: "open" | "done";
  exam: string | null;
};
export type Signed = Report & { next: NextUp };
export type Worklist = { items: Item[]; signed_today: (Item & { signed_at: string })[] };

export type Diff = { section: "technique" | "findings" | "impression"; parts: { op: "eq" | "del" | "ins"; text: string }[] };

export type Block =
  | { type: "next_study"; item: Item; total: number }
  | { type: "study_list"; items: Item[] }
  | { type: "evidence"; item: Item }
  | { type: "case"; case: Case }
  | { type: "report"; report: Report; diff?: Diff }
  | { type: "pending_list"; items: PendingItem[] };

export type Mode = "agent" | "fallback" | "basic" | "command";
// retry: nothing was changed (no tool did it); the app offers to resend the same instruction
export type ChatReply = { text: string; blocks: Block[]; steps: string[]; mode: Mode; retry?: boolean };

export type Activity = {
  at: string;
  kind: "tool" | "view" | "chat" | "llm" | "qc" | "sign" | "voice";
  name: string;
  input: Record<string, unknown> | null;
  output: string | null;
  case_id: string | null;
  mode: Mode | null;
  ok: boolean;
  model?: string | null; // only present for admins
  tokens_in?: number | null;
  tokens_out?: number | null;
  cost_usd?: number | null;
};

export type ResidentState = "ready" | "waking" | "unavailable" | "basic";

export class ApiError extends Error {
  constructor(
    message: string,
    public kind: "offline" | "pacs" | "core" | "notfound" | "conflict" | "other",
  ) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  if (typeof navigator !== "undefined" && !navigator.onLine) throw new ApiError("offline", "offline");
  let res: Response;
  try {
    res = await fetch(path, { ...init, cache: "no-store", signal: AbortSignal.timeout(path.startsWith("/api/chat") ? 125_000 : path.startsWith("/api/reports") ? 65_000 : path.startsWith("/api/transcribe") ? 35_000 : 12_000) });
  } catch {
    throw new ApiError("network", "offline");
  }
  if (res.ok) {
    // the timeout or a dropped connection can also hit while the body is read: that is a network error too
    try {
      return await res.json();
    } catch {
      throw new ApiError("network", "offline");
    }
  }
  const body = await res.json().catch(() => ({}));
  const detail = typeof body.detail === "string" ? body.detail : res.statusText;
  if (res.status === 503) throw new ApiError(detail, "pacs");
  if (res.status === 502) throw new ApiError(detail, "core");
  if (res.status === 404) throw new ApiError(detail, "notfound");
  if (res.status === 409 || res.status === 422 || res.status === 403 || res.status === 429) throw new ApiError(detail, "conflict");
  throw new ApiError(detail, "other");
}

export const api = {
  chat: (text: string, lang: Lang, caseId?: string | null) =>
    call<ChatReply>("/api/chat", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text, lang, case_id: caseId ?? null }),
    }),
  report: (id: string) => call<Report>(`/api/reports/${encodeURIComponent(id)}`),
  stationConfig: () => call<{ viewer_url: string; linked: boolean }>("/api/station/config"),
  stationPair: () => call<{ station_id: string; code: string; expires_in: number }>("/api/station/pair", { method: "POST" }),
  stationState: (station: string) =>
    call<{ linked: boolean; code: string | null; last_study_uid: string | null }>(`/api/station/state?station=${encodeURIComponent(station)}`),
  stationLink: (code: string) =>
    call<{ linked: boolean }>("/api/station/link", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ code }),
    }),
  stationUnlink: () => call<{ linked: boolean }>("/api/station/unlink", { method: "POST" }),
  stationOpen: (caseId: string) =>
    call<{ sent: boolean }>("/api/station/open", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ case_id: caseId }),
    }),
  editReport: (id: string, version: number, sections: Partial<Pick<Report, "technique" | "findings" | "impression">>, lang: Lang) =>
    call<Report>(`/api/reports/${encodeURIComponent(id)}?lang=${lang}`, {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ version, ...sections }),
    }),
  applyFix: (id: string, item: number, lang: Lang) =>
    call<Report & { diff: Diff }>(`/api/reports/${encodeURIComponent(id)}/qc/${item}/apply?lang=${lang}`, { method: "POST" }),
  dismiss: (id: string, item: number, reason: string) =>
    call<Report>(`/api/reports/${encodeURIComponent(id)}/qc/${item}/dismiss`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ reason }),
    }),
  propose: (id: string, lang: Lang) => call<Report>(`/api/reports/${encodeURIComponent(id)}/propose?lang=${lang}`, { method: "POST" }),
  accept: (id: string, version: number) =>
    call<Report>(`/api/reports/${encodeURIComponent(id)}/accept`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ version }),
    }),
  sign: (id: string, version: number, lang: Lang) =>
    call<Signed>(`/api/reports/${encodeURIComponent(id)}/sign?lang=${lang}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ version }),
    }),
  worklist: (lang: Lang) => call<Worklist>(`/api/worklist?lang=${lang}`),
  case: (id: string, lang: Lang) => call<Case>(`/api/cases/${encodeURIComponent(id)}?lang=${lang}`),
  activity: () => call<{ items: Activity[] }>("/api/activity?detail=1"),
  resident: (touch = false) => call<{ state: ResidentState }>(`/api/resident${touch ? "?touch=1" : ""}`),
  pending: (lang: Lang) => call<{ items: PendingItem[]; summary: string }>(`/api/pending?lang=${lang}`),
  pendingStatus: (id: number, action: "done" | "reopen") => call<PendingItem>(`/api/pending/${id}/${action}`, { method: "POST" }),
  voiceConfig: () => call<{ available: boolean; provider: "meta" | "local" | null }>("/api/voice/config"),
  transcribe: (wav: Blob, lang: Lang) =>
    call<{ text: string; audio_ms: number; latency_ms: number; provider: string }>(`/api/transcribe?lang=${lang}`, {
      method: "POST",
      headers: { "content-type": "audio/wav" },
      body: wav,
    }),
  health: () => call<{ core: string; pacs: string; llm: string }>("/api/health"),
};
