"""RAD·QC benchmark validation (ANG-174): the radiologist marks each synthetic benchmark case as valid or not.

Cases come read-only from JSONL files, one per set: "bench" (radqc/data/bench/*.jsonl, public) and "train" (the
training pilot generated with Glimmer; private, kept only in the server's data volume). Case IDs are unique across
sets (B5-…, T5-…). Verdicts live in the state DB, one per case,
the last one wins. A verdict is bound to a digest of the case content: if the case is regenerated under the same ID,
the old verdict no longer counts and the case is reviewed again. Only cases marked valid enter the benchmark that
scores Glimmer base, v4 and v5. Admin only (the proxy and the core both check it).
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS bench_verdicts (
  case_id TEXT PRIMARY KEY, verdict TEXT NOT NULL, note TEXT, by TEXT, at TEXT NOT NULL, digest TEXT NOT NULL
);
"""
# what the page needs; provenance and the never_train flag stay in the file
FIELDS = ("id", "subtype", "type", "hard", "modality", "exam", "sex", "age", "indication", "findings", "impression", "expected")


def digest(case: dict) -> str:
    """What the radiologist validated: the report text, the planted error and its labels."""
    keep = {k: case.get(k) for k in FIELDS if k != "id"}
    return hashlib.sha256(json.dumps(keep, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


class Bench:
    def __init__(self, store, paths: dict[str, str | Path]):
        self.db, self.lock, self.paths = store._db, store._lock, {k: Path(v) for k, v in paths.items() if v}
        with self.lock:
            self.db.executescript(SCHEMA)

    def sets(self) -> list[str]:
        return [k for k, p in self.paths.items() if p.is_file()]

    def cases(self, which: str = "bench") -> list[dict]:
        path = self.paths.get(which)
        if not path or not path.is_file():
            return []
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                c = {k: r.get(k) for k in FIELDS}
                out.append(c | {"model": r.get("provenance", {}).get("model"), "digest": digest(c)})
        return out

    def view(self, which: str = "bench") -> dict:
        with self.lock:
            rows = {r["case_id"]: dict(r) for r in self.db.execute("SELECT * FROM bench_verdicts")}
        # a verdict on a different version of the case does not count
        cases = [c | {"verdict": v if (v := rows.get(c["id"])) and v.pop("digest") == c["digest"] else None}
                 for c in self.cases(which)]
        done = [c for c in cases if c["verdict"]]
        return {"set": which, "sets": self.sets(), "cases": cases, "total": len(cases), "validated": len(done),
                "valid": sum(c["verdict"]["verdict"] == "valid" for c in done)}

    def set(self, case_id: str, verdict: str, note: str | None, by: str) -> dict | None:
        case = next((c for w in self.paths for c in self.cases(w) if c["id"] == case_id), None)
        if not case:
            return None
        at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO bench_verdicts VALUES (?, ?, ?, ?, ?, ?)",
                            (case_id, verdict, note, by, at, case["digest"]))
        return {"case_id": case_id, "verdict": verdict, "note": note, "by": by, "at": at}
