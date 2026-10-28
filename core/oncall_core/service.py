"""Read access to the worklist and to single studies, shared by the UI endpoints, the tools and basic mode."""
from datetime import datetime, timezone
from typing import Callable

from adapters.base import StudySource

from .cases import CaseMeta
from .views import case_view
from .worklist import WorkItem, build_worklist


class Service:
    def __init__(self, source: StudySource, cases: dict[str, CaseMeta], signed: Callable[[], dict[str, str]] | None = None):
        self.source = source
        self.cases = cases
        # case_id -> signed_at of every signed report; signed studies are no longer pending
        self.signed = signed or (lambda: {})

    async def worklist(self) -> tuple[list[WorkItem], datetime]:
        """Pending studies only, in reading order."""
        now = datetime.now(timezone.utc)
        return await build_worklist(self.source, self.cases, now, exclude=set(self.signed())), now

    async def all_items(self) -> tuple[list[WorkItem], datetime]:
        """Every study in the PACS (pending and signed), in reading order."""
        now = datetime.now(timezone.utc)
        return await build_worklist(self.source, self.cases, now), now

    async def find(self, case_id: str) -> tuple[WorkItem, int, datetime] | None:
        """Finds pending and signed studies; the position is the place in the pending list (0 once signed)."""
        items, now = await self.all_items()
        signed = self.signed()
        pending = [i for i in items if i.case_id not in signed]
        for it in items:
            if it.case_id.lower() == case_id.strip().lower():
                return it, (pending.index(it) + 1 if it in pending else 0), now
        return None

    async def signed_since(self, since: datetime) -> tuple[list[tuple[WorkItem, str]], datetime]:
        """Studies signed since `since`, most recent first."""
        items, now = await self.all_items()
        signed = self.signed()
        out = [(i, signed[i.case_id]) for i in items if i.case_id in signed and datetime.fromisoformat(signed[i.case_id]) >= since]
        return sorted(out, key=lambda x: x[1], reverse=True), now

    async def open_case(self, case_id: str, lang: str) -> dict | None:
        found = await self.find(case_id)
        if not found:
            return None
        it, pos, now = found
        others = await self.source.studies_for_patient(it.study.patient_id)
        priors = None if others is None else len([s for s in others if s.study_uid != it.study.study_uid])
        return case_view(it, lang, now, pos, priors)

