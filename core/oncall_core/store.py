"""SQLite state that must survive restarts: arrival times and the activity / tool-call log."""
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS arrivals (case_id TEXT PRIMARY KEY, arrived_at TEXT NOT NULL);
-- model usage for spend; NOT subject to the activity retention
CREATE TABLE IF NOT EXISTS usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, model TEXT, tokens_in INTEGER, tokens_out INTEGER, cost_usd REAL
);
CREATE TABLE IF NOT EXISTS activity (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL,
  kind TEXT NOT NULL,          -- 'tool' (agent tool call), 'view' (UI read), 'chat' (one answer)
  name TEXT NOT NULL,          -- tool / view name
  input TEXT,                  -- JSON
  output TEXT,                 -- short summary, never the full payload
  case_id TEXT,
  model TEXT,                  -- model that requested the call (null for UI reads)
  mode TEXT,                   -- agent | fallback | basic
  ok INTEGER NOT NULL
);
"""
# columns added after the first release; created on startup when missing
MIGRATIONS = [("activity", "tokens_in", "INTEGER"), ("activity", "tokens_out", "INTEGER"), ("activity", "cost_usd", "REAL")]


MAX_ROWS = 5000
MAX_FIELD = 1000


class Store:
    def __init__(self, path: str | Path):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.executescript(SCHEMA)
            for table, col, typ in MIGRATIONS:
                cols = {r["name"] for r in self._db.execute(f"PRAGMA table_info({table})")}
                if col not in cols:
                    self._db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")

    def arrival(self, case_id: str, default: datetime) -> datetime:
        """First time a case is seen its arrival is recorded; later loads (and restarts) reuse it."""
        with self._lock:
            self._db.execute("INSERT OR IGNORE INTO arrivals VALUES (?, ?)", (case_id, default.isoformat()))
            row = self._db.execute("SELECT arrived_at FROM arrivals WHERE case_id = ?", (case_id,)).fetchone()
        return datetime.fromisoformat(row["arrived_at"])

    def log(self, kind: str, name: str, *, input: dict | None = None, output: str | None = None,
            case_id: str | None = None, model: str | None = None, mode: str | None = None, ok: bool = True,
            tokens_in: int | None = None, tokens_out: int | None = None, cost_usd: float | None = None) -> dict:
        raw_input = json.dumps(input, ensure_ascii=False) if input is not None else None
        if raw_input is not None and len(raw_input) > MAX_FIELD:
            raw_input = json.dumps({"truncated": raw_input[:MAX_FIELD]}, ensure_ascii=False)
        rec = {"at": datetime.now(timezone.utc).isoformat(), "kind": kind, "name": name[:100],
               "input": raw_input, "output": output[:MAX_FIELD] if output else output,
               "case_id": str(case_id)[:100] if case_id is not None else None,
               "model": model, "mode": mode, "ok": int(ok),
               "tokens_in": tokens_in, "tokens_out": tokens_out, "cost_usd": cost_usd}
        with self._lock:
            self._db.execute(
                "INSERT INTO activity (at, kind, name, input, output, case_id, model, mode, ok, tokens_in, tokens_out, cost_usd) "
                "VALUES (:at, :kind, :name, :input, :output, :case_id, :model, :mode, :ok, :tokens_in, :tokens_out, :cost_usd)", rec)
            if kind == "llm" and name != "qc_unavailable":
                self._db.execute("INSERT INTO usage (at, model, tokens_in, tokens_out, cost_usd) VALUES (?, ?, ?, ?, ?)",
                                 (rec["at"], model, tokens_in, tokens_out, cost_usd))
            # retention: keep the newest MAX_ROWS records
            self._db.execute("DELETE FROM activity WHERE id <= (SELECT MAX(id) FROM activity) - ?", (MAX_ROWS,))
        return rec

    def recent(self, limit: int = 100) -> list[dict]:
        with self._lock:
            rows = self._db.execute("SELECT * FROM activity ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["input"] = json.loads(d["input"]) if d["input"] else None
            d["ok"] = bool(d["ok"])
            out.append(d)
        return out

    def meta_spend(self) -> float:
        """Everything spent on the Meta Model API (fallback model and voice), all time: the usage table is never
        trimmed or reset."""
        with self._lock:
            row = self._db.execute("SELECT SUM(cost_usd) FROM usage WHERE model LIKE 'meta%'").fetchone()
        return float(row[0] or 0)

    def spend(self, since_iso: str) -> dict:
        """Model usage since a timestamp. `usd_priced` sums only per-token calls (Meta Model API);
        `unpriced_calls` (e.g. Glimmer on our own GPU, billed by time) have no per-call cost, never 0."""
        with self._lock:
            row = self._db.execute(
                "SELECT COUNT(*) calls, SUM(tokens_in) tin, SUM(tokens_out) tout, SUM(cost_usd) usd_priced, "
                "SUM(CASE WHEN cost_usd IS NULL THEN 1 ELSE 0 END) unpriced_calls "
                "FROM usage WHERE at >= ?", (since_iso,)).fetchone()
        return dict(row)
