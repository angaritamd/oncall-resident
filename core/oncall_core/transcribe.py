"""Speech to text for the composer's microphone. TRANSCRIBE_PROVIDER selects the engine:

- `meta`: Muse Voice Transcribe (`muse-voice-transcribe-1.0`) on the Meta Model API, `POST /v1/asr/transcribe`
  (multipart: a JSON `request` part and a WAV `audio` part). Like the text backup it only runs when the data is
  declared and marked synthetic (DATA_CLASSIFICATION=synthetic + "synthetic": true in cases.json).
- `local`: Whisper on the hospital node, for real data. Only the interface exists today (not configured → 503).

Audio is WAV only (RIFF, mono PCM16, 16 or 24 kHz), as the Meta API requires; the app records it that way.
Neither the audio nor the transcript is stored: the activity log keeps duration, latency and cost only.
"""
import json
import os
import re
import struct
import time
from dataclasses import dataclass

import httpx

from .llm import data_is_synthetic

META_MODEL = "muse-voice-transcribe-1.0"
USD_PER_HOUR = 0.18  # official price, metered in whole seconds rounded down
MAX_BYTES = 2_000_000  # ~60 s of 16 kHz mono PCM16
# terms the radiologist says that a general model may miss
KEYWORDS = ["DEMO", "neumotórax", "nódulo", "milímetros", "lateralidad", "impresión", "hallazgos", "previos", "RAD QC"]


_NUMBER_WORDS = ("cero un uno una dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince dieciseis "
                 "diecisiete dieciocho diecinueve veinte treinta cuarenta cincuenta sesenta setenta ochenta noventa cien "
                 "dieciséis veintiuno veintidós veintitrés veinticuatro veinticinco veintiséis veintisiete veintiocho "
                 "veintinueve").split()
_REPEATED_NUMBER = re.compile(r"\b(\d+(?:[.,]\d+)?|" + "|".join(_NUMBER_WORDS) + r")(?:\s+\1\b)+", re.I)


def dedupe_numbers(text: str) -> str:
    """'doce doce milímetros' → 'doce milímetros': the recognizer sometimes repeats a number. Only numbers, only
    immediate repetitions (a dictated '12 12' is not a real measurement either way)."""
    return _REPEATED_NUMBER.sub(r"\1", text)


class TranscribeError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code, self.message = code, message


@dataclass
class Transcript:
    text: str
    audio_ms: int
    latency_ms: int
    provider: str
    cost_usd: float | None


def wav_info(data: bytes) -> tuple[int, int]:
    """(sample_rate, duration_ms) of a mono PCM16 WAV at 16/24 kHz; anything else is rejected."""
    if len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise TranscribeError(415, "El audio debe ser WAV")
    pos, fmt, size = 12, None, None
    while pos + 8 <= len(data):
        cid, clen = data[pos:pos + 4], struct.unpack("<I", data[pos + 4:pos + 8])[0]
        if cid == b"fmt " and clen >= 16:
            fmt = struct.unpack("<HHIIHH", data[pos + 8:pos + 24])
        elif cid == b"data":
            size = min(clen, len(data) - pos - 8)
            break
        pos += 8 + clen + (clen & 1)
    if not fmt or size is None:
        raise TranscribeError(415, "WAV sin formato o sin datos")
    audio_format, channels, rate, _, _, bits = fmt
    if audio_format != 1 or channels != 1 or bits != 16 or rate not in (16000, 24000):
        raise TranscribeError(415, "WAV debe ser mono PCM de 16 bits a 16 o 24 kHz")
    return rate, int(size / 2 / rate * 1000)


class Transcriber:
    name = "none"

    async def transcribe(self, wav: bytes, lang: str) -> Transcript:  # pragma: no cover - interface
        raise NotImplementedError


class MetaTranscriber(Transcriber):
    name = "meta"

    def __init__(self, api_key: str, base_url: str = "https://api.meta.ai/v1", client: httpx.AsyncClient | None = None,
                 timeout: float = 20.0):
        self.api_key, self.base_url, self.timeout = api_key, base_url.rstrip("/"), timeout
        self.client = client or httpx.AsyncClient()

    async def transcribe(self, wav: bytes, lang: str) -> Transcript:
        _, audio_ms = wav_info(wav)
        req = {"model": META_MODEL, "audioEncoding": "WAV", "mode": "PUSH_TO_TALK", "keywords": KEYWORDS,
               "languageBias": ["English" if lang == "en" else "Spanish"]}
        t0 = time.monotonic()
        try:
            r = await self.client.post(
                f"{self.base_url}/asr/transcribe",
                headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"},
                files={"request": (None, json.dumps(req), "application/json"), "audio": ("voz.wav", wav, "audio/wav")},
                timeout=self.timeout)
        except httpx.HTTPError:
            raise TranscribeError(502, "El servicio de transcripción no responde")
        latency = int((time.monotonic() - t0) * 1000)
        if r.status_code != 200:
            # never echo the provider's body: it may carry request details
            raise TranscribeError(502, f"La transcripción falló ({r.status_code})")
        try:
            body = r.json()
        except ValueError:
            raise TranscribeError(502, "Respuesta de transcripción inválida")
        text = body.get("transcript") if isinstance(body, dict) else None
        if not isinstance(text, str):
            raise TranscribeError(502, "Respuesta de transcripción inválida")
        billed_ms = body.get("audioDurationMs") if isinstance(body.get("audioDurationMs"), int) else audio_ms
        cost = round((billed_ms // 1000) * USD_PER_HOUR / 3600, 6)
        return Transcript(dedupe_numbers(text.strip()), billed_ms, latency, self.name, cost)


class LocalTranscriber(Transcriber):
    """Whisper on the hospital node (real data never leaves it). Interface only: not configured today."""
    name = "local"

    def __init__(self, url: str | None = None):
        self.url = url

    async def transcribe(self, wav: bytes, lang: str) -> Transcript:
        wav_info(wav)
        raise TranscribeError(503, "Transcripción local (Whisper en el nodo) no configurada")


def transcriber_from_env(env=os.environ) -> Transcriber | None:
    """None when voice is unavailable (the app shows the microphone as unavailable, never simulated)."""
    provider = env.get("TRANSCRIBE_PROVIDER", "meta")
    if provider == "local":
        return LocalTranscriber(env.get("WHISPER_URL"))
    if provider == "meta" and env.get("MODEL_API_KEY") and data_is_synthetic(env):
        return MetaTranscriber(env["MODEL_API_KEY"], env.get("MODEL_API_BASE_URL", "https://api.meta.ai/v1"))
    return None
