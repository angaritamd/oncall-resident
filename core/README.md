# core

FastAPI orchestrator. It joins Orthanc QIDO-RS studies with the synthetic order metadata in `demo/seed/cases.json`, and answers chat through a tool-using model:

- **Provider chain** (`llm.py`, configured from the environment):
  1. `GLIMMER_BASE_URL` + `GLIMMER_API_KEY` (serving/);
  2. `MODEL_API_KEY`: Meta Model API, `muse-spark-1.3`;
  3. basic rule mode (`basic.py`).
- **Cold starts:** while the scale-to-zero model is cold, chat waits at most `GLIMMER_COLD_THRESHOLD` seconds (default 20) and then falls back. The model keeps loading in the background, and `GET /api/resident` reports `waking` / `ready`.
- **Tools** (`tools.py`): `list_pending` and `summarize_case`. They are read-only, return only PACS and order data, and give every missing value as "Sin dato".
- **Verifiable agent** (`agent.py`, `store.py`): every tool call is stored in SQLite (`STATE_DB`) with time, tool, input, short output, study ID, model and mode. Arrival times persist there too.

```sh
uv sync && uv run pytest
PYTHONPATH=.. DICOMWEB_URL=http://127.0.0.1:18042/dicom-web uv run uvicorn oncall_core.main:app --port 18000
```

| Endpoint | |
|---|---|
| `GET /api/health` | core, PACS reachability, `llm: none` |
| `GET /api/worklist?lang=es|en` | sorted: technologist critical flag, then order priority, then wait |
| `GET /api/cases/{id}` | reason for exam, technologist note, priors (declared vs. found in PACS) |
| `POST /api/chat` | `{text, lang}` → `{text, blocks, steps, mode}` |
| `GET /api/activity` | persistent log of tool calls, reads and answers (`?detail=1` adds the model; the app only passes it for `ADMIN_USERS`) |
| `GET /api/resident` | wakes the primary model; `ready` / `waking` / `basic` |
| `POST /api/review` | starts (or resumes) the shift review; returns the `run_id` immediately, the run advances in the background |
| `GET /api/review/{run_id}` | progress `done/total`, status and studies in display order (polled by the card) |
| `POST /api/review/{run_id}/resume` | resumes a `paused` run |

## Shift review (`review.py`)

Agentic, verifiable loop over the pending studies in `list_pending` order. It never edits, signs, or sends anything.

- **Checklist, fixed in code:** `C1` draft (no draft → `skipped`/`sin_borrador`, no model), `C2` critical (only with technologist flag: does the IMPRESSION answer the suspicion?), `C3` indication (always), `C4` mechanical (`Reports.run_qc`, rules + model, runs in code before the model loop), `C5` counter-evidence (only with open C4 alerts).
- **Loop tools** (only these): `qc_check` replays the C4 result already computed (never re-runs QC), `record_finding(case_id, item, section, quote, claim)` with `section ∈ {indication, tech_note, findings, impression}`, `close_study(case_id, verdict, note)` with `verdict ∈ {ok, revisar, critico_sin_respuesta}`. Max 4 model steps per study.
- **Rejections (audited):** `record_finding` is rejected when the item is outside the study checklist or the quote is not literally in that section; `close_study` is rejected while C4 alerts are open without a `C5` finding or an explicit no-counter-evidence note. `sin_borrador` and `no_evaluado` are code-only verdicts.
- **Fallback:** no model answer or study budget spent → `mode = "rules"`, C2/C3/C5 "No evaluado", verdict `revisar` with alerts, else `no_evaluado`. A verdict is never invented.
- **Resume:** progress is saved after every study; `paused` runs resume unfinished studies only, with zero model calls when nothing is left. One active run at a time. Budgets from the environment: `REVIEW_RUN_BUDGET_S` (default 600), `REVIEW_STUDY_BUDGET_S` (default 120), `REVIEW_CALL_TIMEOUT_S` (default 40). The run budget restarts at every resume (`resumed_at`), so "Continuar" always reviews more instead of pausing again. A restart marks `running` runs `paused`.
- **Audit:** every call, including rejections, goes to `Store.log(kind="review", …)` with the `run_id`.

## Known gaps (day 1)

- **No authentication.** The demo binds the app only to the Tailscale IP and core/Orthanc only to loopback/internal networks, and the data is synthetic and public. Auth is required before any non-demo data.
