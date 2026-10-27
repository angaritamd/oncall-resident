"""Synthetic per-study metadata (stand-in for what a RIS order would carry)."""
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

PRIORITY_RANK = {"urgent": 0, "priority": 1, "routine": 2}


@dataclass(frozen=True)
class CaseMeta:
    case_id: str
    study_uid: str
    exam: dict
    reason: dict
    tech_note: dict
    tech_critical: bool
    priority: str
    arrived_at: datetime
    priors_available: bool


def load_cases(path: str | Path, now: datetime | None = None) -> dict[str, CaseMeta]:
    """Index by StudyInstanceUID. Arrival times are offsets from load time so the demo stays current."""
    now = now or datetime.now(timezone.utc)
    raw = json.loads(Path(path).read_text())
    out = {}
    for c in raw["cases"]:
        if c["priority"] not in PRIORITY_RANK:
            raise ValueError(f"{c['case_id']}: unknown priority {c['priority']!r}")
        out[c["study_uid"]] = CaseMeta(
            case_id=c["case_id"],
            study_uid=c["study_uid"],
            exam=c["exam"],
            reason=c["reason"],
            tech_note=c["tech_note"],
            tech_critical=bool(c["tech_critical"]),
            priority=c["priority"],
            arrived_at=now - timedelta(minutes=c["arrival_minutes_ago"]),
            priors_available=bool(c["priors_available"]),
        )
    return out
