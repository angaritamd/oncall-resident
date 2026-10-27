import asyncio
import os
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from adapters.base import SourceUnavailable, StudySource
from adapters.orthanc import OrthancQido

from . import agent
from .basic import basic_answer
from .cases import load_cases
from .i18n import t
from .llm import LLM, Provider, Warmth, providers_from_env
from .service import Service
from .store import Store
from .tools import Toolbox
from .views import item_view

Lang = Literal["es", "en"]


class ChatIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    lang: Lang = "es"


def create_app(
    source: StudySource | None = None,
    cases_file: str | None = None,
    store: Store | None = None,
    providers: list[Provider] | None = None,
    llm: LLM | None = None,
    env=os.environ,
) -> FastAPI:
    app = FastAPI(title="oncall-resident core", version="0.2.0")
    user, password = env.get("DICOMWEB_USER"), env.get("DICOMWEB_PASSWORD")
    src = source or OrthancQido(
        env.get("DICOMWEB_URL", "http://127.0.0.1:18042/dicom-web"),
        auth=(user, password) if user and password else None,
    )
    store = store or Store(env.get("STATE_DB", "./state/oncall.db"))
    cases = load_cases(cases_file or env.get("CASES_FILE", "../demo/seed/cases.json"), arrival=store.arrival)
    service = Service(src, cases)
    providers = providers if providers is not None else providers_from_env(env)
    llm = llm or LLM()
    primary = providers[0] if providers and providers[0].mode == "agent" else None
    warmth = Warmth(float(env.get("GLIMMER_SCALEDOWN_SECONDS", "300")))
    cold_threshold = float(env.get("GLIMMER_COLD_THRESHOLD", "20"))
    warm_timeout = float(env.get("GLIMMER_TIMEOUT", "90"))
    fallback_timeout = float(env.get("FALLBACK_TIMEOUT", "45"))
    # whole-answer budget; must stay below the app proxy's 120 s chat timeout
    answer_budget = float(env.get("ANSWER_BUDGET_SECONDS", "100"))
    app.state.wake_task = None

    async def wake():
        warmth.waking = True
        try:
            # a cold scale-to-zero container answers once the model is loaded
            if await llm.ping(primary, timeout=float(env.get("GLIMMER_WAKE_TIMEOUT", "900"))):
                warmth.mark_ok()
            else:
                warmth.mark_failed()  # bad key, stopped app (404), outage: report it, retry after a cooldown
        finally:
            warmth.waking = False

    def ensure_waking():
        if primary and not warmth.is_warm() and not warmth.waking and not warmth.recently_failed():
            app.state.wake_task = asyncio.get_running_loop().create_task(wake())

    def resident_state() -> str:
        if not providers:
            return "basic"
        if not primary:
            return "ready"
        if warmth.is_warm():
            return "ready"
        return "unavailable" if warmth.recently_failed() and not warmth.waking else "waking"

    @app.get("/api/health")
    async def health():
        return {"core": "ok", "pacs": "ok" if await src.ping() else "down", "resident": resident_state()}

    @app.get("/api/resident")
    async def resident():
        """Wakes the scale-to-zero model in the background; the UI polls this while it says 'waking'."""
        ensure_waking()
        return {"state": resident_state()}

    @app.get("/api/worklist")
    async def get_worklist(lang: Lang = "es"):
        try:
            items, now = await service.worklist()
        except SourceUnavailable:
            store.log("view", "worklist", ok=False)
            raise HTTPException(503, t(lang, "pacs.down"))
        store.log("view", "worklist", output=t(lang, "tool.list_summary", n=len(items), first=items[0].case_id if items else "—"))
        return {"items": [item_view(it, lang, now, i) for i, it in enumerate(items, 1)]}

    @app.get("/api/cases/{case_id}")
    async def get_case(case_id: str, lang: Lang = "es"):
        try:
            view = await service.open_case(case_id, lang)
        except SourceUnavailable:
            store.log("view", "case", case_id=case_id, ok=False)
            raise HTTPException(503, t(lang, "pacs.down"))
        if not view:
            raise HTTPException(404, t(lang, "case.missing", case=case_id))
        store.log("view", "case", case_id=view["case_id"], output=view["exam"] or "")
        return view

    @app.get("/api/activity")
    async def get_activity(detail: bool = False):
        """Tool calls and reads. The exact model is only included with ?detail=1 (the app passes it for admins)."""
        items = store.recent(100)
        if not detail:
            for i in items:
                i.pop("model", None)
        return {"items": items}

    @app.post("/api/chat")
    async def chat(body: ChatIn):
        lang = body.lang
        toolbox = Toolbox(service, lang)
        timeouts = {}
        if primary:
            timeouts[primary.name] = warm_timeout if warmth.is_warm() else cold_threshold
            ensure_waking()  # a cold model keeps loading in the background even if this answer falls back
        for p in providers:
            timeouts.setdefault(p.name, fallback_timeout)
        try:
            a = await agent.answer(llm, providers, timeouts, body.text, lang, toolbox, store,
                                   lambda text, lg: basic_answer(service, store, text, lg),
                                   budget_s=answer_budget)
        except SourceUnavailable:
            store.log("chat", "answer", output="PACS unavailable", ok=False)
            raise HTTPException(503, t(lang, "pacs.down"))
        if primary and a.mode == "agent":
            warmth.mark_ok()
        store.log("chat", "answer", output=a.text[:200], model=a.model, mode=a.mode,
                  input={"steps": a.steps})
        return {"text": a.text, "blocks": a.blocks, "steps": a.steps, "mode": a.mode}

    return app


app = create_app() if os.environ.get("ONCALL_NO_APP") != "1" else None
