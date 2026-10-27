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
printf 'ORTHANC_USER=oncall\nORTHANC_PASSWORD=%s\n' "$(openssl rand -hex 24)" > .env && chmod 600 .env
./seed/fetch.sh            # downloads the public DICOM listed in seed/manifest.json
docker compose -p oncall-resident up -d --build
./seed/load.sh             # uploads them into the demo Orthanc
```

The app listens on `127.0.0.1:13000` and is published over HTTPS to the tailnet with `tailscale serve` (never Funnel). See `demo/README.md`.

## Security scanning

`scripts/install-hooks.sh` installs pre-commit and commit-msg hooks. They run gitleaks, PHI patterns and a denylist kept **outside** the repo (`~/.config/oncall-resident/denylist.txt`; in CI, the `DENYLIST` secret). Denylist terms without a dot match as whole words, case-insensitive; domains match as substrings. Only `file:line: término de la denylist` is ever printed. CI runs the same checks plus `scripts/test-denylist.sh`.

## License

AGPL-3.0 — see [LICENSE](LICENSE). Commercial licensing: [COMMERCIAL.md](COMMERCIAL.md).
