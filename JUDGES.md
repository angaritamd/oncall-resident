# oncall-resident — for the judges

An AI on-call radiology resident in a mobile chat app. It prepares and discusses studies, checks drafts with RAD·QC,
and leaves the decision and the signature to the radiologist.

> **Workflow tool, not a medical device. The radiologist decides and signs.**
> Public DICOM (LIDC-IDRI) and synthetic clinical metadata only. No real patients.

## What was built during the hackathon (Oct 26 after kickoff – Nov 4)

Every line in this repository: 190 commits (not counting merges) across all branches, each tagged with its Linear issue. The table counts commits per issue on all branches.

| Area | Issue | Commits | Key commits |
|---|---|---|---|
| Repo gate: license, data sources, secret/PHI scanner, FastAPI core, Orthanc DICOMweb adapter | ANG-170 | 49 | `c53602e` (gate), `b9e5802` (core + QIDO adapter) |
| Muse Glimmer served by us on Modal (vLLM, Bearer proxy, scale to zero) and the tool-using orchestrator | ANG-171 | 17 | `3f741b4` → `08d9095` |
| Draft, edit, RAD·QC and two-tap human signature | ANG-172 | 12 | `8641168` → `ec09b6d` |
| Reading-station sync (OHIF viewer follows the phone) | ANG-177 | 8 | `9361a67` → `55e4fe5` |
| Reading order, reading flow, voice, pending items, latency | ANG-173 | 42 | `e2db041` (#7), `7c7096e` (#8 voice), `c025a62` (#9), `60c48a0` (#11 latency) |
| Batch review of the shift | ANG-175 | 8 | `7cd4c8d` → `09126c6` |
| Training data lane: 697 synthetic cases for v5 from Muse Spark Open (generation, review, batches), built with Muse Code | ANG-178 | 35 | `a8a0acf` → `32b891c` (final dataset) |
| RAD·QC v5: taxonomy, data rules, benchmark, LoRA training and serving, Meta backup for QC | ANG-174 | 38 | `810c3ed` (baseline), `701fb8c` (CUDA graphs), `02296c8` (2500 tokens), `c22b1fb` (training manifest), `2594b3a` (LoRA serving fix), `14c865b` (QC backup + "AI review unavailable") |
| Live access for the judges: Glimmer on demand | ANG-176 | 1 | `8670ca8` |

Day-by-day detail, measurements and spend are in [BUILD_LOG.md](BUILD_LOG.md).

## What existed before (not in this repo, no code copied)

| Pre-existing | Used how |
|---|---|
| RadMesh, a private RIS/PACS | Only as a design reference. Here it is an empty adapter stub (`adapters/radmesh`). |
| An earlier Glimmer-on-Modal prototype (Oct 21–26) | Not copied. `serving/` was written from scratch on Oct 27. |
| RAD·QC v3/v4 pilot and RadMesh's v4 training script | v5's training recipe (QLoRA, rank 16) follows the same approach. The code was rewritten here with v5's data rules. |
| AI Mode prototype inside the RIS (Oct 24–25), UI mockup (Oct 26) | Visual concept only |

## Meta models and tools

| Model / tool | Where it runs | What it does |
|---|---|---|
| **Muse Glimmer** (open weights, Apache-2.0), FP8 | Served by us: vLLM on one Modal H100, `serving/glimmer_app.py` | The resident: chat with tools (open case, propose, edit, pending items). It is also the base model for RAD·QC. |
| **RAD·QC v5**, our LoRA adapter on Muse Glimmer (rank 16, trained on Modal) | Served by us on the same vLLM server, model `radqc-v5`, CUDA graphs, text only | Checks every new draft version for omitted findings, an unanswered clinical question and a critical study that needs a second look (`doble_chequeo`). Measurements and laterality are covered by code rules. |
| **Muse Spark Open** (`meta-models/muse-spark-open-1026`) | Baseten (partner inference) | Generated the 697 synthetic training cases for v5. Training data comes only from open-weight models; outputs of the Meta Model API are never used for training. |
| **Muse Wonder** | Meta | Generated bench-v2, the 66-case benchmark. The benchmark is used only for evaluation, never for training. |
| **Muse Code** | Meta (coding agent) | The agent that built the ANG-178 training-data lane: generation, review and the batches of cases. |
| **Muse Spark 1.3** via the Meta Model API | Meta | Backup for the chat and for RAD·QC when Glimmer is down or cold. Synthetic data only, hard spend cap (`META_API_MAX_USD`). |
| **Muse Voice Transcribe 1.0** via the Meta Model API | Meta | Dictation: the phone records WAV, the core transcribes it, and the transcript becomes a chat instruction. Voice never signs. |

## Results: RAD·QC v5 vs base Glimmer (bench-v2, 66 cases)

Both were measured on the same server: Glimmer FP8 on an H100, vLLM with CUDA graphs, QC `max_tokens` 2500,
temperature 0.6, 3 passes, no Meta backup. Each cell is the mean number of correct cases (range).

| Subtype | n | Base, full system | **v5, full system** | Base, Glimmer only | **v5, Glimmer only** |
|---|---|---|---|---|---|
| omitted finding | 10 | 10.0 | 9.0 | 10.0 | 9.0 |
| unanswered clinical question | 9 | 5.0 | **8.67** | 5.0 | **8.67** |
| second look (`doble_chequeo`) | 8 | 5.33 | 5.33 | 5.33 | 5.33 |
| laterality (rules) | 8 | 8.0 | 8.0 | – | – |
| measurement (rules) | 8 | 8.0 | 8.0 | – | – |
| controls (correct reports) | 23 | 17.33 | **23.0** | 17.33 | **23.0** |
| **Total** | 66 / 50 | 53.67 (53–54) | **62.0 (61–63)** | 37.67 (37–38) | **46.0 (45–47)** |

| | Base | v5 |
|---|---|---|
| Answers cut at 2500 tokens | 3 of 198 | 0 of 198 |
| Time per check, median / max | ~14 s / 33 s | 1.35 s / 2.6 s |

**Limitations**
- **Second look (`doble_chequeo`) stays at 5.33 of 8.** v5 did not improve it over the base model. Three of the eight
  critical studies reported with a normal template still get no "verify" prompt. This is the case the demo must not
  hide: when the checker is silent on a critical study, the radiologist still reads it.
- v5 misses one omitted finding in all 3 passes (B6-0033): an intrauterine device lying outside the pelvis, an
  incidental finding unrelated to the clinical question, in an otherwise normal abdominal X-ray.
- bench-v2 is a synthetic benchmark of 66 cases. These are not clinical validation numbers.

## Live access

The demo is not public. Judges get access on request:

1. Ask us, through the contact on the submission page, with the email you use for Tailscale.
2. We share the demo machine with you through a Tailscale invitation and add your login to the allowlist.
3. Install Tailscale, accept the invitation and open the HTTPS address in the invitation. Nothing else is exposed.

The first request after 25 minutes without use wakes Glimmer, which takes about 2.5 minutes. While it wakes, the chat
and RAD·QC answer through the Meta backup. If Glimmer and the backup both fail, the app says "Revisión IA no
disponible" instead of showing a clean check.

A recorded walkthrough of the same flow is the backup if live access is not possible.

## Run it

See `demo/README.md`. The demo is published to a tailnet with `tailscale serve` and asks for a tailnet identity on
the allowlist.
