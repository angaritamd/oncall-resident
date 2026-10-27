"""RadMesh adapter: interface stub only.

RadMesh is a private, pre-existing RIS/PACS and is not part of this repository.
This stub fixes the shape a future adapter must satisfy; it has no implementation
and is never wired into the demo.
"""
from adapters.base import Study


class RadmeshSource:
    async def list_studies(self) -> list[Study]:
        raise NotImplementedError("RadMesh adapter is not implemented")

    async def studies_for_patient(self, patient_id: str) -> list[Study]:
        raise NotImplementedError("RadMesh adapter is not implemented")

    async def ping(self) -> bool:
        return False
