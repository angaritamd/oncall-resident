import asyncio
import os
import time
from typing import Literal

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from adapters.base import SourceUnavailable, StudySource
from adapters.orthanc import OrthancQido

from . import agent, commands, templates
from .bench import Bench
from .basic import basic_answer
from .cases import load_cases
from .i18n import t
from .llm import LLM, MetaCap, Provider, Warmth, providers_from_env
from .pending import KINDS, Pending, is_tomorrow_query, request_kind
from .reports import QcContext, ReportError, Reports
from .service import Service
from .station import StationError, Stations
from .store import Store
from .transcribe import MAX_BYTES, Transcriber, TranscribeError, transcriber_from_env
from .tools import REPORT_TEXT_MAX, Toolbox, qc_tail, untrusted
from .views import item_view, next_reason

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


class LinkIn(BaseModel):
    code: str = Field(pattern=r"^\d{4}$")


class VerdictIn(BaseModel):
    verdict: Literal["valid", "invalid"]
    note: str | None = Field(default=None, max_length=500)


class OpenIn(BaseModel):
    case_id: str = Field(min_length=1, max_length=100)


def create_app(
    source: StudySource | None = None,
    cases_file: str | None = None,
    store: Store | None = None,
    providers: list[Provider] | None = None,
    llm: LLM | None = None,
    env=os.environ,
    transcriber: Transcriber | None = None,
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
    meta_cap = MetaCap.from_env(store, env)  # META_API_MAX_USD: no Meta call starts once the spend reaches it
    reports = Reports(store, QcContext(llm, providers, float(env.get("QC_TIMEOUT", "40")), float(env.get("QC_BUDGET", "45")),
                                       allow=meta_cap.allows),
                      indication_for=lambda cid, lg: by_case[cid].reason[lg] if cid in by_case else "",
                      background_qc=env.get("QC_BACKGROUND", "0") == "1")
    seed_file = env.get("REPORTS_SEED", "../demo/seed/reports.json")
    if os.path.exists(seed_file):
        reports.seed(seed_file)
    app.state.reports = reports
    service.signed = reports.signed  # signed studies leave the pending list
    pending = Pending(store)
    app.state.pending = pending
    bench = Bench(store, {"bench": env.get("BENCH_FILE", "../radqc/data/bench/pilot.jsonl"),
                          "train": env.get("BENCH_TRAIN_FILE", "")})
    shift_tz = ZoneInfo(env.get("SHIFT_TZ", "UTC"))
    stations = Stations()
    app.state.stations = stations

    def station_error(e: StationError):
        raise HTTPException(e.code, e.message)



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
        if not [p for p in providers if meta_cap.allows(p)]:
            return "basic"
        if not primary:
            return "ready"
        if warmth.is_warm():
            return "ready"
        return "unavailable" if warmth.recently_failed() and not warmth.waking else "waking"

    @app.get("/api/health")
    async def health():
        return {"core": "ok", "pacs": "ok" if await src.ping() else "down", "resident": resident_state()}

    keepalive_s = float(env.get("GLIMMER_KEEPALIVE_SECONDS", "120"))
    keep = {"inflight": False, "last_try": 0.0}

    async def keepalive():
        try:
            if await llm.ping(primary, timeout=30):
                warmth.mark_ok()
            else:
                warmth.mark_failed()
        finally:
            keep["inflight"] = False

    @app.get("/api/resident")
    async def resident(touch: bool = False):
        """Wakes the scale-to-zero model in the background; the UI polls this while it says 'waking'.
        `touch` (the radiologist is active: list, case, microphone) also renews a warm model with one light request
        (GET /models) when the last one is older than GLIMMER_KEEPALIVE_SECONDS, so it does not scale down while
        someone is reading. It never raises min_containers."""
        ensure_waking()
        now = time.monotonic()
        # one light request at a time, at most every keepalive_s (attempts count, not only successes)
        if touch and primary and warmth.is_warm() and not warmth.waking and not keep["inflight"] and \
                now - max(warmth.last_ok or 0, keep["last_try"]) > keepalive_s:
            keep["inflight"], keep["last_try"] = True, now
            app.state.keepalive_task = asyncio.get_running_loop().create_task(keepalive())
        return {"state": resident_state()}

    @app.get("/api/worklist")
    async def get_worklist(lang: Lang = "es"):
        try:
            items, now = await service.worklist()
        except SourceUnavailable:
            store.log("view", "worklist", ok=False)
            raise HTTPException(503, t(lang, "pacs.down"))
        store.log("view", "worklist", output=t(lang, "tool.list_summary", n=len(items), first=items[0].case_id if items else "—"))
        day = datetime.now(shift_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        signed, _ = await service.signed_since(day)
        return {"items": [item_view(it, lang, now, i) for i, it in enumerate(items, 1)],
                "signed_today": [item_view(it, lang, now, 0) | {"signed_at": at} for it, at in signed]}

    async def next_pending(lang: str, skip: str | None = None) -> dict | None:
        """The next study by the ordering rule, with the reason in words."""
        items, now = await service.worklist()
        for i, it in enumerate(items, 1):
            if it.case_id != skip:
                return {"item": item_view(it, lang, now, i), "why": next_reason(it, lang, now)}
        return None

    @app.get("/api/cases/{case_id}")
    async def get_case(case_id: str, lang: Lang = "es", x_resident_login: str | None = Header(default=None)):
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

    derived_at: dict[str, float] = {}
    exams: dict[str, dict[str, str | None]] = {}
    derive_locks: dict[str, asyncio.Lock] = {}

    async def pending_view(lang: str) -> list[dict]:
        """Lists the open items (labels in `lang`). Metadata items are derived at most once a minute per language
        (one prior lookup per study that declares priors), single-flight: concurrent requests wait for one run."""
        async with derive_locks.setdefault(lang, asyncio.Lock()):
            if time.monotonic() - derived_at.get(lang, -1e9) > 60:
                await derive_pending(lang)
                derived_at[lang] = time.monotonic()
        return [i | {"label": t(lang, f"pending.{i['kind']}"), "source_label": t(lang, f"pending.src.{i['source']}"),
                     "exam": exams.get(lang, {}).get(i["case_id"])} for i in pending.list()]

    async def derive_pending(lang: str) -> None:
        items, _ = await service.all_items()
        names: dict[str, str | None] = {}
        for it in items:
            m = it.meta
            names[it.case_id] = m.exam[lang] if m else None
            others = await service.source.studies_for_patient(it.study.patient_id) if m and m.priors_available else None
            in_pacs = None if others is None else len([s for s in others if s.study_uid != it.study.study_uid])
            reqs = [{"kind": r.get("kind"), "note": (r.get("note") or {}).get(lang)} for r in (m.tech_requests if m else ())]
            if m and m.priors_available and in_pacs == 0:
                reqs.append({"kind": "missing_priors", "note": t(lang, "pending.priors_note")})
            pending.derive(it.case_id, priors_declared=False, priors_in_pacs=None, requests=reqs)
        exams[lang] = names

    def tomorrow_text(items: list[dict], lang: str) -> str:
        if not items:
            return t(lang, "pending.none")
        by_case: dict[str, list[str]] = {}
        for i in items:
            by_case.setdefault(i["case_id"], []).append(i["label"])
        return t(lang, "pending.tomorrow", items="; ".join(f"{c} · {', '.join(k)}" for c, k in by_case.items()))

    @app.get("/api/pending")
    async def get_pending(lang: Lang = "es"):
        try:
            items = await pending_view(lang)
        except SourceUnavailable:
            raise HTTPException(503, t(lang, "pacs.down"))
        return {"items": items, "summary": tomorrow_text(items, lang)}

    @app.post("/api/pending/{item_id}/{action}")
    async def pending_status(item_id: int, action: Literal["done", "reopen"], x_resident_login: str | None = Header(default=None)):
        row = pending.set_status(item_id, "done" if action == "done" else "open")
        if not row:
            raise HTTPException(404, "No existe")
        store.log("view", f"pending_{action}", input={"item": item_id}, output=row["kind"], case_id=row["case_id"])
        return row

    def bench_admin(admin: str | None):
        # benchmark validation is the admin radiologist's (ADMIN_USERS); others get the same 404 as the proxy
        if admin != "1":
            raise HTTPException(404, "not found")

    @app.get("/api/bench")
    async def get_bench(set: Literal["bench", "train"] = "bench", x_resident_admin: str | None = Header(default=None)):
        bench_admin(x_resident_admin)
        return bench.view(set)

    @app.post("/api/bench/{case_id}")
    async def set_bench(case_id: str, body: VerdictIn, x_resident_login: str | None = Header(default=None),
                        x_resident_admin: str | None = Header(default=None)):
        bench_admin(x_resident_admin)
        by = who(x_resident_login)
        if not by:
            raise HTTPException(403, "Sin identidad")
        row = bench.set(case_id, body.verdict, (body.note or "").strip() or None, by)
        if not row:
            raise HTTPException(404, "No existe")
        store.log("view", "bench_verdict", input={"case": case_id}, output=body.verdict)
        return row

    async def command(name: str, lang: str, case_id: str | None, by: str) -> dict:
        """Reading-flow commands answered in code (fast, and the same with or without a model)."""
        def reply(text: str, blocks: list | None = None, step: str | None = None, cid: str | None = None) -> dict:
            if step:
                store.log("tool", step, input={"case_id": cid} if cid else {}, output=text[:160], case_id=cid, mode="command")
            return {"text": text, "blocks": blocks or [], "steps": [step] if step else [], "mode": "command"}

        if name == "sign":
            return reply(t(lang, "cmd.sign"), step="sign_refused", cid=case_id)
        if name == "tomorrow":
            items = await pending_view(lang)
            return reply(tomorrow_text(items, lang), [{"type": "pending_list", "items": items}], "list_pending_items")
        if name in KINDS:
            if not case_id:
                return reply(t(lang, "cmd.no_case"))
            pending.add(case_id, name, "radiologist", by=by or None)
            items = await pending_view(lang)
            return reply(t(lang, "pending.noted", case=case_id, kind=t(lang, f"pending.{name}")),
                         [{"type": "pending_list", "items": [i for i in items if i["case_id"] == case_id]}], "add_pending_item", case_id)
        if name == "next":
            nxt = await next_pending(lang, skip=case_id)
            if not nxt:
                return reply(t(lang, "next.none"), step="open_next")
            view = await service.open_case(nxt["item"]["case_id"], lang)
            return reply(nxt["why"], [{"type": "case", "case": view}], "open_next", view["case_id"])
        if not case_id:
            return reply(t(lang, "cmd.no_case"))
        if not reports.state(case_id):
            return reply(t(lang, "cmd.no_draft", case=case_id))
        try:
            if name == "accept":
                st = reports.accept(case_id, by)  # by: the tailnet login ("" is refused)
                tail = t(lang, "cmd.ready") if st["signable"] else t(lang, "cmd.alerts", n=st["open_alerts"]) if st["open_alerts"] else ""
                return reply(t(lang, "cmd.accepted", case=case_id) + tail, [{"type": "report", "report": st}], "accept_proposal", case_id)
            st = await reports.run_qc(case_id, lang)
            return reply(t(lang, "cmd.reviewed", case=case_id, n=st["open_alerts"]), [{"type": "report", "report": st}], "qc_check", case_id)
        except ReportError as e:
            return reply(e.message, step=f"{name}_rejected", cid=case_id)

    async def measure_in_code(case_id: str, measure: tuple[str, str, str], lang: str, login: str) -> dict | None:
        """«el nódulo mide 12 mm» applied in code when the change is unequivocal; None hands it to the model."""
        try:
            found = await service.find(case_id)
        except SourceUnavailable:
            raise HTTPException(503, t(lang, "pacs.down"))
        st = reports.state(found[0].case_id) if found else None
        if not st or st["status"] != "draft":
            return None
        change = commands.measurement_edit(st["findings"], *measure)
        if not change:
            return None
        cid = found[0].case_id
        if change[0] == change[1]:
            return {"text": f'{t(lang, "agent.no_change")} {t(lang, "measure.same", case=cid, value=f"{measure[1]} {measure[2]}")}',
                    "blocks": [], "steps": [], "mode": "command", "retry": False}
        if not login:
            raise HTTPException(403, "Editar un borrador requiere un usuario identificado")
        try:
            new, diff = await reports.edit(cid, "findings", change[0], change[1], login, lang)
        except ReportError as e:
            return {"text": f'{t(lang, "agent.no_change")} {e.message}', "blocks": [], "steps": [], "mode": "command", "retry": True}
        store.log("tool", "edit_report", input={"case_id": cid, "section": "findings"}, case_id=cid, mode="command",
                  output=t(lang, "report.edited", case=cid, v=new["version"], n=new["open_alerts"]))
        text = t(lang, "confirm.edited", case=cid, section=t(lang, "section.findings"), v=new["version"]) + qc_tail(new, lang)
        return {"text": text, "blocks": [{"type": "report", "report": new, "diff": diff}], "steps": ["edit_report"],
                "mode": "command", "retry": False}

    @app.post("/api/chat")
    async def chat(body: ChatIn, x_resident_login: str | None = Header(default=None)):
        lang = body.lang
        cmd = commands.match(body.text) or ("tomorrow" if is_tomorrow_query(body.text) else None) \
            or (request_kind(body.text) if body.case_id else None)
        dictated = commands.dictation(body.text) if body.case_id else None
        if dictated and not who(x_resident_login):
            raise HTTPException(403, "Dictar un borrador requiere un usuario identificado")
        if dictated:
            try:
                found = await service.find(body.case_id)
            except SourceUnavailable:
                raise HTTPException(503, t(lang, "pacs.down"))
            if found:
                it = found[0]
                findings, impression = dictated
                technique = (it.meta.exam[lang] + ".") if it.meta else t(lang, "none")
                try:
                    st = await reports.draft(it.case_id, technique, findings, impression or t(lang, "cmd.blank_impression"),
                                             who(x_resident_login), lang, dictated=True)
                except ReportError as e:
                    out = {"text": e.message, "blocks": [], "steps": [], "mode": "command"}
                else:
                    store.log("tool", "draft_report", input={"case_id": it.case_id}, case_id=it.case_id, mode="command",
                              output=t(lang, "report.drafted", case=it.case_id, v=st["version"], n=st["open_alerts"]))
                    out = {"text": t(lang, "cmd.drafted", case=it.case_id), "blocks": [{"type": "report", "report": st}],
                           "steps": ["draft_report"], "mode": "command"}
                store.log("chat", "answer", output=out["text"][:200], mode="command", input={"steps": out["steps"]})
                return out
        measure = commands.measurement(body.text) if body.case_id and not dictated else None
        if measure:
            out = await measure_in_code(body.case_id, measure, lang, who(x_resident_login))
            if out:
                store.log("chat", "answer", output=out["text"][:200], mode="command", input={"steps": out["steps"]})
                return out
            # ambiguous (no single sentence with that structure and one measurement): the resident decides
        if cmd:
            try:
                found = await service.find(body.case_id) if body.case_id else None
                out = await command(cmd, lang, found[0].case_id if found else None, who(x_resident_login))
            except SourceUnavailable:
                raise HTTPException(503, t(lang, "pacs.down"))
            store.log("chat", "answer", output=out["text"][:200], mode="command", input={"steps": out["steps"]})
            return out
        toolbox = Toolbox(service, lang, reports, by=who(x_resident_login) or "residente", pending=pending,
                          pending_list=lambda: pending_view(lang))
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
        live = [p for p in providers if meta_cap.allows(p)]  # past the Meta cap the fallback is skipped
        for p in live:
            timeouts.setdefault(p.name, fallback_timeout)
        try:
            a = await agent.answer(llm, live, timeouts, body.text, lang, toolbox, store,
                                   lambda text, lg: basic_answer(service, store, text, lg),
                                   budget_s=answer_budget, context=context)
        except SourceUnavailable:
            store.log("chat", "answer", output="PACS unavailable", ok=False)
            raise HTTPException(503, t(lang, "pacs.down"))
        if primary and a.mode == "agent":
            warmth.mark_ok()
        store.log("chat", "answer", output=a.text[:200], model=a.model, mode=a.mode,
                  input={"steps": a.steps})
        return {"text": a.text, "blocks": a.blocks, "steps": a.steps, "mode": a.mode, "retry": a.retry}

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

    @app.post("/api/reports/{case_id}/propose")
    async def propose(case_id: str, lang: Lang = "es", x_resident_login: str | None = Header(default=None)):
        """'¿Lo leemos con IA?' → Sí: a template proposal to verify (an existing draft is returned unchanged)."""
        try:
            found = await service.find(case_id)
        except SourceUnavailable:
            raise HTTPException(503, t(lang, "pacs.down"))
        if not found:
            raise HTTPException(404, t(lang, "case.missing", case=case_id))
        it = found[0]
        m = it.meta
        proposal = templates.propose(it.study.modalities, m.exam[lang] if m else None, bool(m and m.tech_critical),
                                     m.tech_note[lang] if m else None, lang)
        try:
            return await reports.propose(it.case_id, proposal, who(x_resident_login) or "residente", lang)
        except ReportError as e:
            report_error(e)

    @app.post("/api/reports/{case_id}/accept")
    async def accept(case_id: str, body: Sign, x_resident_login: str | None = Header(default=None)):
        try:
            return reports.accept(case_id, who(x_resident_login), body.version)
        except ReportError as e:
            report_error(e)

    @app.post("/api/reports/{case_id}/sign")
    async def sign(case_id: str, body: Sign, lang: Lang = "es", x_resident_login: str | None = Header(default=None)):
        """The only way to sign: the human 'Firmar' tap, with the tailnet identity forwarded by the app.
        The answer carries the next study by the ordering rule and why."""
        try:
            st = reports.sign(case_id, body.version, who(x_resident_login))
        except ReportError as e:
            report_error(e)
        try:
            nxt = await next_pending(lang)
        except SourceUnavailable:
            nxt = None  # signed anyway; the app reloads the list
        return st | {"next": nxt or {"item": None, "why": t(lang, "next.none")}}

    @app.post("/api/demo/reset-reports")
    async def reset_reports(x_resident_admin: str | None = Header(default=None)):
        """Demo only (DEMO_RESET_ENABLED=1, admins): reload the synthetic drafts so the QC demo can be replayed."""
        if env.get("DEMO_RESET_ENABLED") != "1" or x_resident_admin != "1" or not os.path.exists(seed_file):
            raise HTTPException(403, "Demo reset disabled")
        reports.reset_demo(seed_file)
        pending.reset()
        derived_at.clear()
        store.log("view", "demo_reset", output="synthetic drafts reloaded")
        return {"ok": True}

    # ---- reading station (level 1) ---------------------------------------------------------------------
    @app.get("/api/station/config")
    async def station_config(x_resident_login: str | None = Header(default=None)):
        st = stations.linked(who(x_resident_login))
        return {"viewer_url": env.get("VIEWER_URL", ""), "linked": st is not None}

    @app.post("/api/station/pair")
    async def station_pair(x_resident_login: str | None = Header(default=None)):
        try:
            st = stations.pair(who(x_resident_login))
        except StationError as e:
            station_error(e)
        store.log("view", "station_pair", output="código emitido")
        return {"station_id": st.id, "code": st.code, "expires_in": 600}

    @app.get("/api/station/events")
    async def station_events(station: str, x_resident_login: str | None = Header(default=None)):
        try:
            st = stations.owned(station, who(x_resident_login))
        except StationError as e:
            station_error(e)
        return StreamingResponse(stations.stream(st), media_type="text/event-stream",
                                 headers={"cache-control": "no-store", "x-accel-buffering": "no"})

    @app.get("/api/station/state")
    async def station_state(station: str, x_resident_login: str | None = Header(default=None)):
        try:
            st = stations.owned(station, who(x_resident_login))
        except StationError as e:
            station_error(e)
        linked = stations.is_linked(st)
        return {"linked": linked, "code": st.code, "last_study_uid": st.last_uid if linked else None}

    @app.post("/api/station/link")
    async def station_link(body: LinkIn, x_resident_login: str | None = Header(default=None)):
        try:
            stations.link(who(x_resident_login), body.code)
        except StationError as e:
            store.log("view", "station_link", output=e.message, ok=False)
            station_error(e)
        store.log("view", "station_link", output="vinculada")
        return {"linked": True}

    @app.post("/api/station/unlink")
    async def station_unlink(x_resident_login: str | None = Header(default=None)):
        stations.unlink(who(x_resident_login))
        return {"linked": False}

    @app.post("/api/station/open")
    async def station_open(body: OpenIn, x_resident_login: str | None = Header(default=None)):
        try:
            found = await service.find(body.case_id)
        except SourceUnavailable:
            raise HTTPException(503, t("es", "pacs.down"))
        if not found:
            raise HTTPException(404, "Case not found")
        login = who(x_resident_login)
        if not stations.linked(login):
            raise HTTPException(409, "No hay estación vinculada")
        if not stations.push_open(login, found[0].study.study_uid):
            # remembered and replayed when the station reconnects, but not shown as delivered
            raise HTTPException(503, "La estación vinculada no está conectada; se abrirá al reconectar")
        store.log("view", "station_open", case_id=found[0].case_id, output="enviado a la estación (UID)")
        return {"sent": True}

    # ---- voice --------------------------------------------------------------------------------------------
    voice = transcriber if transcriber is not None else transcriber_from_env(env)

    @app.get("/api/voice/config")
    async def voice_config():
        available = voice is not None and (voice.name != "meta" or meta_cap.ok())  # Meta voice stops at the cap
        return {"available": available, "provider": voice.name if available else None}

    @app.post("/api/transcribe")
    async def transcribe(request: Request, lang: Lang = "es"):
        """WAV in, text out. The transcript goes back to the app, which sends it as a chat instruction (voice
        never signs: signing has no chat path). Audio and transcript are not stored."""
        if voice is None:
            raise HTTPException(503, "Voz no disponible")
        if voice.name == "meta" and not meta_cap.ok():
            raise HTTPException(503, "Voz no disponible: se alcanzó el tope de gasto de Meta")
        if int(request.headers.get("content-length") or 0) > MAX_BYTES:
            raise HTTPException(413, "Audio demasiado largo")
        wav = await request.body()
        if len(wav) > MAX_BYTES:
            raise HTTPException(413, "Audio demasiado largo")
        try:
            tr = await voice.transcribe(wav, lang)
        except TranscribeError as e:
            store.log("voice", "transcribe", output=e.message, ok=False, mode=voice.name)
            raise HTTPException(e.code, e.message)
        # usage row (spend) + activity: durations and cost only, never the words
        store.log("llm", "transcribe", output=f"{tr.audio_ms} ms de audio · {tr.latency_ms} ms", mode="voice",
                  model=f"{tr.provider}:muse-voice-transcribe-1.0" if tr.provider == "meta" else tr.provider,
                  cost_usd=tr.cost_usd)
        store.log("voice", "transcribe", output=f"{tr.audio_ms} ms de audio · {tr.latency_ms} ms · {len(tr.text)} caracteres",
                  mode=tr.provider)
        return {"text": tr.text, "audio_ms": tr.audio_ms, "latency_ms": tr.latency_ms, "provider": tr.provider}

    @app.get("/api/spend")
    async def spend(x_resident_admin: str | None = Header(default=None)):
        if x_resident_admin != "1":
            raise HTTPException(403, "Admins only")
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        return {"since": today, **store.spend(today)}

    return app


app = create_app() if os.environ.get("ONCALL_NO_APP") != "1" else None
