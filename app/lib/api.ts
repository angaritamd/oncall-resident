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

export type Block =
  | { type: "next_study"; item: Item; total: number }
  | { type: "study_list"; items: Item[] }
  | { type: "evidence"; item: Item }
  | { type: "case"; case: Case };

export type Mode = "agent" | "fallback" | "basic";
export type ChatReply = { text: string; blocks: Block[]; steps: string[]; mode: Mode };

export type Activity = {
  at: string;
  kind: "tool" | "view" | "chat";
  name: string;
  input: Record<string, unknown> | null;
  output: string | null;
  case_id: string | null;
  mode: Mode | null;
  ok: boolean;
  model?: string | null; // only present for admins
};

export type ResidentState = "ready" | "waking" | "unavailable" | "basic";

export class ApiError extends Error {
  constructor(
    message: string,
    public kind: "offline" | "pacs" | "core" | "notfound" | "other",
  ) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  if (typeof navigator !== "undefined" && !navigator.onLine) throw new ApiError("offline", "offline");
  let res: Response;
  try {
    res = await fetch(path, { ...init, cache: "no-store", signal: AbortSignal.timeout(path.startsWith("/api/chat") ? 125_000 : 12_000) });
  } catch {
    throw new ApiError("network", "offline");
  }
  if (res.ok) return res.json();
  const body = await res.json().catch(() => ({}));
  const detail = typeof body.detail === "string" ? body.detail : res.statusText;
  if (res.status === 503) throw new ApiError(detail, "pacs");
  if (res.status === 502) throw new ApiError(detail, "core");
  if (res.status === 404) throw new ApiError(detail, "notfound");
  throw new ApiError(detail, "other");
}

export const api = {
  chat: (text: string, lang: Lang) =>
    call<ChatReply>("/api/chat", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text, lang }),
    }),
  worklist: (lang: Lang) => call<{ items: Item[] }>(`/api/worklist?lang=${lang}`),
  case: (id: string, lang: Lang) => call<Case>(`/api/cases/${encodeURIComponent(id)}?lang=${lang}`),
  activity: () => call<{ items: Activity[] }>("/api/activity?detail=1"),
  resident: () => call<{ state: ResidentState }>("/api/resident"),
  health: () => call<{ core: string; pacs: string; llm: string }>("/api/health"),
};
