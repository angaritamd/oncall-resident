"""Pending items agent: derived from metadata, added from what the radiologist says, '¿qué queda para mañana?'."""
import httpx
from fastapi.testclient import TestClient

from oncall_core.llm import LLM
from oncall_core.main import create_app
from oncall_core.pending import is_tomorrow_query, request_kind
from oncall_core.store import Store

from test_core import CASES, UIDS, FakeSource
from test_agent import GLIMMER, final, scripted, tool_call

RAD = {"x-resident-login": "rad@example.com"}


def app(by_host=None, providers=()):
    transport, _ = scripted(by_host or {})
    a = create_app(FakeSource(list(UIDS.values())), str(CASES), store=Store(":memory:"), providers=list(providers),
                   llm=LLM(httpx.AsyncClient(transport=transport)), env={"DEMO_RESET_ENABLED": "1"})
    return TestClient(a)


def kinds(c):
    return sorted((i["case_id"], i["kind"], i["source"]) for i in c.get("/api/pending").json()["items"])


def test_derived_from_metadata():
    # DEMO-0002 and DEMO-0004 declare priors and the PACS has none; DEMO-0002's technologist asked to repeat a series
    assert kinds(app()) == [("DEMO-0002", "missing_priors", "metadata"), ("DEMO-0002", "repeat_series", "metadata"),
                            ("DEMO-0004", "missing_priors", "metadata")]


def test_radiologist_request_and_tomorrow():
    c = app()
    r = c.post("/api/chat", json={"text": "Pídele previos", "case_id": "DEMO-0005"}, headers=RAD).json()
    assert r["steps"] == ["add_pending_item"] and "No se envía a nadie" in r["text"]
    c.post("/api/chat", json={"text": "segunda revisión mañana", "case_id": "DEMO-0005"}, headers=RAD)
    assert ("DEMO-0005", "missing_priors", "radiologist") in kinds(c) and ("DEMO-0005", "second_review", "radiologist") in kinds(c)
    r = c.post("/api/chat", json={"text": "¿Qué queda para mañana?"}).json()
    assert r["steps"] == ["list_pending_items"] and "DEMO-0005 · Previos que faltan, Segunda revisión mañana" in r["text"]
    assert r["blocks"][0]["type"] == "pending_list" and len(r["blocks"][0]["items"]) == 5


def test_done_is_not_reopened_by_metadata_and_reset_clears():
    c = app()
    item = next(i for i in c.get("/api/pending").json()["items"] if i["kind"] == "repeat_series")
    assert c.post(f"/api/pending/{item['id']}/done").json()["status"] == "done"
    assert ("DEMO-0002", "repeat_series", "metadata") not in kinds(c)
    c.post(f"/api/pending/{item['id']}/reopen")
    assert ("DEMO-0002", "repeat_series", "metadata") in kinds(c)
    c.post("/api/demo/reset-reports", headers={"x-resident-admin": "1"})
    assert len(c.get("/api/pending").json()["items"]) == 3  # re-derived after the reset


def test_metadata_derivation_is_cached():
    src = FakeSource(list(UIDS.values()))
    calls = []
    orig = src.studies_for_patient

    async def counted(pid):
        calls.append(pid)
        return await orig(pid)

    src.studies_for_patient = counted
    c = TestClient(create_app(src, str(CASES), store=Store(":memory:"), providers=[], env={}))
    for _ in range(5):
        c.get("/api/pending")
    assert len(calls) == 2  # DEMO-0002 and DEMO-0004 declare priors: one lookup each, not one per request


def test_model_tool_adds_item():
    c = app({"glimmer.test": [tool_call("add_pending_item", {"case_id": "DEMO-0003", "kind": "late_phase", "note": "fase tardía"}),
                              final("Anotado.")]}, [GLIMMER])
    r = c.post("/api/chat", json={"text": "Para el DEMO-0003 hay que pedir unos cortes más adelante, por favor anótalo ahí", "case_id": "DEMO-0003"}, headers=RAD).json()
    # provenance is the model, never the radiologist
    assert r["steps"] == ["add_pending_item"] and ("DEMO-0003", "late_phase", "resident") in kinds(c)


async def test_model_never_reopens_or_relabels():
    from oncall_core.pending import Pending
    p = Pending(Store(":memory:"))
    row = p.add("X", "second_review", "radiologist", "mi nota", by="rad")
    p.set_status(row["id"], "done")
    again = p.add("X", "second_review", "resident", "nota del modelo", by="residente-ia")
    assert again["status"] == "done" and again["note"] == "mi nota" and again["source"] == "radiologist"
    assert p.add("X", "second_review", "radiologist", by="rad")["status"] == "open"  # the radiologist may re-open


def test_matchers():
    assert is_tomorrow_query("¿Qué queda para mañana?") and is_tomorrow_query("que quedo para manana")
    assert not is_tomorrow_query("qué queda para mañana en el DEMO-0003 y luego abre el siguiente")
    assert request_kind("pídele previos") == "missing_priors" and request_kind("repetir la serie") == "repeat_series"
    assert request_kind("cortes tardíos") == "late_phase" and request_kind("hola") is None
    assert request_kind("el nódulo mide doce milímetros y además quiero segunda revisión mañana por favor") is None


def test_model_told_the_truth_about_a_closed_item():
    c = app({"glimmer.test": [tool_call("add_pending_item", {"case_id": "DEMO-0002", "kind": "repeat_series"}), final("…")]}, [GLIMMER])
    item = next(i for i in c.get("/api/pending").json()["items"] if i["kind"] == "repeat_series")
    c.post(f"/api/pending/{item['id']}/done")
    c.post("/api/chat", json={"text": "Anota otra vez que hay que repetir la serie del DEMO-0002 para mañana", "case_id": "DEMO-0002"}, headers=RAD)
    assert ("DEMO-0002", "repeat_series", "metadata") not in kinds(c)  # still done
