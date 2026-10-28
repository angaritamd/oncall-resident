"""Latency PR: no false 'Listo.', measurements in code, QC of the model in the background, keepalive, '12 12'."""
import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from oncall_core.commands import measurement, measurement_edit
from oncall_core.llm import LLM
from oncall_core.main import create_app
from oncall_core.reports import QcContext, Reports
from oncall_core.store import Store
from oncall_core.transcribe import dedupe_numbers

from test_agent import GLIMMER, final, scripted, tool_call
from test_core import CASES, UIDS, FakeSource
from test_reports import SEED

RAD = {"x-resident-login": "rad@example.com"}
SPARK_HOST = "api.meta.test"


def make(by_host, providers, env=None):
    transport, seen = scripted(by_host)
    store = Store(":memory:")
    app = create_app(FakeSource(list(UIDS.values())), str(CASES), store=store, providers=providers,
                     llm=LLM(httpx.AsyncClient(transport=transport)),
                     env={"GLIMMER_COLD_THRESHOLD": "5", "REPORTS_SEED": str(SEED), **(env or {})})
    app.state.reports.qc_ctx = None  # QC by rules here: every scripted reply goes to the agent
    return TestClient(app), store, seen


def truncated(text="Listo."):
    """A reply cut by max_tokens: the reasoning used the budget and no tool was called."""
    return {"choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "length"}],
            "usage": {"prompt_tokens": 1886, "completion_tokens": 1500}}


def spark():
    from oncall_core.llm import Provider
    return Provider("meta-model-api", "fallback", f"https://{SPARK_HOST}/v1", "k2", "muse-spark-1.3")


EDIT = "en hallazgos cambia bordes lisos por bordes espiculados"


@pytest.mark.parametrize("who", ["glimmer", "spark"])
@pytest.mark.parametrize("reply", [truncated(), final("Hecho, actualicé el borrador."), final("")])
def test_no_false_listo(who, reply):
    hosts = {"glimmer.test": [reply]} if who == "glimmer" else {"glimmer.test": 404, SPARK_HOST: [reply]}
    c, _, _ = make(hosts, [GLIMMER, spark()])
    before = c.get("/api/reports/DEMO-0004").json()["version"]
    r = c.post("/api/chat", json={"text": EDIT, "case_id": "DEMO-0004"}, headers=RAD).json()
    assert r["text"] == "No apliqué ningún cambio." and r["retry"] is True and r["steps"] == []
    assert r["mode"] == ("agent" if who == "glimmer" else "fallback")
    assert c.get("/api/reports/DEMO-0004").json()["version"] == before


def test_failed_tool_is_never_confirmed():
    # the find text does not exist: the tool fails, and the model's "Hecho" is not passed on
    hosts = {"glimmer.test": [tool_call("edit_report", {"case_id": "DEMO-0004", "section": "findings", "find": "no existe",
                                                         "replace": "x"}), final("Hecho.")]}
    c, _, _ = make(hosts, [GLIMMER])
    r = c.post("/api/chat", json={"text": EDIT, "case_id": "DEMO-0004"}, headers=RAD).json()
    assert r["text"].startswith("No apliqué ningún cambio.") and "0 veces" in r["text"] and r["retry"]


def test_no_op_edit_is_not_a_change():
    hosts = {"glimmer.test": [tool_call("edit_report", {"case_id": "DEMO-0004", "section": "findings", "find": "bordes lisos",
                                                         "replace": "bordes lisos"}), final("Listo.")]}
    c, _, _ = make(hosts, [GLIMMER])
    r = c.post("/api/chat", json={"text": EDIT, "case_id": "DEMO-0004"}, headers=RAD).json()
    assert r["text"].startswith("No apliqué ningún cambio.") and r["retry"]


def test_questions_without_tools_still_answer():
    c, _, _ = make({"glimmer.test": [final("La prioridad viene de la orden: STAT.")]}, [GLIMMER])
    r = c.post("/api/chat", json={"text": "¿por qué es prioritario?", "case_id": "DEMO-0002"}).json()
    assert r["text"] == "La prioridad viene de la orden: STAT." and r["retry"] is False


def test_measurement_applied_in_code_without_the_model():
    c, _, seen = make({"glimmer.test": [final("no debería llamarse")]}, [GLIMMER])
    # seeded DEMO-0004: findings 12 mm, impression 8 mm → dictating 15 mm changes the findings only
    r = c.post("/api/chat", json={"text": "El nódulo mide quince milímetros", "case_id": "DEMO-0004"}, headers=RAD).json()
    assert r["mode"] == "command" and r["steps"] == ["edit_report"] and not [x for x in seen if x[1].endswith("/chat/completions")]
    rep = r["blocks"][0]["report"]
    assert "de 15 mm, de bordes lisos" in rep["findings"] and "8 mm" in rep["impression"] and rep["open_alerts"] == 1
    assert r["text"].startswith("Cambio aplicado en hallazgos de DEMO-0004 (v2).")
    assert c.post("/api/chat", json={"text": "El nódulo mide 15 mm", "case_id": "DEMO-0004"}).status_code in (200, 403)


def test_ambiguous_measurement_goes_to_the_model():
    hosts = {"glimmer.test": [tool_call("edit_report", {"case_id": "DEMO-0005", "section": "findings",
                                                         "find": "Consolidación", "replace": "Consolidación de 3 cm"})]}
    c, _, seen = make(hosts, [GLIMMER])
    # DEMO-0005 names no nodule with a measurement: the code does not guess
    r = c.post("/api/chat", json={"text": "El nódulo mide 12 mm", "case_id": "DEMO-0005"}, headers=RAD).json()
    assert [x for x in seen if x[1].endswith("/chat/completions")] and r["steps"] == ["edit_report"]


def test_measurement_parsing():
    assert measurement("El nódulo mide doce milímetros.") == ("nodulo", "12", "mm")
    assert measurement("la masa mide uno coma cinco centímetros") == ("masa", "1,5", "cm")
    assert measurement("el nódulo mide 12 mm y el otro 8") is None
    f = "Nódulo de 8 mm. Otro nódulo de 4 mm."
    assert measurement_edit(f, "nodulo", "12", "mm") is None  # two nodules: ambiguous
    assert measurement_edit("Nódulo de 8 mm, adenopatía de 9 mm.", "nodulo", "12", "mm") is None  # two measures
    assert measurement_edit("Nódulo de 12 mm.", "nodulo", "12", "mm") == ("Nódulo de 12 mm.", "Nódulo de 12 mm.")


def test_same_measurement_is_said_not_applied():
    c, _, seen = make({"glimmer.test": [final("x")]}, [GLIMMER])
    r = c.post("/api/chat", json={"text": "El nódulo mide doce milímetros", "case_id": "DEMO-0004"}, headers=RAD).json()
    assert r["text"] == "No apliqué ningún cambio. Los hallazgos de DEMO-0004 ya dicen 12 mm." and r["steps"] == []
    assert not [x for x in seen if x[1].endswith("/chat/completions")]


async def test_model_qc_runs_in_background_and_blocks_signing():
    release = asyncio.Event()

    class SlowLLM:
        async def complete(self, *a, **k):
            await release.wait()
            return {"content": "[]", "_usage": None}

    store = Store(":memory:")
    r = Reports(store, QcContext(SlowLLM(), [GLIMMER]), background_qc=True)
    st = await r.draft("X", "TC.", "Nódulo de 12 mm.", "Nódulo de 8 mm.", "rad", "es")
    # answered at once: the proven rule alert is there, the model checker still running, signing blocked
    assert st["open_alerts"] == 1 and st["qc_pending"] and not st["signable"]
    st, _ = await r.edit("X", "impression", "8 mm", "12 mm", "rad", "es")
    assert st["open_alerts"] == 0 and st["qc_pending"] and not st["signable"]
    with pytest.raises(Exception):
        r.sign("X", st["version"], "rad")
    release.set()
    for _ in range(50):
        await asyncio.sleep(0.01)
        if not r.state("X")["qc_pending"]:
            break
    assert r.state("X")["signable"]


def test_keepalive_touch_pings_a_warm_model():
    c, _, seen = make({"glimmer.test": [{"data": []}]}, [GLIMMER], env={"GLIMMER_KEEPALIVE_SECONDS": "0"})
    c.get("/api/resident")  # wakes
    n = len([x for x in seen if x[1].endswith("/models")])
    c.get("/api/resident?touch=1")
    assert len([x for x in seen if x[1].endswith("/models")]) == n + 1


def test_repeated_numbers_deduped():
    assert dedupe_numbers("El nódulo mide doce doce milímetros") == "El nódulo mide doce milímetros"
    assert dedupe_numbers("mide 12 12 mm") == "mide 12 mm" and dedupe_numbers("de de la") == "de de la"


def test_stricter_measurement_targets():
    assert measurement_edit("Nódulo de 12 x 8 mm en el LSD.", "nodulo", "15", "mm") is None  # two dimensions
    assert measurement_edit("Lesión en el lóbulo superior derecho, nódulo de 8 mm.", "nodulo", "12", "mm") is None  # not the subject
    assert measurement("El lóbulo superior mide 12 mm") == ("lobulo superior", "12", "mm")
    assert measurement_edit("Lóbulo superior de 8 mm.", "lobulo superior", "12", "mm") is None  # location word, not a lesion


def test_claim_after_read_only_tools_is_refused_and_questions_are_not_edits():
    hosts = {"glimmer.test": [tool_call("summarize_case", {"case_id": "DEMO-0004"}), final("Hecho, cambié a espiculados.")]}
    c, _, _ = make(hosts, [GLIMMER])
    r = c.post("/api/chat", json={"text": EDIT, "case_id": "DEMO-0004"}, headers=RAD).json()
    assert r["text"] == "No apliqué ningún cambio." and r["steps"] == ["summarize_case"]
    from oncall_core.commands import looks_like_edit
    assert not looks_like_edit("¿Cuánto mide el nódulo?") and looks_like_edit("cambia bordes lisos por espiculados")


def test_partial_failure_is_said_and_offered_again():
    hosts = {"glimmer.test": [{"choices": [{"message": {"role": "assistant", "content": "", "tool_calls": [
        {"id": "a", "type": "function", "function": {"name": "edit_report", "arguments": '{"case_id": "DEMO-0004", "section": "findings", "find": "bordes lisos", "replace": "bordes espiculados"}'}},
        {"id": "b", "type": "function", "function": {"name": "edit_report", "arguments": '{"case_id": "DEMO-0004", "section": "findings", "find": "no existe", "replace": "x"}'}},
    ]}, "finish_reason": "tool_calls"}]}]}
    c, _, _ = make(hosts, [GLIMMER])
    r = c.post("/api/chat", json={"text": EDIT, "case_id": "DEMO-0004"}, headers=RAD).json()
    assert r["text"].startswith("Cambio aplicado") and "No apliqué ningún cambio." in r["text"] and r["retry"] is True


async def test_background_qc_one_per_case():
    calls = []
    release = asyncio.Event()

    class SlowLLM:
        async def complete(self, *a, **k):
            calls.append(1)
            await release.wait()
            return {"content": "[]", "_usage": None}

    r = Reports(Store(":memory:"), QcContext(SlowLLM(), [GLIMMER]), background_qc=True)
    await r.draft("X", "TC.", "Nódulo de 12 mm.", "Nódulo de 12 mm.", "rad", "es")
    await asyncio.sleep(0.01)  # the check of v1 is running (waiting on the model)
    for v in ("13", "14", "15"):
        await r.edit("X", "findings", r.state("X")["findings"].split(" de ")[1].split(" mm")[0] + " mm", v + " mm", "rad", "es")
    await asyncio.sleep(0.05)
    assert len(calls) == 1  # three more edits while one check runs: no fan-out
    release.set()
    for _ in range(100):
        await asyncio.sleep(0.01)
        if not r.state("X")["qc_pending"]:
            break
    st = r.state("X")
    assert not st["qc_pending"] and st["version"] == 4 and len(calls) == 2  # one more run, on the latest version
