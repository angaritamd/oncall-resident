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
};

export type Diff = { section: "technique" | "findings" | "impression"; parts: { op: "eq" | "del" | "ins"; text: string }[] };

export type Block =
  | { type: "next_study"; item: Item; total: number }
  | { type: "study_list"; items: Item[] }
  | { type: "evidence"; item: Item }
  | { type: "case"; case: Case }
  | { type: "report"; report: Report; diff?: Diff };

export type Mode = "agent" | "fallback" | "basic";
export type ChatReply = { text: string; blocks: Block[]; steps: string[]; mode: Mode };

export type Activity = {
  at: string;
  kind: "tool" | "view" | "chat" | "llm" | "qc" | "sign";
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
    res = await fetch(path, { ...init, cache: "no-store", signal: AbortSignal.timeout(path.startsWith("/api/chat") ? 125_000 : path.startsWith("/api/reports") ? 65_000 : 12_000) });
  } catch {
    throw new ApiError("network", "offline");
  }
  if (res.ok) return res.json();
  const body = await res.json().catch(() => ({}));
  const detail = typeof body.detail === "string" ? body.detail : res.statusText;
  if (res.status === 503) throw new ApiError(detail, "pacs");
  if (res.status === 502) throw new ApiError(detail, "core");
  if (res.status === 404) throw new ApiError(detail, "notfound");
  if (res.status === 409 || res.status === 422 || res.status === 403) throw new ApiError(detail, "conflict");
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
  sign: (id: string, version: number) =>
    call<Report>(`/api/reports/${encodeURIComponent(id)}/sign`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ version }),
    }),
  worklist: (lang: Lang) => call<{ items: Item[] }>(`/api/worklist?lang=${lang}`),
  case: (id: string, lang: Lang) => call<Case>(`/api/cases/${encodeURIComponent(id)}?lang=${lang}`),
  activity: () => call<{ items: Activity[] }>("/api/activity?detail=1"),
  resident: () => call<{ state: ResidentState }>("/api/resident"),
  health: () => call<{ core: string; pacs: string; llm: string }>("/api/health"),
};
