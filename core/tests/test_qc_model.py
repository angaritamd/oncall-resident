"""GLIMMER_QC_MODEL: the checker asks the RAD·QC LoRA (radqc-v5) first, the chat stays on muse-glimmer; unset, nothing
changes (Miguel: the demo turns it on only if v5 beats the baseline on bench-v2)."""
import json
import os

os.environ["ONCALL_NO_APP"] = "1"

import httpx
from fastapi.testclient import TestClient

from oncall_core.llm import LLM, qc_providers
from oncall_core.main import create_app
from oncall_core.reports import QcContext, Reports
from oncall_core.store import Store
from tests.test_agent import GLIMMER, SPARK, final, tool_call
from tests.test_core import CASES, UIDS, FakeSource

F12 = "Nódulo sólido en el lóbulo superior derecho de 12 mm, de bordes lisos."
I8 = "Nódulo pulmonar sólido en el lóbulo superior derecho de 8 mm."
ISSUE = json.dumps({"issues": [{"type": "omitted_finding", "body_excerpt": F12, "impression_excerpt": "",
                                "explanation": "x"}]})


def by_model(answers: dict):
    """Glimmer answers per requested model (a status code, or the assistant content); records every model asked."""
    asked = []

    def handler(req: httpx.Request):
        body = json.loads(req.content or b"{}")
        asked.append(body.get("model"))
        a = answers.get(body.get("model"), 404)
        if isinstance(a, int):
            return httpx.Response(a, json={"error": {"message": "The model does not exist."}})
        return httpx.Response(200, json=a if isinstance(a, dict) else final(a))
    return httpx.AsyncClient(transport=httpx.MockTransport(handler)), asked


def test_unset_the_checker_uses_the_chat_providers():
    assert qc_providers([GLIMMER, SPARK], {}) == [GLIMMER, SPARK]
    assert qc_providers([GLIMMER, SPARK], {"GLIMMER_QC_MODEL": " "}) == [GLIMMER, SPARK]


def test_set_the_checker_asks_the_lora_then_base_glimmer_then_the_rest():
    got = qc_providers([GLIMMER, SPARK], {"GLIMMER_QC_MODEL": "radqc-v5"})
    assert [(p.name, p.model) for p in got] == [("glimmer", "radqc-v5"), ("glimmer", "muse-glimmer"),
                                                ("meta-model-api", "muse-spark-1.3")]
    assert qc_providers([SPARK], {"GLIMMER_QC_MODEL": "radqc-v5"}) == [SPARK]  # no Glimmer: nothing to swap


async def test_the_lora_answers_the_qc():
    client, asked = by_model({"radqc-v5": ISSUE})
    r = Reports(Store(":memory:"), QcContext(LLM(client), qc_providers([GLIMMER], {"GLIMMER_QC_MODEL": "radqc-v5"})))
    st = await r.draft("DEMO-0002", "TC.", F12, I8, "residente", "es")
    assert asked == ["radqc-v5"] and st["qc_mode"] != "rules"


async def test_lora_not_served_falls_back_to_base_glimmer():
    client, asked = by_model({"muse-glimmer": ISSUE})  # radqc-v5 -> 404 (glimmer_app without GLIMMER_LORA)
    r = Reports(Store(":memory:"), QcContext(LLM(client), qc_providers([GLIMMER], {"GLIMMER_QC_MODEL": "radqc-v5"})))
    st = await r.draft("DEMO-0002", "TC.", F12, I8, "residente", "es")
    assert asked == ["radqc-v5", "muse-glimmer"] and st["qc_mode"] != "rules"


def test_the_chat_stays_on_muse_glimmer():
    client, asked = by_model({"muse-glimmer": tool_call("list_pending", {}), "radqc-v5": ISSUE})
    app = create_app(FakeSource(list(UIDS.values())), str(CASES), store=Store(":memory:"), providers=[GLIMMER],
                     llm=LLM(client), env={"GLIMMER_COLD_THRESHOLD": "5", "GLIMMER_QC_MODEL": "radqc-v5"})
    TestClient(app).post("/api/chat", json={"text": "¿Qué tengo pendiente?"})
    assert set(asked) - {None} == {"muse-glimmer"}  # None: the wake ping, no body


async def test_the_checker_asks_for_qc_max_tokens_and_2500_fit_the_budget():
    from oncall_core import qc
    from tests.test_agent import scripted
    transport, seen = scripted({"glimmer.test": [final('{"issues": []}')]})
    ctx = QcContext(LLM(httpx.AsyncClient(transport=transport)), [GLIMMER])
    await Reports(Store(":memory:"), ctx).draft("DEMO-0002", "TC.", F12, F12, "residente", "es")
    assert seen[0][3]["max_tokens"] == qc.MAX_TOKENS == 2500
    # Glimmer with CUDA graphs: ~76 tok/s per request (train_v5 graphs_check, 31 Oct), 1 s for the prompt
    assert qc.MAX_TOKENS / 76 + 1 < ctx.timeout <= ctx.budget == 45


def test_qc_model_timeout_only_with_glimmer_qc_model():
    from oncall_core.llm import qc_model_timeout
    assert qc_model_timeout({}) == {}
    assert qc_model_timeout({"GLIMMER_QC_MODEL": "radqc-v5"}) == {"radqc-v5": 15.0}
    assert qc_model_timeout({"GLIMMER_QC_MODEL": "radqc-v5", "QC_MODEL_TIMEOUT": "20"}) == {"radqc-v5": 20.0}


def _down_glimmer(meta_answer):
    """Glimmer's server times out (cold or down) for every model; Meta answers."""
    asked = []

    def handler(req: httpx.Request):
        body = json.loads(req.content or b"{}")
        asked.append((req.url.host, body.get("model")))
        if req.url.host == "glimmer.test":
            raise httpx.ReadTimeout("cold")
        return httpx.Response(200, json=final(meta_answer))
    return httpx.AsyncClient(transport=httpx.MockTransport(handler)), asked


async def test_glimmer_down_skips_its_other_models_and_qc_reaches_meta():
    client, asked = _down_glimmer(ISSUE)
    ctx = QcContext(LLM(client), qc_providers([GLIMMER, SPARK], {"GLIMMER_QC_MODEL": "radqc-v5"}),
                    model_timeout={"radqc-v5": 15.0})
    st = await Reports(Store(":memory:"), ctx).draft("DEMO-0002", "TC.", F12, I8, "residente", "es")
    # radqc-v5 once, base Glimmer skipped (same server), then Meta answers
    assert asked == [("glimmer.test", "radqc-v5"), ("api.meta.test", SPARK.model)]
    assert st["qc_mode"] == "fallback"


async def test_a_4xx_for_the_adapter_still_tries_base_glimmer():
    client, asked = by_model({"muse-glimmer": '{"issues": []}'})  # radqc-v5 not served: 404
    ctx = QcContext(LLM(client), qc_providers([GLIMMER, SPARK], {"GLIMMER_QC_MODEL": "radqc-v5"}))
    st = await Reports(Store(":memory:"), ctx).draft("DEMO-0002", "TC.", F12, F12, "residente", "es")
    assert asked == ["radqc-v5", "muse-glimmer"] and st["qc_mode"] == "agent"
