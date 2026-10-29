"""Muse Spark Open via Baseten (ANG-178): OpenAI-compatible chat client.

The model always reasons: each response carries ``message.reasoning_content``
apart from ``message.content``. This client returns both separately, and the
JSON parser works ONLY on ``content`` (never on the reasoning trace).

Configuration is 100% environment (nothing pinned in code):
- SPARK_OPEN_URL   (OpenAI-compatible base URL, e.g. the Baseten inference URL)
- SPARK_OPEN_MODEL (model id served on that endpoint)
- SPARK_OPEN_API_KEY (Baseten key; on this Mac it lives in the Keychain as
  `baseten-hack` and is injected only inside the command, never printed or
  written to files)

Only synthetic generation prompts and synthetic cases may be sent here:
this endpoint is external, so nothing from Orthanc or any real study
may ever go through this client (callers enforce it).

Per-call tokens (prompt, completion, reasoning_tokens) are appended by the
caller to radqc/gen/costos.jsonl via :func:`log_cost`.
"""
import json
import os
import re
import time
from dataclasses import dataclass

import httpx

ENV_URL = "SPARK_OPEN_URL"
ENV_MODEL = "SPARK_OPEN_MODEL"
ENV_KEY = "SPARK_OPEN_API_KEY"

RETRYABLE_STATUS = {429, 500, 502, 503, 504}

COST_LOG = "radqc/gen/costos.jsonl"


class SparkOpenError(Exception):
    """The Spark Open endpoint could not answer (network, timeout, non-2xx)."""


class SparkOpenConfigError(SparkOpenError):
    """Missing SPARK_OPEN_* environment configuration."""


@dataclass(frozen=True)
class SparkOpenConfig:
    base_url: str
    api_key: str
    model: str

    @classmethod
    def from_env(cls, env=os.environ) -> "SparkOpenConfig":
        base = (env.get(ENV_URL) or "").strip().rstrip("/")
        model = (env.get(ENV_MODEL) or "").strip()
        key = env.get(ENV_KEY) or ""
        missing = [k for k, v in ((ENV_URL, base), (ENV_MODEL, model), (ENV_KEY, key)) if not v]
        if missing:
            raise SparkOpenConfigError(f"missing env: {', '.join(missing)}")
        return cls(base, key, model)


@dataclass(frozen=True)
class SparkOpenAnswer:
    """One chat answer: content and reasoning kept apart, plus raw usage."""

    content: str
    reasoning_content: str
    usage: dict
    model: str


def token_counts(usage: dict | None) -> tuple[int, int, int]:
    """(prompt_tokens, completion_tokens, reasoning_tokens) from an OpenAI-style usage object.

    Reasoning tokens travel in ``usage.completion_tokens_details.reasoning_tokens``
    on OpenAI-compatible endpoints (top-level ``reasoning_tokens`` accepted too).
    Unknown counts are 0 (never shown as a real measurement elsewhere).
    """
    if not isinstance(usage, dict):
        return 0, 0, 0
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    details = usage.get("completion_tokens_details")
    reasoning = details.get("reasoning_tokens") if isinstance(details, dict) else None
    if reasoning is None:
        reasoning = usage.get("reasoning_tokens")
    ok = lambda n: n if isinstance(n, int) and n >= 0 else 0
    return ok(prompt), ok(completion), ok(reasoning)


def parse_json_content(content: str):
    """Parse JSON working ONLY on message content (never on reasoning_content)."""
    if not isinstance(content, str):
        raise SparkOpenError("empty content")
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        raise SparkOpenError("no JSON object in content")
    try:
        return json.loads(m.group(0))
    except ValueError as e:
        raise SparkOpenError("content is not valid JSON") from e


def _is_retryable(status: int) -> bool:
    return status in RETRYABLE_STATUS or 500 <= status <= 599


def _backoff(attempt: int, base_s: float = 1.0) -> float:
    return base_s * (2.0 ** attempt)


def chat(messages: list[dict], *, config: SparkOpenConfig | None = None,
         temperature: float = 0.8, max_tokens: int = 4000,
         timeout: float = 180.0, tries: int = 4,
         client: httpx.Client | None = None) -> SparkOpenAnswer:
    """One chat.completions call with backoff on 429/5xx. Returns content and reasoning apart."""
    cfg = config or SparkOpenConfig.from_env()
    body = {"model": cfg.model, "messages": messages,
            "temperature": temperature, "max_tokens": max_tokens}
    own = client is None
    http = client or httpx.Client()
    try:
        last: Exception | None = None
        for attempt in range(max(1, tries)):
            try:
                r = http.post(f"{cfg.base_url}/chat/completions",
                              headers={"authorization": f"Bearer {cfg.api_key}"},
                              json=body, timeout=timeout)
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last = SparkOpenError(type(e).__name__)
            else:
                if r.status_code == 200:
                    try:
                        data = r.json()
                        msg = data["choices"][0]["message"]
                    except (ValueError, KeyError, IndexError, TypeError) as e:
                        raise SparkOpenError("malformed response") from e
                    if not isinstance(msg, dict):
                        raise SparkOpenError("malformed response")
                    return SparkOpenAnswer(
                        content=str(msg.get("content") or ""),
                        reasoning_content=str(msg.get("reasoning_content") or ""),
                        usage=data.get("usage") if isinstance(data.get("usage"), dict) else {},
                        model=str(data.get("model") or cfg.model),
                    )
                if _is_retryable(r.status_code):
                    last = SparkOpenError(f"HTTP {r.status_code}")
                else:
                    raise SparkOpenError(f"HTTP {r.status_code}")
            if attempt < tries - 1:
                time.sleep(_backoff(attempt))
        raise last or SparkOpenError("no attempts made")
    finally:
        if own:
            http.close()


async def achat(messages: list[dict], *, config: SparkOpenConfig | None = None,
                temperature: float = 0.8, max_tokens: int = 4000,
                timeout: float = 180.0, tries: int = 4,
                client: httpx.AsyncClient | None = None) -> SparkOpenAnswer:
    """Async variant of :func:`chat` (same contract, same retries)."""
    import asyncio

    cfg = config or SparkOpenConfig.from_env()
    body = {"model": cfg.model, "messages": messages,
            "temperature": temperature, "max_tokens": max_tokens}
    own = client is None
    http = client or httpx.AsyncClient()
    try:
        last: Exception | None = None
        for attempt in range(max(1, tries)):
            try:
                r = await http.post(f"{cfg.base_url}/chat/completions",
                                    headers={"authorization": f"Bearer {cfg.api_key}"},
                                    json=body, timeout=timeout)
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last = SparkOpenError(type(e).__name__)
            else:
                if r.status_code == 200:
                    try:
                        data = r.json()
                        msg = data["choices"][0]["message"]
                    except (ValueError, KeyError, IndexError, TypeError) as e:
                        raise SparkOpenError("malformed response") from e
                    if not isinstance(msg, dict):
                        raise SparkOpenError("malformed response")
                    return SparkOpenAnswer(
                        content=str(msg.get("content") or ""),
                        reasoning_content=str(msg.get("reasoning_content") or ""),
                        usage=data.get("usage") if isinstance(data.get("usage"), dict) else {},
                        model=str(data.get("model") or cfg.model),
                    )
                if _is_retryable(r.status_code):
                    last = SparkOpenError(f"HTTP {r.status_code}")
                else:
                    raise SparkOpenError(f"HTTP {r.status_code}")
            if attempt < tries - 1:
                await asyncio.sleep(_backoff(attempt))
        raise last or SparkOpenError("no attempts made")
    finally:
        if own:
            await http.aclose()


def log_cost(path: str, purpose: str, answer: SparkOpenAnswer, seconds: float | None = None) -> dict:
    """Append one token row (prompt, completion, reasoning_tokens) to a JSONL log. Returns the row."""
    import datetime

    prompt, completion, reasoning = token_counts(answer.usage)
    row = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "purpose": purpose, "model": answer.model,
           "prompt_tokens": prompt, "completion_tokens": completion,
           "reasoning_tokens": reasoning}
    if seconds is not None:
        row["seconds"] = seconds
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row
