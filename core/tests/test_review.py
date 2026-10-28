import json
import os
import tempfile
from pathlib import Path

os.environ["ONCALL_NO_APP"] = "1"

import httpx
import pytest
from fastapi.testclient import TestClient

from oncall_core.cases import load_cases
from oncall_core.llm import LLM
from oncall_core.main import create_app
from oncall_core.reports import Reports
from oncall_core.review import Review, _no_counter_evidence
from oncall_core.service import Service
from oncall_core.store import Store
from tests.test_agent import GLIMMER, scripted, tool_call
from tests.test_core import FakeSource

# Unit-only review data (inline, fake study UIDs): DEMO-0006 critical with a normal-template
# draft, DEMO-0007 with a laterality error, DEMO-0008 critical without a draft. The live review
# set (demo/seed/review_cases.json + review_reports.json) is shaped differently and is not
# used here.
TECH6 = "Sospecha de neumotórax izquierdo."
IND6 = "Dolor torácico izquierdo súbito."
FIND7 = "Consolidación en el lóbulo inferior derecho con broncograma aéreo."

_UNIT_CASES = {
    "synthetic": True,
    "cases": [
        {"case_id": "DEMO-0006", "study_uid": "1.9.9.6", "exam": {"es": "RX de tórax", "en": "Chest X-ray"},
         "sex": "M", "age": 45, "reason": {"es": IND6, "en": "Sudden left chest pain."},
         "tech_note": {"es": TECH6 + " Avisé al médico tratante.", "en": "Suspected left pneumothorax."},
         "tech_critical": True, "priority": "stat", "arrival_minutes_ago": 10, "priors_available": False},
        {"case_id": "DEMO-0007", "study_uid": "1.9.9.7", "exam": {"es": "TC de tórax", "en": "Chest CT"},
         "sex": "F", "age": 60, "reason": {"es": "Tos persistente.", "en": "Persistent cough."},
         "tech_note": {"es": "Sin novedades durante la adquisición.", "en": "Uneventful acquisition."},
         "tech_critical": False, "priority": "routine", "arrival_minutes_ago": 50, "priors_available": False},
        {"case_id": "DEMO-0008", "study_uid": "1.9.9.8", "exam": {"es": "RX de tórax", "en": "Chest X-ray"},
         "sex": "F", "age": 52, "reason": {"es": "Valoración preoperatoria.", "en": "Pre-operative assessment."},
         "tech_note": {"es": "Sospecha de derrame pleural derecho. Avisé al médico tratante.",
                       "en": "Suspected right pleural effusion."},
         "tech_critical": True, "priority": "routine", "arrival_minutes_ago": 30, "priors_available": False},
    ],
}
_UNIT_SEED = {
    "synthetic": True,
    "reports": [
        {"case_id": "DEMO-0006", "technique": "RX de tórax posteroanterior y lateral.",
         "findings": "Parénquima pulmonar sin consolidaciones ni derrame pleural. Silueta cardiaca de tamaño normal.",
         "impression": "Estudio sin hallazgos agudos. Sin cambios respecto a lo esperado."},
        {"case_id": "DEMO-0007", "technique": "TC de tórax sin contraste.", "findings": FIND7 + " Sin adenopatías mediastínicas.",
         "impression": "Consolidación en el lóbulo inferior izquierdo. Sin adenopatías."},
    ],
}


def _unit_files():
    d = Path(tempfile.mkdtemp(prefix="review-unit-"))
    c, s = d / "cases.json", d / "reports.json"
    c.write_text(json.dumps(_UNIT_CASES, ensure_ascii=False))
    s.write_text(json.dumps(_UNIT_SEED, ensure_ascii=False))
    return c, s


def mk_review(providers, by_host=None, store=None, **kw):
    transport, seen = scripted(by_host or {})
    store = store or Store(":memory:")
    cases_file, seed_file = _unit_files()
    cases = load_cases(cases_file)
    svc = Service(FakeSource([m.study_uid for m in cases.values()]), cases)
    reports = Reports(store)
    reports.seed(seed_file)
    by_case = {m.case_id: m for m in cases.values()}
    llm = LLM(httpx.AsyncClient(transport=transport))
    return Review(store, svc, reports, llm, providers, by_case, **kw), store, seen


async def started(rv, lang="es"):
    snap = await rv.start(lang, "test")
    assert snap["progress"] == {"done": 0, "total": 3}
    return snap["run_id"]


def base_state():
    return {"steps": 0, "mode": "agent", "model": "glimmer:x", "closed": None}


# 1 · a quote that is not in the section is rejected and audited
async def test_record_finding_with_invented_quote_is_rejected_and_audited():
    rv, store, _ = mk_review([])
    run_id = await started(rv)
    findings = []
    texts, _ = rv._sections("DEMO-0006", "es")
    res = rv._tool_record(run_id, "DEMO-0006", "es", base_state(), ["C1", "C2", "C3", "C4"], texts, findings,
                          {"item": "C2", "section": "tech_note", "quote": "Neumotórax a tensión", "claim": "x"})
    assert "error" in res and findings == []
    rec = [x for x in store.recent() if x["name"] == "record_finding"][0]
    assert rec["ok"] is False and rec["case_id"] == "DEMO-0006" and rec["kind"] == "review"


# 2 · an item outside the study checklist is rejected
async def test_record_finding_outside_the_checklist_is_rejected():
    rv, store, _ = mk_review([])
    run_id = await started(rv)
    findings = []
    texts, _ = rv._sections("DEMO-0006", "es")  # no C5: C4 leaves no open alerts here
    res = rv._tool_record(run_id, "DEMO-0006", "es", base_state(), ["C1", "C2", "C3", "C4"], texts, findings,
                          {"item": "C5", "section": "findings", "quote": "Parénquima", "claim": "x"})
    assert "error" in res and findings == []
    assert [x for x in store.recent() if x["name"] == "record_finding"][0]["ok"] is False


# 3 · closing with open C4 alerts and no C5 is rejected; a literal C5 closes
async def test_close_with_open_alerts_and_no_c5_is_rejected():
    rv, store, _ = mk_review([])
    run_id = await started(rv)
    state = base_state()
    qc_cached = {"open_alerts": 1, "alerts": []}
    res = rv._tool_close({"id": run_id}, "DEMO-0007", "es", state, ["C1", "C3", "C4", "C5"], [], qc_cached,
                         {"verdict": "revisar", "note": "hay que mirar"})
    assert "error" in res and state["closed"] is None
    assert [x for x in store.recent() if x["name"] == "close_study"][0]["ok"] is False
    texts, _ = rv._sections("DEMO-0007", "es")
    findings = []
    rec = rv._tool_record(run_id, "DEMO-0007", "es", state, ["C1", "C3", "C4", "C5"], texts, findings,
                          {"item": "C5", "section": "findings", "quote": FIND7, "claim": "La lateralidad cruza."})
    assert rec["recorded"] is True
    done = rv._tool_close({"id": run_id}, "DEMO-0007", "es", state, ["C1", "C3", "C4", "C5"], findings, qc_cached,
                          {"verdict": "revisar", "note": "Lateralidad por confirmar."})
    assert done == {"closed": "revisar"}
    row = [s for s in rv.get(run_id)["studies"] if s["case_id"] == "DEMO-0007"][0]
    assert row["verdict"] == "revisar" and row["items"]["C5"] == "registrado"


# 4 · provider down: rules mode, C2/C3/C5 "No evaluado"
async def test_provider_down_closes_in_rules_mode_with_no_evaluado():
    rv, store, _ = mk_review([GLIMMER], {"glimmer.test": 500})
    run_id = await started(rv)
    await rv.advance(run_id)
    snap = rv.get(run_id)
    assert snap["status"] == "done"
    by_id = {s["case_id"]: s for s in snap["studies"]}
    assert by_id["DEMO-0007"]["verdict"] == "revisar" and by_id["DEMO-0007"]["mode"] == "rules"
    assert by_id["DEMO-0007"]["items"]["C5"] == "no_evaluado"
    assert by_id["DEMO-0006"]["verdict"] == "no_evaluado" and by_id["DEMO-0006"]["mode"] == "rules"
    assert by_id["DEMO-0006"]["items"]["C2"] == "no_evaluado"
    assert by_id["DEMO-0006"]["mode_label"] == "Reglas"
    assert by_id["DEMO-0008"]["verdict"] == "sin_borrador"
    assert by_id["DEMO-0008"]["items"] == {"C1": "evaluado", "C2": "no_evaluado"}


# 5 · resume skips finished studies and makes zero model calls when nothing is left
async def test_resume_skips_finished_and_makes_no_calls_when_empty():
    script = [
        tool_call("record_finding", {"item": "C2", "section": "tech_note", "quote": TECH6, "claim": "No responde."}),
        tool_call("record_finding", {"item": "C3", "section": "indication", "quote": IND6, "claim": "No responde."}),
        tool_call("close_study", {"verdict": "critico_sin_respuesta", "note": "No menciona el neumotórax."}),
        tool_call("record_finding", {"item": "C5", "section": "findings", "quote": FIND7, "claim": "Cruza."}),
        tool_call("close_study", {"verdict": "revisar", "note": "Lateralidad."}),
    ]
    rv, store, seen = mk_review([GLIMMER], {"glimmer.test": script})
    run_id = await started(rv)
    await rv.advance(run_id)
    assert rv.get(run_id)["status"] == "done"
    calls = len(seen)
    assert calls > 0
    await rv.advance(run_id)  # nothing left: no model call
    assert len(seen) == calls
    assert rv.get(run_id)["status"] == "done"


# 6 · exhausted budget pauses; resume finishes
async def test_exhausted_budget_pauses_and_resume_finishes():
    rv, store, _ = mk_review([], run_budget_s=0.0)
    run_id = await started(rv)
    await rv.advance(run_id)
    assert rv.get(run_id)["status"] == "paused"
    assert all(s["status"] == "pending" for s in rv.get(run_id)["studies"])
    rv.run_budget_s = 3600.0
    rv.mark_running(run_id, "es")
    await rv.advance(run_id)
    snap = rv.get(run_id)
    assert snap["status"] == "done" and snap["progress"] == {"done": 3, "total": 3}


# 6b · pause mid-run on a real budget, then resume reviews more studies
async def test_pause_mid_run_then_resume_reviews_more():
    rv, _, _ = mk_review([], run_budget_s=3600.0)
    run_id = await started(rv)
    run = rv._run_row(run_id)
    await rv._review_one(run, rv._studies(run_id)[0])  # first study reviewed with budget left
    assert rv.get(run_id)["progress"] == {"done": 1, "total": 3}
    with rv.lock:  # two hours of work pass: the next study would exceed the real budget
        rv.db.execute("UPDATE review_runs SET resumed_at = '2000-01-01T00:00:00+00:00' WHERE id = ?", (run_id,))
    await rv.advance(run_id)
    snap = rv.get(run_id)
    assert snap["status"] == "paused" and snap["progress"] == {"done": 1, "total": 3}
    rv.mark_running(run_id, "es")  # resume grants a fresh budget from now
    await rv.advance(run_id)
    snap = rv.get(run_id)
    assert snap["status"] == "done" and snap["progress"] == {"done": 3, "total": 3}


# 6c · a restart marks a running run paused (resumable, never stuck)
async def test_restart_marks_running_as_paused():
    store = Store(":memory:")
    rv, _, _ = mk_review([], store=store)
    run_id = await started(rv)
    rv2, _, _ = mk_review([], store=store)  # "restart": same DB, new instance
    assert rv2.get(run_id)["status"] == "paused"
    rv2.mark_running(run_id, "es")
    await rv2.advance(run_id)
    assert rv2.get(run_id)["status"] == "done"


# 3b · counter-evidence needs an explicit denial
@pytest.mark.parametrize("note,ok", [
    ("No hay contraevidencia en el informe.", True),
    ("Sin contraevidencia que la contradiga.", True),
    ("Ninguna contraevidencia en hallazgos.", True),
    ("There is no counter-evidence in findings.", True),
    ("Without counter-evidence, closing.", True),
    ("Sí hay contraevidencia en hallazgos.", False),
    ("Hay contraevidencia.", False),
    ("No, hay contraevidencia.", False),
    ("Hay que mirar.", False),
])
def test_no_counter_evidence_needs_explicit_negation(note, ok):
    assert _no_counter_evidence(note) is ok


# 7 · display order: critical unanswered and critical without draft first
async def test_output_order_puts_critical_first():
    script = [
        tool_call("record_finding", {"item": "C2", "section": "tech_note", "quote": TECH6, "claim": "No responde."}),
        tool_call("record_finding", {"item": "C3", "section": "indication", "quote": IND6, "claim": "No responde."}),
        tool_call("close_study", {"verdict": "critico_sin_respuesta", "note": "No menciona el neumotórax."}),
        tool_call("record_finding", {"item": "C5", "section": "findings", "quote": FIND7, "claim": "Cruza."}),
        tool_call("close_study", {"verdict": "revisar", "note": "Lateralidad."}),
    ]
    rv, _, _ = mk_review([GLIMMER], {"glimmer.test": script})
    run_id = await started(rv)
    await rv.advance(run_id)
    order = [(s["case_id"], s["verdict"]) for s in rv.get(run_id)["studies"]]
    by_id = dict(order)
    assert {c for c, _ in order[:2]} == {"DEMO-0006", "DEMO-0008"}
    assert by_id["DEMO-0006"] == "critico_sin_respuesta" and by_id["DEMO-0008"] == "sin_borrador"
    assert order[2] == ("DEMO-0007", "revisar")


# 8 · no report changes and nothing signed
async def test_review_never_modifies_or_signs_reports():
    script = [
        tool_call("record_finding", {"item": "C2", "section": "tech_note", "quote": TECH6, "claim": "No responde."}),
        tool_call("record_finding", {"item": "C3", "section": "indication", "quote": IND6, "claim": "No responde."}),
        tool_call("close_study", {"verdict": "critico_sin_respuesta", "note": "No menciona el neumotórax."}),
        tool_call("record_finding", {"item": "C5", "section": "findings", "quote": FIND7, "claim": "Cruza."}),
        tool_call("close_study", {"verdict": "revisar", "note": "Lateralidad."}),
    ]
    rv, store, _ = mk_review([GLIMMER], {"glimmer.test": script})
    before = {cid: (rv.reports.state(cid)["findings"], rv.reports.state(cid)["impression"],
                    rv.reports.state(cid)["version"]) for cid in ("DEMO-0006", "DEMO-0007")}
    run_id = await started(rv)
    await rv.advance(run_id)
    after = {cid: (rv.reports.state(cid)["findings"], rv.reports.state(cid)["impression"],
                   rv.reports.state(cid)["version"]) for cid in ("DEMO-0006", "DEMO-0007")}
    assert before == after and rv.reports.signed() == {}
    assert rv.reports.state("DEMO-0006")["status"] == "draft"


def app_with_review(by_host, providers, env=None):
    transport, seen = scripted(by_host)
    store = Store(":memory:")
    cases_file, seed_file = _unit_files()
    cases = load_cases(cases_file)
    svc_uids = [m.study_uid for m in cases.values()]
    from tests.test_core import FakeSource as FS
    app = create_app(FS(svc_uids), str(cases_file), store=store, providers=providers,
                     llm=LLM(httpx.AsyncClient(transport=transport)),
                     env={"GLIMMER_COLD_THRESHOLD": "5", "REPORTS_SEED": str(seed_file), **(env or {})})
    return TestClient(app), store, seen


# 10 · ?set=review swaps the live set (own case_ids, reused studies); default restores 0001-0005
def test_demo_set_switch_swaps_cases_and_back():
    from tests.test_core import CASES, UIDS
    root = Path(__file__).resolve().parents[2]
    transport, seen = scripted({})
    store = Store(":memory:")
    app = create_app(FakeSource(list(UIDS.values())), str(CASES), store=store, providers=[],
                     llm=LLM(httpx.AsyncClient(transport=transport)),
                     env={"GLIMMER_COLD_THRESHOLD": "5", "DEMO_RESET_ENABLED": "1",
                          "REVIEW_REPORTS_SEED": str(root / "demo/seed/review_reports.json"),
                          "REVIEW_CASES_FILE": str(root / "demo/seed/review_cases.json")})
    c = TestClient(app)
    assert c.post("/api/demo/reset-reports?set=review").status_code == 403  # admin only
    r = c.post("/api/demo/reset-reports?set=review", headers={"x-resident-admin": "1"})
    assert r.status_code == 200 and r.json() == {"ok": True, "set": "review"}
    wl = c.get("/api/worklist").json()["items"]
    assert [i["case_id"] for i in wl[:3]] == ["DEMO-0006", "DEMO-0007", "DEMO-0008"]
    assert len(wl) == 5 and all(not i["has_metadata"] for i in wl[3:])
    assert c.get("/api/cases/DEMO-0006").json()["critical"] is True
    r = c.post("/api/demo/reset-reports", headers={"x-resident-admin": "1"})
    assert r.status_code == 200
    assert [i["case_id"] for i in c.get("/api/worklist").json()["items"]] == [
        "DEMO-0001", "DEMO-0002", "DEMO-0005", "DEMO-0004", "DEMO-0003"]


# 9 · review intent in ES and EN
def test_review_intent_es_and_en():
    from oncall_core import intents
    assert intents.match("revisa todos los estudios")[0] == "review_all"
    assert intents.match("revisión del turno")[0] == "review_all"
    assert intents.match("review all studies")[0] == "review_all"
    c, _, _ = app_with_review({}, [])
    r = c.post("/api/chat", json={"text": "revisa todos los estudios"}).json()
    assert r["steps"] == ["review_all"] and r["mode"] == "command"
    assert r["blocks"][0]["type"] == "review" and r["blocks"][0]["review"]["progress"]["total"] == 3
    c2, _, _ = app_with_review({}, [])
    r2 = c2.post("/api/chat", json={"text": "review all studies", "lang": "en"}).json()
    assert r2["blocks"][0]["type"] == "review" and r2["blocks"][0]["review"]["lang"] == "en"
