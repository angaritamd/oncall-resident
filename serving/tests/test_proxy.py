import sys
from pathlib import Path

import httpx
import pytest

# upstream responses are streamed raw, so the fake upstream must return an unread stream

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from proxy import authorized, create_proxy  # noqa: E402

KEY = "k" * 64


def upstream(request: httpx.Request) -> httpx.Response:
    assert "authorization" not in request.headers  # the client's key is never forwarded to vLLM
    body = ('{"path": "%s"}' % request.url.path).encode()
    return httpx.Response(200, headers={"content-type": "application/json"}, stream=httpx.ByteStream(body))


@pytest.fixture
def client():
    fake = httpx.AsyncClient(transport=httpx.MockTransport(upstream), base_url="http://vllm")
    app = create_proxy("http://vllm", KEY, client=fake)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://proxy")


@pytest.mark.parametrize("method,path", [
    ("GET", "/health"), ("GET", "/v1/models"), ("POST", "/v1/chat/completions"),
    ("POST", "/invocations"), ("GET", "/metrics"), ("GET", "/"),
])
async def test_every_route_requires_the_key(client, method, path):
    for headers in ({}, {"authorization": "Bearer wrong"}, {"authorization": KEY}, {"authorization": "Basic " + KEY}):
        r = await client.request(method, path, headers=headers)
        assert r.status_code == 401, (path, headers)


async def test_valid_key_is_forwarded(client):
    r = await client.post("/v1/chat/completions", headers={"authorization": f"Bearer {KEY}"}, json={})
    assert r.status_code == 200 and r.json() == {"path": "/v1/chat/completions"}


def test_refuses_to_start_without_key():
    with pytest.raises(RuntimeError):
        create_proxy("http://vllm", "")


def test_authorized_edge_cases():
    assert authorized(f"Bearer {KEY}", KEY)
    assert not authorized(None, KEY) and not authorized("Bearer ", KEY) and not authorized(f"Bearer {KEY}", "")


def test_wait_ready_fails_fast_when_vllm_exits(monkeypatch):
    import importlib, subprocess, types, time
    fake_modal = types.SimpleNamespace(
        Image=types.SimpleNamespace(from_registry=lambda *a, **k: types.SimpleNamespace(
            entrypoint=lambda *a: types.SimpleNamespace(env=lambda *a: types.SimpleNamespace(add_local_python_source=lambda *a: None)))),
        Volume=types.SimpleNamespace(from_name=lambda *a, **k: None),
        Secret=types.SimpleNamespace(from_name=lambda *a, **k: None),
        App=lambda *a: types.SimpleNamespace(function=lambda **k: (lambda f: f)),
        concurrent=lambda **k: (lambda f: f), web_server=lambda **k: (lambda f: f),
    )
    monkeypatch.setitem(sys.modules, "modal", fake_modal)
    glimmer_app = importlib.import_module("glimmer_app")
    proc = subprocess.Popen([sys.executable, "-c", "raise SystemExit(3)"])
    t0 = time.time()
    with pytest.raises(RuntimeError, match="exited during startup with code 3"):
        glimmer_app._wait_ready(proc, 59999, 600)
    assert time.time() - t0 < 10


def test_the_adapter_is_served_only_with_glimmer_lora(monkeypatch):
    import importlib, types
    chain = types.SimpleNamespace(entrypoint=lambda *a: types.SimpleNamespace(
        env=lambda *a: types.SimpleNamespace(add_local_python_source=lambda *a: None)))
    monkeypatch.setitem(sys.modules, "modal", types.SimpleNamespace(
        Image=types.SimpleNamespace(from_registry=lambda *a, **k: chain),
        Volume=types.SimpleNamespace(from_name=lambda *a, **k: None),
        Secret=types.SimpleNamespace(from_name=lambda *a, **k: None),
        App=lambda *a: types.SimpleNamespace(function=lambda **k: (lambda f: f)),
        concurrent=lambda **k: (lambda f: f), web_server=lambda **k: (lambda f: f)))
    monkeypatch.delenv("GLIMMER_LORA", raising=False)
    sys.modules.pop("glimmer_app", None)
    ga = importlib.import_module("glimmer_app")
    assert not ga.LORA and "--enable-lora" not in ga.vllm_cmd()  # the demo as today unless GLIMMER_LORA=1
    cmd = ga.vllm_cmd(lora=True)
    assert cmd[cmd.index("--lora-modules") + 1] == "radqc-v5=/lora/radqc-v5" and "--enforce-eager" in cmd
    assert cmd[cmd.index("--limit-mm-per-prompt") + 1] == '{"image": 0, "video": 0}'
    sys.modules.pop("glimmer_app", None)
