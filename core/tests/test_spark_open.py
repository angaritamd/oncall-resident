"""Spark Open client (ANG-178): reasoning/content split, content-only JSON, 429/5xx retries, token counts."""
import json

import httpx
import pytest

from oncall_core import spark_open
from oncall_core.spark_open import SparkOpenConfig, SparkOpenError, chat, parse_json_content, token_counts


def cfg():
    return SparkOpenConfig("http://localhost:9", "k", "m")


def ok_transport(payload, status=200, calls=None):
    def handler(request):
        if calls is not None:
            calls.append(request)
        return httpx.Response(status, json=payload)
    return httpx.MockTransport(handler)


def test_reasoning_returned_apart_and_parser_uses_only_content():
    payload = {"model": "m", "choices": [{"message": {
        "content": 'Razoné mucho. {"a": 1}',
        "reasoning_content": '{"a": 999, "trampa": true}'}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5,
                  "completion_tokens_details": {"reasoning_tokens": 3}}}
    ans = chat([{"role": "user", "content": "Say OK"}], config=cfg(),
               client=httpx.Client(transport=ok_transport(payload)))
    assert ans.reasoning_content == '{"a": 999, "trampa": true}'
    assert parse_json_content(ans.content) == {"a": 1}
    assert token_counts(ans.usage) == (10, 5, 3)


def test_retry_on_429_then_ok():
    payload = {"model": "m", "choices": [{"message": {"content": "OK"}}], "usage": {}}
    seq = [httpx.Response(429, json={}), httpx.Response(200, json=payload)]
    calls = []
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: calls.append(r) or seq.pop(0)))
    ans = chat([{"role": "user", "content": "Say OK"}], config=cfg(), client=client)
    assert ans.content == "OK" and len(calls) == 2


def test_no_retry_on_400():
    calls = []
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: calls.append(r) or httpx.Response(400, json={})))
    with pytest.raises(SparkOpenError):
        chat([{"role": "user", "content": "Say OK"}], config=cfg(), tries=3, client=client)
    assert len(calls) == 1


def test_missing_env_raises_config_error():
    with pytest.raises(SparkOpenError):
        SparkOpenConfig.from_env({})


def test_log_cost_writes_token_row(tmp_path, monkeypatch):
    monkeypatch.setattr(spark_open, "COST_LOG", str(tmp_path / "costos.jsonl"))
    ans = spark_open.SparkOpenAnswer("OK", "pensé", {"prompt_tokens": 7, "completion_tokens": 2,
                                                     "completion_tokens_details": {"reasoning_tokens": 1}}, "m")
    row = spark_open.log_cost(str(tmp_path / "costos.jsonl"), "smoke", ans, seconds=1.2)
    assert (row["prompt_tokens"], row["completion_tokens"], row["reasoning_tokens"]) == (7, 2, 1)
    assert json.loads((tmp_path / "costos.jsonl").read_text().strip())["purpose"] == "smoke"
