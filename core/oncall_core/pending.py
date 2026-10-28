"""Pending items per study (pending_items): what is left to do after reading, for the shift or for tomorrow.

Kinds: series to repeat, late phase / new injection, priors that are missing, second review tomorrow.
Two sources, always labelled: the order and PACS metadata (derived in code), and the radiologist's own request
("pídele previos"). Nothing is sent to anyone: this is a list for the radiologist.
"""
import re
from datetime import datetime, timezone

from .intents import _norm

KINDS = ("repeat_series", "late_phase", "missing_priors", "second_review")

SCHEMA = """
CREATE TABLE IF NOT EXISTS pending_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, kind TEXT NOT NULL, note TEXT,
  source TEXT NOT NULL,          -- 'metadata' | 'radiologist'
  status TEXT NOT NULL,          -- 'open' | 'done'
  by TEXT, at TEXT NOT NULL,
  UNIQUE (case_id, kind)
);
"""

# what the radiologist says → kind (whole phrases; anything else goes to the model's add_pending_item tool)
_REQUESTS = [
    ("missing_priors", re.compile(r"\b(pide|pidele|pidan|pedir|solicita|consigue|busca)( (le|les))? (los )?(estudios )?previos\b|\b(request|get|ask for) (the )?priors\b")),
    ("second_review", re.compile(r"\b(segunda revision|revisar(lo|la)? manana|revision manana|lo reviso manana|second (look|review)|review (it )?tomorrow)\b")),
    ("repeat_series", re.compile(r"\b(repetir|repite|repitan) (la )?serie\b|\brepeat (the )?series\b")),
    ("late_phase", re.compile(r"\b(cortes tardios|fase tardia|nueva inyeccion|reinyectar|delayed (phase|images)|new injection)\b")),
]
_TOMORROW = re.compile(r"^(que (me )?(queda|quedo|hay) (para|pendiente para) manana|pendientes (de|para) manana|what'?s (left )?(for|due) tomorrow)$")


def request_kind(text: str) -> str | None:
    """Only short requests ("pídele previos"); a longer dictation that also mentions one goes to the model."""
    n = re.sub(r"[¿?¡!.,;:]", " ", _norm(text))
    n = re.sub(r"\s+", " ", n).strip()
    if len(n.split()) > 8:
        return None
    for kind, rx in _REQUESTS:
        if rx.search(n):
            return kind
    return None


def is_tomorrow_query(text: str) -> bool:
    n = re.sub(r"[¿?¡!.,;:]", " ", _norm(text))
    return bool(_TOMORROW.match(re.sub(r"\s+", " ", n).strip()))


class Pending:
    def __init__(self, store):
        self.store, self.db, self.lock = store, store._db, store._lock
        with self.lock:
            self.db.executescript(SCHEMA)

    def add(self, case_id: str, kind: str, source: str, note: str | None = None, by: str | None = None) -> dict:
        """Idempotent per (study, kind): asking twice keeps one item (re-opened if it was done)."""
        if kind not in KINDS:
            raise ValueError(kind)
        now = datetime.now(timezone.utc).isoformat()
        note = (note or "").strip()[:200] or None
        with self.lock:
            self.db.execute(
                "INSERT INTO pending_items (case_id, kind, note, source, status, by, at) VALUES (?, ?, ?, ?, 'open', ?, ?) "
                "ON CONFLICT(case_id, kind) DO UPDATE SET status='open', "
                "note=COALESCE(excluded.note, pending_items.note), "
                # a radiologist request outranks a metadata derivation; metadata never overwrites the radiologist
                "source=CASE WHEN excluded.source='radiologist' THEN 'radiologist' ELSE pending_items.source END, "
                "by=COALESCE(excluded.by, pending_items.by) "
                "WHERE pending_items.status = 'done' OR excluded.source = 'radiologist'",
                (case_id, kind, note, source, by, now))
            row = self.db.execute("SELECT * FROM pending_items WHERE case_id = ? AND kind = ?", (case_id, kind)).fetchone()
        return dict(row)

    def derive(self, case_id: str, *, priors_declared: bool | None, priors_in_pacs: int | None, requests: list[dict]) -> None:
        """From metadata: priors the order declares but the PACS does not have, and the technologist's requests.
        Never re-opens an item the radiologist closed."""
        with self.lock:
            closed = {r["kind"] for r in self.db.execute(
                "SELECT kind FROM pending_items WHERE case_id = ? AND status = 'done'", (case_id,))}
            have = {r["kind"] for r in self.db.execute("SELECT kind FROM pending_items WHERE case_id = ?", (case_id,))}
        wanted = []
        if priors_declared and priors_in_pacs == 0:
            wanted.append(("missing_priors", None))
        for r in requests:
            if r.get("kind") in KINDS:
                wanted.append((r["kind"], r.get("note")))
        for kind, note in wanted:
            if kind not in have and kind not in closed:
                self.add(case_id, kind, "metadata", note)

    def list(self, status: str = "open") -> list[dict]:
        with self.lock:
            rows = self.db.execute("SELECT * FROM pending_items WHERE status = ? ORDER BY case_id, id", (status,)).fetchall()
        return [dict(r) for r in rows]

    def set_status(self, item_id: int, status: str) -> dict | None:
        with self.lock:
            self.db.execute("UPDATE pending_items SET status = ? WHERE id = ?", (status, item_id))
            row = self.db.execute("SELECT * FROM pending_items WHERE id = ?", (item_id,)).fetchone()
        return dict(row) if row else None

    def reset(self) -> None:
        with self.lock:
            self.db.execute("DELETE FROM pending_items")
