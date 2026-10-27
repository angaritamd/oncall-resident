# oncall-resident

An AI on-call radiology resident as a mobile chat app, independent of any RIS and connected through open standards (DICOMweb).

> **Workflow tool, not a medical device. The radiologist decides and signs.**

## Status

Day 1: no LLM yet. The chat answers fixed intents (pending studies, open case) with data read from Orthanc over DICOMweb (QIDO-RS) and synthetic per-study metadata. See [BUILD_LOG.md](BUILD_LOG.md).

## Layout

| Path | What |
|---|---|
| `app/` | Next.js (App Router, TypeScript, Tailwind) mobile-first PWA |
| `core/` | Python FastAPI orchestrator (no LLM today) |
| `adapters/` | `orthanc` (DICOMweb QIDO-RS, working) · `radmesh` (empty interface stub) |
| `demo/` | docker compose: Orthanc + core + app, seed scripts and synthetic metadata |
| `serving/`, `radqc/` | README only: what comes later |
| `scripts/` | secret / denylist / PHI scanner used by the git hook and CI |

## Provenance

| Built during the hackathon (Oct 26 after kickoff – Nov 4) | Pre-existing (not in this repo) |
|---|---|
| Everything in this repository: app, core, adapters, demo, scanners, docs | RadMesh: private RIS/PACS |
| | AI Mode prototype inside the RIS (Oct 24–25) |
| | Glimmer server on Modal (Oct 21–26) |
| | RAD·QC v3 and v4 pilot |
| | UI mockup (Oct 26, visual concept only) |

No code from pre-existing projects is copied or imported here.

## Data

Only public, redistributable DICOM (see [DATA_SOURCES.md](DATA_SOURCES.md)) and synthetic clinical metadata. No real patients.

## Run the demo

```sh
cd demo
./seed/fetch.sh            # downloads the public DICOM listed in seed/manifest.json
docker compose -p oncall-resident up -d --build
./seed/load.sh             # uploads them into the demo Orthanc
```

App on `:13000`. See `demo/README.md` for ports and binding.

## Security scanning

`scripts/install-hooks.sh` installs a pre-commit hook running gitleaks, a denylist kept **outside** the repo (`~/.config/oncall-resident/denylist.txt`), and PHI patterns. CI runs the same checks.

## License

AGPL-3.0 — see [LICENSE](LICENSE). Commercial licensing: [COMMERCIAL.md](COMMERCIAL.md).
