import json
import os
from pathlib import Path

os.environ["ONCALL_NO_APP"] = "1"

import httpx
import pytest
from fastapi.testclient import TestClient

from oncall_core import qc
from oncall_core.llm import LLM, Provider, usage_cost
from oncall_core.main import create_app
from oncall_core.reports import ReportError, Reports
from oncall_core.store import Store
from tests.test_agent import GLIMMER, SPARK, final, scripted, tool_call
from tests.test_core import CASES, UIDS, FakeSource

SEED = Path(__file__).resolve().parents[2] / "demo/seed/reports.json"
F12 = "Nódulo sólido en el lóbulo superior derecho de 12 mm, de bordes lisos."
I8 = "Nódulo pulmonar sólido en el lóbulo superior derecho de 8 mm."


# ---- QC rules -----------------------------------------------------------------------------------------

def test_measure_mismatch_is_proven_with_exact_fragments_and_fix():
    [i] = qc.rule_issues(F12, I8)
    assert i.rule == "measure_mismatch" and i.severity == "error"
    assert i.body_excerpt in F12 and i.impression_excerpt in I8
    assert i.fix_find == I8 and i.fix_replace == I8.replace("8 mm", "12 mm")
    assert {"section": "impression", "text": "8 mm"} in i.marks and {"section": "findings", "text": "12 mm"} in i.marks


def test_units_are_normalised_and_equal_measures_pass():
    assert qc.rule_issues("Masa de 1,2 cm.", "Masa de 12 mm.") == []


def test_crossed_laterality_is_proven_and_swapped_with_agreement():
    [i] = qc.rule_issues("Consolidación en el lóbulo inferior derecho.", "Consolidación en el lóbulo inferior izquierdo.")
    assert i.rule == "laterality_mismatch" and i.fix_replace == "Consolidación en el lóbulo inferior derecho."
    assert qc.rule_issues("Derrame bilateral, derecho e izquierdo.", "Derrame izquierdo.") == []  # bilateral: not provable


def test_model_issues_with_invented_quotes_are_dropped():
    raw = json.dumps({"issues": [
        {"type": "omitted_finding", "body_excerpt": "No hay derrame pleural.", "impression_excerpt": "", "explanation": "x"},
        {"type": "omitted_finding", "body_excerpt": "Neumotórax a tensión", "impression_excerpt": "", "explanation": "inventado"},
        {"type": "free_opinion", "body_excerpt": "No hay derrame pleural.", "impression_excerpt": ""},
    ]})
    issues = qc.parse_model_issues("texto previo " + raw, "Seguimiento", "Nódulo. No hay derrame pleural.", "Nódulo.")
    assert [(i.rule, i.severity, i.body_excerpt) for i in issues] == [("omitted_finding", "verify", "No hay derrame pleural.")]
    assert qc.parse_model_issues("no es json", "", "a", "b") == []


# ---- report lifecycle ---------------------------------------------------------------------------------

def reports(model_reply: str | None = None):
    store = Store(":memory:")
    ctx = None
    if model_reply is not None:
        transport, _ = scripted({"glimmer.test": [final(model_reply)]})
        from oncall_core.reports import QcContext
        ctx = QcContext(LLM(httpx.AsyncClient(transport=transport)), [GLIMMER])
    return Reports(store, ctx), store


async def test_edit_changes_one_fragment_reruns_qc_and_returns_diff():
    r, _ = reports()
    st = await r.draft("DEMO-0002", "TC.", "Nódulo de 8 mm en el lóbulo superior derecho.", "Nódulo de 8 mm.", "residente", "es")
    assert st["open_alerts"] == 0 and st["signable"]
    st, diff = await r.edit("DEMO-0002", "findings", "8 mm", "12 mm", "residente", "es")
    assert st["version"] == 2 and "12 mm" in st["findings"] and "8 mm" in st["impression"]  # not propagated
    assert st["open_alerts"] == 1 and not st["signable"]
    assert {"op": "del", "text": "8"} in diff["parts"] and {"op": "ins", "text": "12"} in diff["parts"]
    with pytest.raises(ReportError) as e:
        await r.edit("DEMO-0002", "impression", "zzz", "x", "residente", "es")
    assert e.value.code == 422


async def test_apply_fix_then_sign_locks_the_report():
    r, store = reports()
    r.seed(SEED)
    st = await r.run_qc("DEMO-0004", "es")
    [alert] = [i for i in st["qc"] if i["status"] == "open"]
    with pytest.raises(ReportError, match="pendiente"):
        r.sign("DEMO-0004", st["version"], "rad@example.com")
    st, _ = await r.apply_fix("DEMO-0004", alert["id"], "rad@example.com", "es")
    assert "12 mm" in st["impression"] and st["open_alerts"] == 0 and st["signable"]
    with pytest.raises(ReportError, match="identificado"):
        r.sign("DEMO-0004", st["version"], "")
    with pytest.raises(ReportError, match="cambió"):
        r.sign("DEMO-0004", st["version"] - 1, "rad@example.com")
    signed = r.sign("DEMO-0004", st["version"], "rad@example.com")
    assert signed["status"] == "signed" and signed["signed_by"] == "rad@example.com"
    for attempt in (r.edit("DEMO-0004", "findings", "12 mm", "9 mm", "x", "es"),):
        with pytest.raises(ReportError, match="bloqueado"):
            await attempt
    assert any(x["kind"] == "sign" for x in store.recent())


async def test_dismiss_needs_a_reason_and_survives_reruns():
    r, _ = reports()
    r.seed(SEED)
    st = await r.run_qc("DEMO-0005", "es")
    [alert] = [i for i in st["qc"] if i["status"] == "open"]
    with pytest.raises(ReportError):
        r.dismiss("DEMO-0005", alert["id"], "", "rad")
    st = r.dismiss("DEMO-0005", alert["id"], "Lado confirmado en la imagen", "rad")
    assert st["open_alerts"] == 0
    st = await r.run_qc("DEMO-0005", "es")  # same issue again -> stays dismissed with its reason
    assert st["open_alerts"] == 0 and st["qc"][0]["reason"] == "Lado confirmado en la imagen"


async def test_model_qc_adds_verify_items_and_logs_usage():
    reply = json.dumps({"issues": [{"type": "indication_unanswered", "body_excerpt": "neumonía complicada",
                                    "impression_excerpt": "Sin derrame.", "explanation": "No responde."}]})
    r, store = reports(reply)
    r.indication_for = lambda cid, lang: "Fiebre y tos de 5 días; descartar neumonía complicada."
    st = await r.draft("DEMO-0002", "TC.", "Sin consolidaciones. Sin derrame.", "Sin derrame.", "residente", "es")
    [v] = [i for i in st["qc"] if i["status"] == "open"]
    assert v["severity"] == "verify" and v["body_label"] == "indication" and v["fix_find"] is None
    assert st["qc_mode"] == "agent"
    assert any(x["kind"] == "llm" and x["name"] == "qc" for x in store.recent())


# ---- API and model guard ------------------------------------------------------------------------------

def app_with(by_host, providers, env=None):
    transport, seen = scripted(by_host)
    store = Store(":memory:")
    app = create_app(FakeSource(list(UIDS.values())), str(CASES), store=store, providers=providers,
                     llm=LLM(httpx.AsyncClient(transport=transport)),
                     env={"GLIMMER_COLD_THRESHOLD": "5", "REPORTS_SEED": str(SEED), **(env or {})})
    return TestClient(app), store, seen


def test_the_model_cannot_sign():
    c, store, _ = app_with({"glimmer.test": [tool_call("sign_report", {"case_id": "DEMO-0004"}), final("No puedo firmar.")]}, [GLIMMER])
    r = c.post("/api/chat", json={"text": "firma el informe", "case_id": "DEMO-0004"}).json()
    assert r["steps"] == ["sign_report"]
    assert c.get("/api/reports/DEMO-0004").json()["status"] == "draft"
    assert [x for x in store.recent() if x["kind"] == "tool"][0]["ok"] is False


def test_sign_endpoint_requires_identity_and_no_open_alerts():
    c, _, _ = app_with({}, [])
    st = c.get("/api/reports/DEMO-0004").json()
    assert st["open_alerts"] == 1  # seeded 12 mm vs 8 mm
    assert c.post("/api/reports/DEMO-0004/sign", json={"version": st["version"]},
                  headers={"x-resident-login": "rad@example.com"}).status_code == 409
    item = [i for i in st["qc"] if i["status"] == "open"][0]["id"]
    st = c.post(f"/api/reports/DEMO-0004/qc/{item}/apply", headers={"x-resident-login": "rad@example.com"}).json()
    assert st["diff"]["section"] == "impression" and st["signable"]
    assert c.post("/api/reports/DEMO-0004/sign", json={"version": st["version"]}).status_code == 403
    ok = c.post("/api/reports/DEMO-0004/sign", json={"version": st["version"]}, headers={"x-resident-login": "rad@example.com"})
    assert ok.status_code == 200 and ok.json()["status"] == "signed"
    assert c.put("/api/reports/DEMO-0004", json={"version": st["version"], "findings": "x"}).status_code == 409


def test_chat_edit_uses_screen_context_and_shows_qc():
    script = [tool_call("edit_report", {"case_id": "DEMO-0002", "section": "findings", "find": "8 mm", "replace": "12 mm"}),
              final("Cambiado a 12 mm en hallazgos.")]
    c, _, seen = app_with({"glimmer.test": script}, [GLIMMER])
    c.app.state.reports.db.execute("DELETE FROM reports")
    c.app.state.reports.qc_ctx = None  # QC by rules only here, so the scripted model replies all go to the agent
    import asyncio
    asyncio.run(c.app.state.reports.draft("DEMO-0002", "TC.", "Nódulo de 8 mm.", "Nódulo de 8 mm.", "residente", "es"))
    r = c.post("/api/chat", json={"text": "el nódulo mide 12 mm", "case_id": "DEMO-0002"}).json()
    ctx = seen[0][3]["messages"][1]["content"]
    assert "DEMO-0002" in ctx and "<<<Nódulo de 8 mm.>>>" in ctx
    rep = r["blocks"][0]
    assert rep["type"] == "report" and rep["diff"]["section"] == "findings" and rep["report"]["open_alerts"] == 1


def test_demo_reset_is_admin_only_and_opt_in():
    c, _, _ = app_with({}, [])
    assert c.post("/api/demo/reset-reports", headers={"x-resident-admin": "1"}).status_code == 403
    c2, _, _ = app_with({}, [], {"DEMO_RESET_ENABLED": "1"})
    assert c2.post("/api/demo/reset-reports").status_code == 403
    assert c2.post("/api/demo/reset-reports", headers={"x-resident-admin": "1"}).status_code == 200


def test_usage_cost_uses_official_prices():
    tin, tout, cost = usage_cost("muse-spark-1.3", {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000,
                                                    "prompt_tokens_details": {"cached_tokens": 200_000}})
    assert (tin, tout) == (1_000_000, 1_000_000) and cost == round(0.8 * 1.25 + 0.2 * 0.15 + 4.25, 6)
    assert usage_cost("muse-glimmer", {"prompt_tokens": 10, "completion_tokens": 5}) == (10, 5, None)
    assert usage_cost("x", None) == (None, None, None)


def test_spark_usage_is_logged_per_call():
    resp = final("ok") | {"usage": {"prompt_tokens": 1000, "completion_tokens": 100}}
    c, store, _ = app_with({"api.meta.test": [resp]}, [SPARK])
    c.post("/api/chat", json={"text": "hola"})
    llm = [x for x in store.recent() if x["kind"] == "llm"][0]
    assert llm["tokens_in"] == 1000 and llm["cost_usd"] == round((1000 * 1.25 + 100 * 4.25) / 1e6, 6)
    assert c.get("/api/spend").status_code == 403
    assert c.get("/api/spend", headers={"x-resident-admin": "1"}).json()["usd"] > 0
    plain = [x for x in c.get("/api/activity").json()["items"] if x["kind"] == "llm"][0]
    assert "cost_usd" not in plain and "tokens_in" not in plain and plain["output"] is None
