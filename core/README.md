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

## Known gaps (day 1)

- **No authentication.** The demo binds the app only to the Tailscale IP and core/Orthanc only to loopback/internal networks, and the data is synthetic and public. Auth is required before any non-demo data.
