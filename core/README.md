# core

FastAPI orchestrator. **Day 1: no LLM.** It does rule-based intent matching over a fixed set of intents (pending studies, why is it first, open case) and joins Orthanc QIDO-RS studies with the synthetic metadata in `demo/seed/cases.json`.

```sh
uv sync && uv run pytest
PYTHONPATH=.. DICOMWEB_URL=http://127.0.0.1:18042/dicom-web uv run uvicorn oncall_core.main:app --port 18000
```

| Endpoint | |
|---|---|
| `GET /api/health` | core, PACS reachability, `llm: none` |
| `GET /api/worklist?lang=es|en` | sorted: technologist critical flag, then order priority, then wait |
| `GET /api/cases/{id}` | reason for exam, technologist note, priors (declared vs. found in PACS) |
| `POST /api/chat` | `{text, lang}` → `{intent, text, blocks}` |
| `GET /api/activity` | in-memory log of what was queried and opened |

## Known gaps (day 1)

- **No authentication.** The demo binds the app only to the Tailscale IP and core/Orthanc only to loopback/internal networks, and the data is synthetic and public. Auth is required before any non-demo data.
