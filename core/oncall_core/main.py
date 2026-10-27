import asyncio
import os
from typing import Literal

from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from adapters.base import SourceUnavailable, StudySource
from adapters.orthanc import OrthancQido

from . import agent
from .basic import basic_answer
from .cases import load_cases
from .i18n import t
from .llm import LLM, Provider, Warmth, providers_from_env
from .reports import QcContext, ReportError, Reports
from .service import Service
from .store import Store
from .tools import REPORT_TEXT_MAX, Toolbox, untrusted
from .views import item_view

Lang = Literal["es", "en"]


class ChatIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    lang: Lang = "es"
    case_id: str | None = Field(default=None, max_length=100)  # case open on screen, if any


class ReportEdit(BaseModel):
    version: int
    technique: str | None = Field(default=None, max_length=4000)
    findings: str | None = Field(default=None, max_length=8000)
    impression: str | None = Field(default=None, max_length=4000)


class Dismiss(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


class Sign(BaseModel):
    version: int


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
    by_case = {m.case_id: m for m in cases.values()}
    reports = Reports(store, QcContext(llm, providers, float(env.get("QC_TIMEOUT", "40")), float(env.get("QC_BUDGET", "45"))),
                      indication_for=lambda cid, lg: by_case[cid].reason[lg] if cid in by_case else "")
    seed_file = env.get("REPORTS_SEED", "../demo/seed/reports.json")
    if os.path.exists(seed_file):
        reports.seed(seed_file)
    app.state.reports = reports

    def who(login: str | None) -> str:
        return (login or "").strip().lower()

    def report_error(e: ReportError):
        raise HTTPException(e.code, e.message)

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
        """Tool calls and reads. Model, tokens and cost are only included with ?detail=1 (the app passes it for admins)."""
        items = store.recent(100)
        if not detail:
            for i in items:
                for k in ("model", "tokens_in", "tokens_out", "cost_usd"):
                    i.pop(k, None)
                if i["kind"] == "llm":
                    i["output"] = None  # token counts are admin detail too
        return {"items": items}

    @app.post("/api/chat")
    async def chat(body: ChatIn, x_resident_login: str | None = Header(default=None)):
        lang = body.lang
        toolbox = Toolbox(service, lang, reports)
        context = ""
        try:
            found = await service.find(body.case_id) if body.case_id else None
        except SourceUnavailable:
            raise HTTPException(503, t(lang, "pacs.down"))
        if found:
            cid = found[0].case_id
            st = reports.state(cid)
            context = t(lang, "ctx.case", case=cid)
            if st:
                u = lambda x: untrusted(x, REPORT_TEXT_MAX)
                context += " " + t(lang, "ctx.report", v=st["version"], status=st["status"], technique=u(st["technique"]),
                                   findings=u(st["findings"]), impression=u(st["impression"]))
        timeouts = {}
        if primary:
            timeouts[primary.name] = warm_timeout if warmth.is_warm() else cold_threshold
            ensure_waking()  # a cold model keeps loading in the background even if this answer falls back
        for p in providers:
            timeouts.setdefault(p.name, fallback_timeout)
        try:
            a = await agent.answer(llm, providers, timeouts, body.text, lang, toolbox, store,
                                   lambda text, lg: basic_answer(service, store, text, lg),
                                   budget_s=answer_budget, context=context)
        except SourceUnavailable:
            store.log("chat", "answer", output="PACS unavailable", ok=False)
            raise HTTPException(503, t(lang, "pacs.down"))
        if primary and a.mode == "agent":
            warmth.mark_ok()
        store.log("chat", "answer", output=a.text[:200], model=a.model, mode=a.mode,
                  input={"steps": a.steps})
        return {"text": a.text, "blocks": a.blocks, "steps": a.steps, "mode": a.mode}

    @app.get("/api/reports/{case_id}")
    async def get_report(case_id: str):
        st = reports.state(case_id)
        if not st:
            raise HTTPException(404, "No draft")
        return st

    @app.put("/api/reports/{case_id}")
    async def put_report(case_id: str, body: ReportEdit, lang: Lang = "es", x_resident_login: str | None = Header(default=None)):
        try:
            return await reports.replace_text(case_id, body.version, body.model_dump(exclude={"version"}), who(x_resident_login) or "ui", lang)
        except ReportError as e:
            report_error(e)

    @app.post("/api/reports/{case_id}/qc/{item_id}/apply")
    async def apply_fix(case_id: str, item_id: int, lang: Lang = "es", x_resident_login: str | None = Header(default=None)):
        try:
            st, diff = await reports.apply_fix(case_id, item_id, who(x_resident_login) or "ui", lang)
            return st | {"diff": diff}
        except ReportError as e:
            report_error(e)

    @app.post("/api/reports/{case_id}/qc/{item_id}/dismiss")
    async def dismiss(case_id: str, item_id: int, body: Dismiss, x_resident_login: str | None = Header(default=None)):
        try:
            return reports.dismiss(case_id, item_id, body.reason, who(x_resident_login) or "ui")
        except ReportError as e:
            report_error(e)

    @app.post("/api/reports/{case_id}/sign")
    async def sign(case_id: str, body: Sign, x_resident_login: str | None = Header(default=None)):
        """The only way to sign: the human 'Firmar' tap, with the tailnet identity forwarded by the app."""
        try:
            return reports.sign(case_id, body.version, who(x_resident_login))
        except ReportError as e:
            report_error(e)

    @app.post("/api/demo/reset-reports")
    async def reset_reports(x_resident_admin: str | None = Header(default=None)):
        """Demo only (DEMO_RESET_ENABLED=1, admins): reload the synthetic drafts so the QC demo can be replayed."""
        if env.get("DEMO_RESET_ENABLED") != "1" or x_resident_admin != "1" or not os.path.exists(seed_file):
            raise HTTPException(403, "Demo reset disabled")
        reports.reset_demo(seed_file)
        store.log("view", "demo_reset", output="synthetic drafts reloaded")
        return {"ok": True}

    @app.get("/api/spend")
    async def spend(x_resident_admin: str | None = Header(default=None)):
        if x_resident_admin != "1":
            raise HTTPException(403, "Admins only")
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        return {"since": today, **store.spend(today)}

    return app


app = create_app() if os.environ.get("ONCALL_NO_APP") != "1" else None
