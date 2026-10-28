"""Voice: Muse Voice Transcribe (Meta Model API) behind TRANSCRIBE_PROVIDER, with the synthetic TTS clips."""
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from oncall_core.main import create_app
from oncall_core.store import Store
from oncall_core.transcribe import (LocalTranscriber, MetaTranscriber, TranscribeError, transcriber_from_env,
                                    wav_info)

from test_core import CASES, UIDS, FakeSource

AUDIO = Path(__file__).resolve().parents[2] / "app/e2e/audio"
CLIPS = {"que-tengo-pendiente.wav": "¿Qué tengo pendiente?", "abre-el-siguiente.wav": "Abre el siguiente.",
         "nodulo-12mm.wav": "El nódulo mide 12 mm."}


def fake_meta(text="¿Qué tengo pendiente?", status=200, seen=None):
    def handler(request: httpx.Request):
        if seen is not None:
            seen.append(request)
        if status != 200:
            return httpx.Response(status, json={"error": "secret detail"})
        return httpx.Response(200, json={"sessionId": "s", "transcript": f" {text} ", "audioDurationMs": 2075, "turns": []})
    return MetaTranscriber("k", client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def app(transcriber):
    store = Store(":memory:")
    a = create_app(FakeSource(list(UIDS.values())), str(CASES), store=store, providers=[], env={}, transcriber=transcriber)
    return TestClient(a), store


def test_clips_are_wav_the_api_accepts():
    for name in CLIPS:
        rate, ms = wav_info((AUDIO / name).read_bytes())
        assert rate == 16000 and 500 < ms < 6000


async def test_meta_request_shape_and_cost():
    seen = []
    tr = await fake_meta(seen=seen).transcribe((AUDIO / "nodulo-12mm.wav").read_bytes(), "es")
    req = seen[0]
    assert req.url.path == "/v1/asr/transcribe" and req.headers["authorization"] == "Bearer k"
    assert b'name="request"' in req.content and b'name="audio"' in req.content and b"RIFF" in req.content
    part = req.content.split(b'name="request"')[1].split(b"\r\n\r\n", 1)[1].split(b"\r\n--")[0]
    sent = json.loads(part)
    assert sent["model"] == "muse-voice-transcribe-1.0" and sent["audioEncoding"] == "WAV" and sent["languageBias"] == ["Spanish"]
    assert tr.text == "¿Qué tengo pendiente?" and tr.audio_ms == 2075
    assert tr.cost_usd == round(2 * 0.18 / 3600, 6)  # whole seconds, rounded down


async def test_non_wav_and_wrong_format_rejected():
    with pytest.raises(TranscribeError) as e:
        await fake_meta().transcribe(b"OggS" + b"\0" * 100, "es")
    assert e.value.code == 415


async def test_provider_error_is_not_echoed():
    with pytest.raises(TranscribeError) as e:
        await fake_meta(status=401).transcribe((AUDIO / "abre-el-siguiente.wav").read_bytes(), "es")
    assert e.value.code == 502 and "secret" not in e.value.message


def test_endpoint_logs_latency_and_cost_never_words():
    c, store = app(fake_meta("El nódulo mide 12 mm."))
    r = c.post("/api/transcribe", content=(AUDIO / "nodulo-12mm.wav").read_bytes(), headers={"content-type": "audio/wav"})
    assert r.status_code == 200 and r.json()["text"] == "El nódulo mide 12 mm." and r.json()["provider"] == "meta"
    rows = store.recent()
    assert any(x["kind"] == "voice" and "ms de audio" in x["output"] for x in rows)
    assert all("nódulo" not in json.dumps(x, ensure_ascii=False) for x in rows)
    assert store.spend("2000-01-01")["usd_priced"] > 0


def test_voice_never_signs():
    # a transcript reaches the chat like typed text: "fírmalo" gets the refusal and the report stays a draft
    c, _ = app(fake_meta("Fírmalo."))
    text = c.post("/api/transcribe", content=(AUDIO / "abre-el-siguiente.wav").read_bytes()).json()["text"]
    r = c.post("/api/chat", json={"text": text, "case_id": "DEMO-0004"}, headers={"x-resident-login": "rad@example.com"}).json()
    assert r["steps"] == ["sign_refused"]
    assert c.get("/api/reports/DEMO-0004").status_code == 404 or c.get("/api/reports/DEMO-0004").json()["status"] == "draft"


def test_voice_commands_from_transcripts():
    c, _ = app(fake_meta("Abre el siguiente."))
    text = c.post("/api/transcribe", content=(AUDIO / "abre-el-siguiente.wav").read_bytes()).json()["text"]
    r = c.post("/api/chat", json={"text": text, "case_id": "DEMO-0001"}).json()
    assert r["steps"] == ["open_next"] and r["blocks"][0]["case"]["case_id"] == "DEMO-0002"


def test_provider_selection_and_synthetic_gate(tmp_path):
    base = {"MODEL_API_KEY": "k", "CASES_FILE": str(CASES)}
    assert transcriber_from_env(base) is None  # no DATA_CLASSIFICATION=synthetic → nothing goes to Meta
    assert isinstance(transcriber_from_env(base | {"DATA_CLASSIFICATION": "synthetic"}), MetaTranscriber)
    assert isinstance(transcriber_from_env({"TRANSCRIBE_PROVIDER": "local"}), LocalTranscriber)
    c, _ = app(None)
    assert c.get("/api/voice/config").json() == {"available": False, "provider": None}
    assert c.post("/api/transcribe", content=b"RIFF").status_code == 503


def test_local_is_an_interface_only():
    c, _ = app(LocalTranscriber())
    r = c.post("/api/transcribe", content=(AUDIO / "abre-el-siguiente.wav").read_bytes())
    assert r.status_code == 503 and "Whisper" in r.json()["detail"]


def test_oversized_audio_rejected():
    c, _ = app(fake_meta())
    assert c.post("/api/transcribe", content=b"RIFF" + b"\0" * 2_000_001).status_code == 413
