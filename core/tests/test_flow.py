"""Day 4: stable reading order, template proposal, accept, sign → next, and flow commands."""
import random

import httpx
from fastapi.testclient import TestClient

from adapters.base import Study
from oncall_core import commands, templates
from oncall_core.llm import LLM
from oncall_core.main import create_app
from oncall_core.store import Store

from test_core import CASES, UIDS, FakeSource

RAD = {"x-resident-login": "rad@example.com"}
ORDER = ["DEMO-0001", "DEMO-0002", "DEMO-0005", "DEMO-0004", "DEMO-0003"]


def app(uids=None, store=None):
    store = store or Store(":memory:")
    a = create_app(FakeSource(list(uids or UIDS.values())), str(CASES), store=store, providers=[],
                   llm=LLM(httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500)))), env={})
    return TestClient(a), store


def order(c):
    return [i["case_id"] for i in c.get("/api/worklist").json()["items"]]


def test_order_is_the_rule_whatever_the_pacs_order():
    uids = list(UIDS.values())
    for seed in range(5):
        random.Random(seed).shuffle(uids)
        c, _ = app(uids)
        assert order(c) == ORDER


def test_equal_wait_is_broken_by_study_id():
    from datetime import datetime, timezone
    from oncall_core.cases import CaseMeta
    from oncall_core.worklist import WorkItem, sort_items
    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    mk = lambda cid: WorkItem(Study(cid, "P", ("CT",), None, None, 1, 1),
                              CaseMeta(cid, cid, {}, None, None, {}, {}, False, "routine", at, False))
    assert [i.case_id for i in sort_items([mk("B"), mk("C"), mk("A")])] == ["A", "B", "C"]


def test_signed_leave_pending_and_show_in_signed_today_and_sign_proposes_next():
    c, _ = app()
    st = c.post("/api/reports/DEMO-0001/propose").json()
    assert st["proposal_pending"] and st["blanks"] and not st["signable"]  # critical: blanks to dictate
    st = c.put("/api/reports/DEMO-0001", json={"version": st["version"], "findings": "Neumotórax derecho de 2 cm.",
                                               "impression": "Neumotórax derecho."}).json()
    assert st["blanks"] == [] and st["proposal_pending"] and not st["signable"]
    assert c.post("/api/reports/DEMO-0001/sign", json={"version": st["version"]}, headers=RAD).status_code == 409
    st = c.post("/api/reports/DEMO-0001/accept", headers=RAD).json()
    assert st["signable"]
    r = c.post("/api/reports/DEMO-0001/sign", json={"version": st["version"]}, headers=RAD).json()
    assert r["status"] == "signed" and r["next"]["item"]["case_id"] == "DEMO-0002"
    assert "STAT" in r["next"]["why"] and "Regla" in r["next"]["why"]
    wl = c.get("/api/worklist").json()
    assert [i["case_id"] for i in wl["items"]] == ORDER[1:]
    assert [i["case_id"] for i in wl["signed_today"]] == ["DEMO-0001"]
    assert c.get("/api/cases/DEMO-0001").json()["position"] == 0  # still openable once signed


def test_proposal_never_overwrites_a_draft_and_normal_template_is_marked_pending():
    c, _ = app()
    st = c.post("/api/reports/DEMO-0003/propose").json()
    # the fake PACS reports CT for every study; the modality decides the template
    assert st["proposal_pending"] and st["blanks"] == [] and st["template"] == "ct-normal"
    assert c.post("/api/reports/DEMO-0003/propose").json()["version"] == st["version"]
    assert c.post("/api/reports/DEMO-0003/accept", headers=RAD).json()["signable"]
    assert c.post("/api/reports/DEMO-0003/accept", headers=RAD).status_code == 409


def test_accept_refused_with_blanks():
    c, _ = app()
    c.post("/api/reports/DEMO-0001/propose")
    r = c.post("/api/reports/DEMO-0001/accept", headers=RAD)
    assert r.status_code == 409 and "dictar" in r.json()["detail"]


def test_commands_accept_next_review_and_sign_refusal():
    c, store = app()
    c.post("/api/reports/DEMO-0003/propose")
    r = c.post("/api/chat", json={"text": "De acuerdo", "case_id": "DEMO-0003"}).json()
    assert r["mode"] == "command" and r["steps"] == ["accept_proposal"] and "listo para firma" in r["text"]
    r = c.post("/api/chat", json={"text": "Fírmalo", "case_id": "DEMO-0003"}).json()
    assert r["steps"] == ["sign_refused"] and c.get("/api/reports/DEMO-0003").json()["status"] == "draft"
    r = c.post("/api/chat", json={"text": "revisa", "case_id": "DEMO-0003"}).json()
    assert r["steps"] == ["qc_check"] and r["blocks"][0]["type"] == "report"
    r = c.post("/api/chat", json={"text": "Abre el siguiente", "case_id": "DEMO-0001"}).json()
    assert r["blocks"][0]["case"]["case_id"] == "DEMO-0002" and "DEMO-0002" in r["text"]


def test_command_matching():
    assert commands.match("¿De acuerdo!") == "accept" and commands.match("abre el siguiente") == "next"
    assert commands.match("fírmalo") == "sign" and commands.match("Revisa.") == "review"
    assert commands.match("el nódulo mide 12 mm") is None
    assert commands.match("de acuerdo pero cambia el nódulo a doce milímetros por favor") is None


def test_templates_by_modality():
    assert templates.propose(("CT",), "TC de tórax", False, None, "es")["template"] == "ct-normal"
    p = templates.propose(("CR",), "RX de tórax", True, "Sospecha de neumotórax derecho.", "es")
    assert templates.blanks(p["findings"], p["impression"]) and "neumotórax derecho" in p["findings"]
