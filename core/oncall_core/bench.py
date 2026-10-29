"""RAD·QC benchmark validation (ANG-174): the radiologist marks each synthetic benchmark case as valid or not.

Cases come read-only from a JSONL file (radqc/data/bench/*.jsonl); verdicts live in the state DB, one per case,
the last one wins. Only cases marked valid enter the benchmark that scores Glimmer base, v4 and v5.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS bench_verdicts (
  case_id TEXT PRIMARY KEY, verdict TEXT NOT NULL, note TEXT, by TEXT, at TEXT NOT NULL
);
"""
# what the page needs; provenance and the never_train flag stay in the file
FIELDS = ("id", "subtype", "type", "hard", "modality", "exam", "sex", "age", "indication", "findings", "impression", "expected")


class Bench:
    def __init__(self, store, path: str | Path):
        self.db, self.lock, self.path = store._db, store._lock, Path(path)
        with self.lock:
            self.db.executescript(SCHEMA)

    def cases(self) -> list[dict]:
        if not self.path.is_file():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out.append({k: r.get(k) for k in FIELDS} | {"model": r.get("provenance", {}).get("model")})
        return out

    def view(self) -> dict:
        with self.lock:
            rows = {r["case_id"]: dict(r) for r in self.db.execute("SELECT * FROM bench_verdicts")}
        cases = [c | {"verdict": rows.get(c["id"])} for c in self.cases()]
        done = [c for c in cases if c["verdict"]]
        return {"cases": cases, "total": len(cases), "validated": len(done),
                "valid": sum(c["verdict"]["verdict"] == "valid" for c in done)}

    def set(self, case_id: str, verdict: str, note: str | None, by: str) -> dict | None:
        if case_id not in {c["id"] for c in self.cases()}:
            return None
        at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO bench_verdicts VALUES (?, ?, ?, ?, ?)", (case_id, verdict, note, by, at))
        return {"case_id": case_id, "verdict": verdict, "note": note, "by": by, "at": at}
