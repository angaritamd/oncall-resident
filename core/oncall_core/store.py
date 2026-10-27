"""SQLite state that must survive restarts: arrival times and the activity / tool-call log."""
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS arrivals (case_id TEXT PRIMARY KEY, arrived_at TEXT NOT NULL);
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

    def arrival(self, case_id: str, default: datetime) -> datetime:
        """First time a case is seen its arrival is recorded; later loads (and restarts) reuse it."""
        with self._lock:
            self._db.execute("INSERT OR IGNORE INTO arrivals VALUES (?, ?)", (case_id, default.isoformat()))
            row = self._db.execute("SELECT arrived_at FROM arrivals WHERE case_id = ?", (case_id,)).fetchone()
        return datetime.fromisoformat(row["arrived_at"])

    def log(self, kind: str, name: str, *, input: dict | None = None, output: str | None = None,
            case_id: str | None = None, model: str | None = None, mode: str | None = None, ok: bool = True) -> dict:
        rec = {"at": datetime.now(timezone.utc).isoformat(), "kind": kind, "name": name,
               "input": json.dumps(input, ensure_ascii=False) if input is not None else None,
               "output": output, "case_id": case_id, "model": model, "mode": mode, "ok": int(ok)}
        with self._lock:
            self._db.execute(
                "INSERT INTO activity (at, kind, name, input, output, case_id, model, mode, ok) "
                "VALUES (:at, :kind, :name, :input, :output, :case_id, :model, :mode, :ok)", rec)
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
