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


# Fail-closed: only plain identifiers are queried (no QIDO wildcards, escapes or control chars).
PATIENT_ID_RE = re.compile(r"[A-Za-z0-9._^-][A-Za-z0-9._^ -]{0,63}")
PAGE_SIZE = 200
MAX_STUDIES = 2000


class OrthancQido:
    def __init__(
        self,
        dicomweb_root: str,
        timeout: float = 5.0,
        client: httpx.AsyncClient | None = None,
        auth: tuple[str, str] | None = None,
    ):
        self.root = dicomweb_root.rstrip("/")
        self.client = client or httpx.AsyncClient(timeout=timeout, auth=httpx.BasicAuth(*auth) if auth else None)

    async def _qido(self, params: dict) -> list[dict]:
        query = {"includefield": ",".join(TAGS.values()), "limit": str(PAGE_SIZE), **params}
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
        pid = (patient_id or "").rstrip(" ")  # DICOM pads values with trailing spaces only
        if not PATIENT_ID_RE.fullmatch(pid):
            return None
        page = await self._qido({"PatientID": pid})
        if len(page) >= PAGE_SIZE:
            return None
        return [s for s in map(parse_study, page) if s.patient_id.rstrip(" ") == pid]

    async def ping(self) -> bool:
        try:
            await self._qido({"limit": "1"})
            return True
        except SourceUnavailable:
            return False
