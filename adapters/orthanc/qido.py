"""Orthanc adapter over standard DICOMweb QIDO-RS (no Orthanc-specific REST)."""
import re

import httpx

from adapters.base import SourceUnavailable, Study

# DICOM tags requested from QIDO-RS
TAGS = {
    "StudyInstanceUID": "0020000D",
    "PatientID": "00100020",
    "ModalitiesInStudy": "00080061",
    "StudyDate": "00080020",
    "StudyDescription": "00081030",
    "NumberOfStudyRelatedSeries": "00201206",
    "NumberOfStudyRelatedInstances": "00201208",
}


def _value(item: dict, tag: str):
    values = item.get(TAGS[tag], {}).get("Value") or []
    return values


def _first(item: dict, tag: str):
    values = _value(item, tag)
    return values[0] if values else None


def parse_study(item: dict) -> Study:
    return Study(
        study_uid=_first(item, "StudyInstanceUID"),
        patient_id=_first(item, "PatientID") or "",
        modalities=tuple(_value(item, "ModalitiesInStudy")),
        study_date=_first(item, "StudyDate"),
        description=_first(item, "StudyDescription"),
        series_count=_first(item, "NumberOfStudyRelatedSeries"),
        instance_count=_first(item, "NumberOfStudyRelatedInstances"),
    )


# Characters with QIDO-RS matching semantics (wildcards, escapes, multi-value) or control chars.
UNSAFE_ID_RE = re.compile(r"[*?\\\x00-\x1f]")
PAGE_SIZE = 200
MAX_STUDIES = 2000


class OrthancQido:
    def __init__(self, dicomweb_root: str, timeout: float = 5.0, client: httpx.AsyncClient | None = None):
        self.root = dicomweb_root.rstrip("/")
        self.client = client or httpx.AsyncClient(timeout=timeout)

    async def _qido(self, params: dict) -> list[dict]:
        query = {"includefield": ",".join(TAGS.values()), **params}
        try:
            r = await self.client.get(f"{self.root}/studies", params=query, headers={"Accept": "application/dicom+json"})
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise SourceUnavailable(f"QIDO-RS failed: {type(e).__name__}") from e
        return r.json() if r.content else []

    async def list_studies(self) -> list[Study]:
        """Pages through every study. Above MAX_STUDIES it fails loudly rather than return a partial worklist."""
        out: list[dict] = []
        while True:
            page = await self._qido({"limit": str(PAGE_SIZE), "offset": str(len(out))})
            out.extend(page)
            if len(page) < PAGE_SIZE:
                break
            if len(out) >= MAX_STUDIES:
                raise SourceUnavailable(f"more than {MAX_STUDIES} studies; worklist would be incomplete")
        return [parse_study(i) for i in out]

    async def studies_for_patient(self, patient_id: str) -> list[Study] | None:
        """Exact PatientID match. None means "cannot be determined", never "no studies"."""
        if not patient_id or UNSAFE_ID_RE.search(patient_id):
            return None
        found = [parse_study(i) for i in await self._qido({"PatientID": patient_id})]
        return [s for s in found if s.patient_id == patient_id]

    async def ping(self) -> bool:
        try:
            await self._qido({"limit": "1"})
            return True
        except SourceUnavailable:
            return False
