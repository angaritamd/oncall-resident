"""Interface every imaging source adapter implements."""
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Study:
    study_uid: str
    patient_id: str
    modalities: tuple[str, ...]
    study_date: str | None
    description: str | None
    series_count: int | None
    instance_count: int | None
    extra: dict = field(default_factory=dict)


class SourceUnavailable(Exception):
    """The imaging source could not be reached or answered with an error."""


class StudySource(Protocol):
    async def list_studies(self) -> list[Study]: ...

    async def studies_for_patient(self, patient_id: str) -> list[Study]: ...

    async def ping(self) -> bool: ...
