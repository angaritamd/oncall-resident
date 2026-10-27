# Build log

## 2026-10-26 — Day 1 (after kickoff) · ANG-170

**Works for real (no LLM, no Muse Code, no Meta API):**
- Orthanc (DICOMweb) seeded with 5 public LIDC-IDRI chest studies (2 radiographs, 3 CT; CC BY 3.0) plus synthetic order metadata.
- `core` (FastAPI): rule-based intents over QIDO-RS:
  - "¿Qué tengo pendiente?" returns a summary, the next study and the full list.
  - "¿Por qué va primero?" explains where the priority comes from (technologist flag or order, never the model).
  - "Abrir DEMO-000N" opens the case. Priors are shown two ways: what the order declares, and what is actually in this PACS.
- `app` (Next.js PWA, dark, ES/EN): chat, Pendientes and Actividad tabs, a case view with back to chat, and loading, empty, offline and PACS-failure states with retry.
- Demo stack on the hack server, as a separate compose project, reachable over Tailscale only.
- Scanning: gitleaks, an external denylist, PHI patterns and DICOM detection, run by git hooks and CI.
- Tests: 13 core unit tests and 10 Playwright e2e runs in Brave (390 px mobile and desktop).

**Not available yet (shown as unavailable in the UI, never simulated):** LLM, microphone/voice, image viewer, the "necesita confirmación" state, authentication, the RadMesh adapter (stub only), serving/, radqc/.

**Known limits:** arrival times are offsets from core start, and the activity log is in memory. Both reset when the core restarts.
