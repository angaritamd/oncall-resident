"""Serialisation of work items into the shapes the app renders."""
from datetime import datetime

from .i18n import t
from .worklist import WorkItem


def item_view(item: WorkItem, lang: str, now: datetime, position: int) -> dict:
    m = item.meta
    reasons = []
    if m and m.tech_critical:
        reasons.append({"kind": "critical", "label": t(lang, "critical"), "source": t(lang, "src.tech")})
    if m:
        reasons.append({"kind": m.priority, "label": t(lang, f"priority.{m.priority}"), "source": t(lang, "src.order")})
    else:
        reasons.append({"kind": "unknown", "label": t(lang, "priority.unknown"), "source": t(lang, "src.none")})
    return {
        "position": position,
        "case_id": item.case_id,
        "study_uid": item.study.study_uid,
        "exam": m.exam[lang] if m else None,
        "modalities": list(item.study.modalities),
        "wait_minutes": item.wait_minutes(now),
        "arrived_at": m.arrived_at.isoformat() if m else None,
        "critical": bool(m and m.tech_critical),
        "priority": m.priority if m else None,
        "reasons": reasons,
        "has_metadata": m is not None,
        "reason": m.reason[lang] if m else None,
        "tech_note": m.tech_note[lang] if m else None,
    }


def case_view(item: WorkItem, lang: str, now: datetime, position: int, priors_in_pacs: int | None) -> dict:
    m = item.meta
    s = item.study
    return {
        **item_view(item, lang, now, position),
        "sex": m.sex if m else None,
        "age": m.age if m else None,
        "priors_declared": m.priors_available if m else None,
        "priors_in_pacs": priors_in_pacs,
        "study_date": s.study_date,
        "series_count": s.series_count,
        "instance_count": s.instance_count,
    }


def next_reason(item: WorkItem, lang: str, now: datetime) -> str:
    """Why this study is next, in the words of the ordering rule (never a model judgement)."""
    m = item.meta
    if not m:
        lead = t(lang, "next.nometa")
    elif m.tech_critical:
        lead = t(lang, "next.critical")
    else:
        lead = t(lang, "next.priority", p=t(lang, f"priority.{m.priority}"))
    wait = item.wait_minutes(now)
    tail = t(lang, "next.wait", m=wait) if wait is not None else ""
    return t(lang, "next.text", case=item.case_id, lead=lead, wait=tail)
