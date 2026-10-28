"""Synthetic per-study metadata (stand-in for what a RIS order would carry)."""
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

# order priority: STAT > urgente > rutina
PRIORITY_RANK = {"stat": 0, "urgent": 1, "routine": 2}


@dataclass(frozen=True)
class CaseMeta:
    case_id: str
    study_uid: str
    exam: dict
    sex: str | None
    age: int | None
    reason: dict
    tech_note: dict
    tech_critical: bool
    priority: str
    arrived_at: datetime
    priors_available: bool
    # technologist / order requests for after the reading, e.g. a series to repeat (synthetic metadata)
    tech_requests: tuple = ()


def load_cases(
    path: str | Path,
    now: datetime | None = None,
    arrival: Callable[[str, datetime], datetime] | None = None,
) -> dict[str, CaseMeta]:
    """Index by StudyInstanceUID. A case's arrival is first computed as an offset from load time; when an
    `arrival` resolver (the SQLite store) is given, that first value is persisted and reused afterwards."""
    now = now or datetime.now(timezone.utc)
    arrival = arrival or (lambda _case, default: default)
    raw = json.loads(Path(path).read_text())
    out = {}
    for c in raw["cases"]:
        if c["priority"] not in PRIORITY_RANK:
            raise ValueError(f"{c['case_id']}: unknown priority {c['priority']!r}")
        out[c["study_uid"]] = CaseMeta(
            case_id=c["case_id"],
            study_uid=c["study_uid"],
            exam=c["exam"],
            sex=c.get("sex"),
            age=c.get("age"),
            reason=c["reason"],
            tech_note=c["tech_note"],
            tech_critical=bool(c["tech_critical"]),
            priority=c["priority"],
            arrived_at=arrival(c["case_id"], now - timedelta(minutes=c["arrival_minutes_ago"])),
            priors_available=bool(c["priors_available"]),
            tech_requests=tuple(c.get("tech_requests") or ()),
        )
    return out
