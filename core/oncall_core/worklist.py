"""Worklist: join PACS studies (QIDO-RS) with order metadata and sort deterministically.

One rule, in code and never decided by the model:
technologist critical flag > order priority (STAT > urgente > rutina) > longest wait (oldest arrival first)
> study ID as the final tiebreak. Arrival is a persisted timestamp (not minutes rounded at request time), so
the same inputs always give the same order. Signed studies leave the pending list.
Every reason shown to the user names its source; nothing here is a model judgement.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from adapters.base import Study, StudySource

from .cases import PRIORITY_RANK, CaseMeta

_LAST = datetime.max.replace(tzinfo=timezone.utc)


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

    def sort_key(self):
        if not self.meta:
            # studies without order metadata go last, by UID
            return (2, 99, _LAST, self.study.study_uid)
        return (0 if self.meta.tech_critical else 1, PRIORITY_RANK[self.meta.priority], self.meta.arrived_at, self.case_id)


def sort_items(items: list[WorkItem]) -> list[WorkItem]:
    return sorted(items, key=WorkItem.sort_key)


async def build_worklist(source: StudySource, cases: dict[str, CaseMeta], now: datetime | None = None,
                         exclude: set[str] | frozenset = frozenset()) -> list[WorkItem]:
    """`exclude`: case IDs that are no longer pending (signed)."""
    studies = await source.list_studies()
    items = [WorkItem(s, cases.get(s.study_uid)) for s in studies]
    return sort_items([i for i in items if i.case_id not in exclude])
