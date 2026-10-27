# adapters

Imaging-source adapters behind one interface (`base.StudySource`).

- `orthanc/`: **working.** Standard DICOMweb QIDO-RS (`/studies`), so it also works against any QIDO-RS server.
- `radmesh/`: **empty stub.** Only the interface; it raises `NotImplementedError`.
