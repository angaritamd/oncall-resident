"""Worklist: join PACS studies (QIDO-RS) with order metadata and sort deterministically.

Order: technologist critical flag, then order priority, then longest wait.
Every reason shown to the user names its source; nothing here is a model judgement.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from adapters.base import Study, StudySource

from .cases import PRIORITY_RANK, CaseMeta


@dataclass
class WorkItem:
    study: Study
    meta: CaseMeta | None

    @property
    def case_id(self) -> str:
        return self.meta.case_id if self.meta else self.study.study_uid

    def wait_minutes(self, now: datetime) -> int | None:
        if not self.meta:
            return None
        return max(0, int((now - self.meta.arrived_at).total_seconds() // 60))

    def sort_key(self, now: datetime):
        if not self.meta:
            return (2, 99, 0)
        return (0 if self.meta.tech_critical else 1, PRIORITY_RANK[self.meta.priority], -self.wait_minutes(now))


async def build_worklist(source: StudySource, cases: dict[str, CaseMeta], now: datetime | None = None) -> list[WorkItem]:
    now = now or datetime.now(timezone.utc)
    studies = await source.list_studies()
    items = [WorkItem(s, cases.get(s.study_uid)) for s in studies]
    return sorted(items, key=lambda i: i.sort_key(now))
