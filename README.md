# oncall-resident

An AI on-call radiology resident as a mobile chat app, independent of any RIS and connected through open standards (DICOMweb).

> **Workflow tool, not a medical device. The radiologist decides and signs.**

## Status

Day 2. The resident is a tool-using model that **prepares and discusses** studies and never diagnoses or signs. It runs [Muse Glimmer](https://dev.meta.ai/resources/blog/build-with-muse-glimmer) (Meta, open weights, Apache-2.0), served from `serving/` on Modal with scale-to-zero. Backup chain:
1. Muse Spark through the Meta Model API, with synthetic data only.
2. The day-1 rule answers, labelled "Modo básico".

Every tool call is logged and shown in Actividad. See [BUILD_LOG.md](BUILD_LOG.md).

Day 4:
- **Reading order:** one rule in code (technologist critical > STAT > urgente > rutina > oldest > study ID). The model may comment on it, never change it.
- **Reading flow:** open a case → "¿Lo leemos con IA?" → a template proposal marked "Propuesta · verificar" → "de acuerdo" or dictated changes → RAD·QC → human signature in two taps → back to the list with the next study.
- **Voice:** see below.
- **Pending items:** a per-study list for after the reading.

## Layout

| Path | What |
|---|---|
| `app/` | Next.js (App Router, TypeScript, Tailwind) mobile-first PWA |
| `core/` | Python FastAPI orchestrator (no LLM today) |
| `adapters/` | `orthanc` (DICOMweb QIDO-RS, working) · `radmesh` (empty interface stub) |
| `demo/` | docker compose: Orthanc + core + app, seed scripts and synthetic metadata |
| `serving/` | Modal app `oncall-resident-glimmer`: vLLM (OpenAI-compatible) behind a Bearer-auth proxy on every route |
| `radqc/` | README only: what comes later |
| `scripts/` | secret / denylist / PHI scanner used by the git hook and CI |

## Provenance

| Built during the hackathon (Oct 26 after kickoff – Nov 4) | Pre-existing (not in this repo) |
|---|---|
| Everything in this repository: app, core (orchestrator, tools, activity log), adapters, demo, scanners, docs | RadMesh: private RIS/PACS |
| `serving/`: a new Modal app for Muse Glimmer, written from scratch on Oct 27 | Earlier prototype serving Glimmer on Modal (Oct 21–26), not copied |
| | AI Mode prototype inside the RIS (Oct 24–25) |
| | RAD·QC v3 and v4 pilot |
| | UI mockup (Oct 26, visual concept only) |

No code from pre-existing projects is copied or imported here. The Muse Glimmer weights are Meta's (Apache-2.0) and are downloaded at deploy time, not stored in this repo.

## Voice

The composer's microphone records WAV on the phone (mono PCM16, 16 kHz), the core transcribes it, and the
transcript runs as a chat instruction. Voice never signs: signing has no chat path, and "fírmalo" gets a refusal.
Short commands are answered in code: «¿qué tengo pendiente?», «abre el siguiente», «revisa», «de acuerdo».
Dictation such as «el nódulo mide 12 mm» goes to the resident. Spoken answers use the browser's own speech
synthesis, with a visible mute button.

`TRANSCRIBE_PROVIDER` selects the engine:

| Value | Engine | When |
|---|---|---|
| `meta` (default) | Muse Voice Transcribe (`muse-voice-transcribe-1.0`) on the Meta Model API, `POST /v1/asr/transcribe` | Synthetic data only. Like the text backup, it runs only with `DATA_CLASSIFICATION=synthetic` and a `cases.json` marked synthetic. The key is `MODEL_API_KEY` in `.env`, never printed. |
| `local` | Whisper on the hospital node (`WHISPER_URL`) | Real data. The audio of a real dictation can carry patient details, so it must never leave the node. Today only the interface exists: the endpoint answers 503 "no configurada". |

Neither the audio nor the transcript is stored. Actividad keeps duration, latency and cost only. Tests use three
synthetic TTS clips (`app/e2e/audio`), never real voices.

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
