"""Read access to the worklist and to single studies, shared by the UI endpoints, the tools and basic mode."""
from datetime import datetime, timezone

from adapters.base import StudySource

from .cases import CaseMeta
from .views import case_view
from .worklist import WorkItem, build_worklist


class Service:
    def __init__(self, source: StudySource, cases: dict[str, CaseMeta]):
        self.source = source
        self.cases = cases

    async def worklist(self) -> tuple[list[WorkItem], datetime]:
        now = datetime.now(timezone.utc)
        return await build_worklist(self.source, self.cases, now), now

    async def find(self, case_id: str) -> tuple[WorkItem, int, datetime] | None:
        items, now = await self.worklist()
        for i, it in enumerate(items, 1):
            if it.case_id.lower() == case_id.strip().lower():
                return it, i, now
        return None

    async def open_case(self, case_id: str, lang: str) -> dict | None:
        found = await self.find(case_id)
        if not found:
            return None
        it, pos, now = found
        others = await self.source.studies_for_patient(it.study.patient_id)
        priors = None if others is None else len([s for s in others if s.study_uid != it.study.study_uid])
        return case_view(it, lang, now, pos, priors)
