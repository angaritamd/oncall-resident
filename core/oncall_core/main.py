import os
from collections import deque
from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from adapters.base import SourceUnavailable, StudySource
from adapters.orthanc import OrthancQido

from . import intents
from .cases import load_cases
from .i18n import t
from .views import case_view, item_view
from .worklist import WorkItem, build_worklist

Lang = Literal["es", "en"]


class ChatIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    lang: Lang = "es"


def create_app(source: StudySource | None = None, cases_file: str | None = None) -> FastAPI:
    app = FastAPI(title="oncall-resident core", version="0.1.0")
    src = source or OrthancQido(os.environ.get("DICOMWEB_URL", "http://127.0.0.1:18042/dicom-web"))
    cases = load_cases(cases_file or os.environ.get("CASES_FILE", "../demo/seed/cases.json"))
    activity: deque[dict] = deque(maxlen=100)

    def log(kind: str, case_id: str | None = None, ok: bool = True):
        activity.appendleft({"at": datetime.now(timezone.utc).isoformat(), "kind": kind, "case_id": case_id, "ok": ok})

    async def worklist() -> tuple[list[WorkItem], datetime]:
        now = datetime.now(timezone.utc)
        return await build_worklist(src, cases, now), now

    async def find(case_id: str) -> tuple[WorkItem, int, datetime] | None:
        items, now = await worklist()
        for i, it in enumerate(items, 1):
            if it.case_id.lower() == case_id.lower():
                return it, i, now
        return None

    async def open_case(case_id: str, lang: str) -> dict | None:
        found = await find(case_id)
        if not found:
            return None
        it, pos, now = found
        others = await src.studies_for_patient(it.study.patient_id)
        priors = None if others is None else len([s for s in others if s.study_uid != it.study.study_uid])
        return case_view(it, lang, now, pos, priors)

    @app.get("/api/health")
    async def health():
        return {"core": "ok", "pacs": "ok" if await src.ping() else "down", "llm": "none"}

    @app.get("/api/worklist")
    async def get_worklist(lang: Lang = "es"):
        try:
            items, now = await worklist()
        except SourceUnavailable:
            log("worklist", ok=False)
            raise HTTPException(503, t(lang, "pacs.down"))
        log("worklist")
        return {"items": [item_view(it, lang, now, i) for i, it in enumerate(items, 1)]}

    @app.get("/api/cases/{case_id}")
    async def get_case(case_id: str, lang: Lang = "es"):
        try:
            view = await open_case(case_id, lang)
        except SourceUnavailable:
            log("open", case_id, ok=False)
            raise HTTPException(503, t(lang, "pacs.down"))
        if not view:
            raise HTTPException(404, t(lang, "case.missing", case=case_id))
        log("open", view["case_id"])
        return view

    @app.get("/api/activity")
    async def get_activity():
        return {"items": list(activity)}

    @app.post("/api/chat")
    async def chat(body: ChatIn):
        lang = body.lang
        intent, case_id = intents.match(body.text)
        try:
            if intent == "worklist":
                items, now = await worklist()
                log("worklist")
                if not items:
                    return {"intent": intent, "text": t(lang, "wl.empty"), "blocks": []}
                views = [item_view(it, lang, now, i) for i, it in enumerate(items, 1)]
                c = sum(v["critical"] for v in views)
                crit = t(lang, "wl.crit_some", c=c) if c else t(lang, "wl.crit_none")
                key = "wl.summary_one" if len(views) == 1 else "wl.summary"
                text = f"{t(lang, key, n=len(views), crit=crit)} {t(lang, 'wl.next', case=views[0]['case_id'])}"
                return {"intent": intent, "text": text,
                        "blocks": [{"type": "next_study", "item": views[0], "total": len(views)},
                                   {"type": "study_list", "items": views}]}
            if intent == "why":
                items, now = await worklist()
                if not items:
                    return {"intent": intent, "text": t(lang, "wl.empty"), "blocks": []}
                target = next((it for it in items if case_id and it.case_id == case_id), items[0])
                m = target.meta
                if m and m.tech_critical:
                    text = t(lang, "why.critical", case=target.case_id)
                elif m and target is items[0] and len(items) > 1 and items[1].meta and items[1].meta.priority == m.priority:
                    text = t(lang, "why.wait", case=target.case_id, m=target.wait_minutes(now))
                else:
                    p = t(lang, f"priority.{m.priority}") if m else t(lang, "priority.unknown")
                    text = t(lang, "why.priority", case=target.case_id, p=p)
                log("why", target.case_id)
                pos = items.index(target) + 1
                return {"intent": intent, "text": f"{text} {t(lang, 'why.rule')}",
                        "blocks": [{"type": "evidence", "item": item_view(target, lang, now, pos)}]}
            if intent == "open":
                if not case_id:
                    return {"intent": intent, "text": t(lang, "case.which"), "blocks": []}
                view = await open_case(case_id, lang)
                if not view:
                    return {"intent": intent, "text": t(lang, "case.missing", case=case_id), "blocks": []}
                log("open", view["case_id"])
                if view["critical"]:
                    why = t(lang, "case.why_critical")
                elif view["priority"]:
                    why = t(lang, "case.why_priority", p=t(lang, f"priority.{view['priority']}"))
                else:
                    why = t(lang, "case.why_none")
                n = view["priors_in_pacs"]
                priors = t(lang, "case.priors_unknown") if n is None else t(lang, "case.priors_0") if n == 0 else t(lang, "case.priors_n", n=n)
                return {"intent": intent, "text": t(lang, "case.open", case=view["case_id"], why=why, priors=priors),
                        "blocks": [{"type": "case", "case": view}]}
        except SourceUnavailable:
            log(intent, case_id, ok=False)
            raise HTTPException(503, t(lang, "pacs.down"))
        return {"intent": "help", "text": t(lang, "help"), "blocks": []}

    return app


app = create_app() if os.environ.get("ONCALL_NO_APP") != "1" else None
