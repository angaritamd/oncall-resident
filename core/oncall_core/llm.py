"""OpenAI-compatible chat client with an ordered provider chain (configured from the environment)."""
import json
import os
import time
from dataclasses import dataclass

import httpx


# USD per 1M tokens (input, cached input, output); official Meta Model API pricing for the standard model.
# Glimmer runs on our own Modal GPU, billed by time, so it has no per-token price.
PRICES = {"muse-spark-1.3": (1.25, 0.15, 4.25)}


def usage_cost(model: str, usage: dict | None) -> tuple[int | None, int | None, float | None]:
    """(tokens_in, tokens_out, cost_usd) from an OpenAI-style `usage` object."""
    if not isinstance(usage, dict):
        return None, None, None
    tin, tout = usage.get("prompt_tokens"), usage.get("completion_tokens")
    if not isinstance(tin, int) or not isinstance(tout, int):
        return None, None, None
    price = PRICES.get(model)
    if not price:
        return tin, tout, None
    details = usage.get("prompt_tokens_details")
    cached = details.get("cached_tokens") if isinstance(details, dict) else 0
    cached = cached if isinstance(cached, int) and 0 <= cached <= tin else 0
    cost = ((tin - cached) * price[0] + cached * price[1] + tout * price[2]) / 1_000_000
    return tin, tout, round(cost, 6)


def log_usage(store, p: "Provider", usage, purpose: str) -> None:
    """One activity row per model call: tokens and, for per-token providers, cost."""
    tin, tout, cost = usage_cost(p.model, usage)
    shown = lambda n: "Sin dato" if n is None else str(n)  # unknown is never shown as 0
    store.log("llm", purpose, output=f"{shown(tin)}→{shown(tout)} tokens", model=p.label, mode=p.mode,
              tokens_in=tin, tokens_out=tout, cost_usd=cost)


class ProviderError(Exception):
    """The provider could not answer (network, timeout, non-2xx such as Modal's 404 for a stopped app).
    The message never names the provider: it ends up in the activity log that regular users see."""


@dataclass(frozen=True)
class Provider:
    name: str        # internal id, recorded in the activity log; never shown to regular users
    mode: str        # "agent" for the primary model, "fallback" for the backup
    base_url: str
    api_key: str
    model: str

    @property
    def label(self) -> str:
        return f"{self.name}:{self.model}"


def data_is_synthetic(env=os.environ) -> bool:
    """The external backup may only see synthetic data. That holds when the operator declares it
    (DATA_CLASSIFICATION=synthetic) AND the order metadata file itself is marked synthetic."""
    if env.get("DATA_CLASSIFICATION") != "synthetic":
        return False
    try:
        with open(env.get("CASES_FILE", "../demo/seed/cases.json"), encoding="utf-8") as f:
            return json.load(f).get("synthetic") is True
    except (OSError, ValueError):
        return False


def meta_api_enabled(env=os.environ) -> bool:
    """META_API_ENABLED=0 turns off every Meta Model API call (fallback model and voice) without removing the key.
    Only an affirmative value turns it on ("false", "off" or a typo turn it off); unset keeps it on."""
    return env.get("META_API_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"}


def providers_from_env(env=os.environ) -> list[Provider]:
    out = []
    if env.get("GLIMMER_BASE_URL") and env.get("GLIMMER_API_KEY"):
        out.append(Provider("glimmer", "agent", env["GLIMMER_BASE_URL"].rstrip("/"), env["GLIMMER_API_KEY"],
                            env.get("GLIMMER_MODEL", "muse-glimmer")))
    if env.get("MODEL_API_KEY") and data_is_synthetic(env) and meta_api_enabled(env):
        out.append(Provider("meta-model-api", "fallback", env.get("MODEL_API_BASE_URL", "https://api.meta.ai/v1").rstrip("/"),
                            env["MODEL_API_KEY"], env.get("MODEL_API_MODEL", "muse-spark-1.3")))
    return out


class LLM:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self.http = client or httpx.AsyncClient()

    async def complete(self, p: Provider, messages: list[dict], tools: list[dict] | None, timeout: float,
                       max_tokens: int = 1500) -> dict:
        """Returns the assistant message ({content, tool_calls?}) plus `_usage` (the response's usage object)."""
        body = {"model": p.model, "messages": messages, "temperature": 0.6,
                "max_tokens": max_tokens}  # room for the reasoning parser plus the answer
        if tools:
            body |= {"tools": tools, "tool_choice": "auto"}
        try:
            r = await self.http.post(
                f"{p.base_url}/chat/completions",
                headers={"authorization": f"Bearer {p.api_key}"},
                json=body,
                timeout=httpx.Timeout(timeout, connect=min(10.0, timeout)),
            )
        except httpx.HTTPError as e:
            raise ProviderError(type(e).__name__) from e
        if r.status_code != 200:
            raise ProviderError(f"HTTP {r.status_code}")
        try:
            data = r.json()
            msg = data["choices"][0]["message"]
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise ProviderError("malformed response") from e
        if isinstance(msg, dict):
            finish = data["choices"][0].get("finish_reason") if isinstance(data["choices"][0], dict) else None
            msg = {**msg, "_usage": data.get("usage"), "_finish": finish}
        return msg

    async def ping(self, p: Provider, timeout: float) -> bool:
        try:
            r = await self.http.get(f"{p.base_url}/models", headers={"authorization": f"Bearer {p.api_key}"},
                                    timeout=httpx.Timeout(timeout, connect=min(10.0, timeout)))
            return r.status_code == 200
        except httpx.HTTPError:
            return False


class Warmth:
    """Tracks whether the scale-to-zero primary model is probably warm, and wakes it in the background."""

    def __init__(self, scaledown_s: float = 300.0, retry_after_s: float = 60.0):
        self.scaledown_s = scaledown_s
        self.retry_after_s = retry_after_s
        self.last_ok: float | None = None
        self.failed_at: float | None = None
        self.waking = False

    def mark_ok(self):
        self.last_ok = time.monotonic()
        self.failed_at = None

    def mark_failed(self):
        self.failed_at = time.monotonic()

    def recently_failed(self) -> bool:
        return self.failed_at is not None and time.monotonic() - self.failed_at < self.retry_after_s

    def is_warm(self) -> bool:
        return self.last_ok is not None and time.monotonic() - self.last_ok < self.scaledown_s * 0.9
