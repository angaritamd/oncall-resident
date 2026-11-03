"""Meta Model API spend cap (META_API_MAX_USD, Miguel: US$ 10 in the demo). The fallback only runs when Glimmer fails,
and no Meta call starts once the recorded Meta spend reaches the cap."""
import os

os.environ["ONCALL_NO_APP"] = "1"

import httpx
from fastapi.testclient import TestClient

from oncall_core.llm import LLM, MetaCap
from oncall_core.main import create_app
from oncall_core.reports import QcContext, Reports
from oncall_core.store import Store
from tests.test_agent import GLIMMER, SPARK, final, scripted, tool_call
from tests.test_core import CASES, UIDS, FakeSource
from tests.test_voice import fake_meta

F12 = "Nódulo sólido en el lóbulo superior derecho de 12 mm, de bordes lisos."
I8 = "Nódulo pulmonar sólido en el lóbulo superior derecho de 8 mm."


def spend(store, usd):
    store.log("llm", "agent", model="meta-model-api:muse-spark-1.3", mode="fallback", tokens_in=1, tokens_out=1,
              cost_usd=usd)


def make(spent, cap="10", transcriber=None):
    transport, seen = scripted({"glimmer.test": 404,
                                "api.meta.test": [tool_call("list_pending", {}), final("Tienes 5 estudios.")]})
    store = Store(":memory:")
    spend(store, spent)
    app = create_app(FakeSource(list(UIDS.values())), str(CASES), store=store, providers=[GLIMMER, SPARK],
                     llm=LLM(httpx.AsyncClient(transport=transport)), transcriber=transcriber,
                     env={"GLIMMER_COLD_THRESHOLD": "5", "META_API_MAX_USD": cap})
    return TestClient(app), store, seen


def test_cap_counts_every_meta_row_and_logs_once():
    store = Store(":memory:")
    cap = MetaCap(store, 10.0)
    spend(store, 6.0)
    store.log("llm", "transcribe", model="meta:muse-voice-transcribe-1.0", mode="voice", cost_usd=3.99)
    store.log("llm", "agent", model="glimmer:muse-glimmer", mode="agent", tokens_in=1, tokens_out=1)  # not Meta
    assert round(cap.spent(), 2) == 9.99 and cap.ok() and cap.allows(SPARK)
    spend(store, 0.01)
    assert not cap.ok() and not cap.allows(SPARK) and cap.allows(GLIMMER)
    cap.ok()
    assert len([x for x in store.recent() if x["name"] == "meta_cap_reached"]) == 1
    assert MetaCap(store, None).ok()  # unset: no cap
    unpriced = Store(":memory:")
    unpriced.log("llm", "agent", model="meta-model-api:muse-spark-1.3", mode="fallback")  # answer without usage
    assert unpriced.meta_spend() == 0.01  # counted at the worst case, never free
    assert not MetaCap(Store(":memory:"), 10.0, model="muse-unpriced").ok()  # spend could not be counted: refused


def test_below_the_cap_glimmer_down_falls_back_to_meta():
    c, _, seen = make(spent=9.0)
    r = c.post("/api/chat", json={"text": "¿Qué tengo pendiente?"}).json()
    assert r["mode"] == "fallback" and "api.meta.test" in [s[0] for s in seen]


def test_at_the_cap_the_chat_uses_basic_mode_and_never_calls_meta():
    c, store, seen = make(spent=10.0)
    r = c.post("/api/chat", json={"text": "¿Qué tengo pendiente?"}).json()
    assert r["mode"] == "basic" and "5 estudios" in r["text"]
    assert "api.meta.test" not in [s[0] for s in seen]
    assert any(x["name"] == "meta_cap_reached" for x in store.recent())


async def test_at_the_cap_qc_runs_the_rules_only_and_never_calls_meta():
    transport, seen = scripted({"glimmer.test": 404, "api.meta.test": [final('{"issues": []}')]})
    store = Store(":memory:")
    spend(store, 10.0)
    cap = MetaCap(store, 10.0)
    r = Reports(store, QcContext(LLM(httpx.AsyncClient(transport=transport)), [GLIMMER, SPARK], allow=cap.allows))
    st = await r.draft("DEMO-0002", "TC.", F12, I8, "residente", "es")
    assert st["qc_mode"] == "rules" and st["open_alerts"] == 1
    assert [s[0] for s in seen] == ["glimmer.test"]


def test_at_the_cap_meta_voice_is_unavailable():
    sent = []
    c, _, _ = make(spent=10.0, transcriber=fake_meta(seen=sent))
    assert c.get("/api/voice/config").json() == {"available": False, "provider": None}
    r = c.post("/api/transcribe", content=b"RIFF")
    assert r.status_code == 503 and "tope" in r.json()["detail"] and sent == []
    below, _, _ = make(spent=1.0, transcriber=fake_meta())
    assert below.get("/api/voice/config").json() == {"available": True, "provider": "meta"}
