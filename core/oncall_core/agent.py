"""Tool-using resident: tries each provider in order and falls back to basic (rule) mode.

Every tool call is executed here (never by the model) and recorded in the store with time, tool, input,
short output, study ID and the model that asked for it, so each answer can be verified afterwards."""
import json
from dataclasses import dataclass, field

from adapters.base import SourceUnavailable

from .i18n import t
from .llm import LLM, Provider, ProviderError
from .prompts import SYSTEM
from .store import Store
from .tools import TOOL_NAMES, TOOL_SPECS, Toolbox

MAX_STEPS = 4


@dataclass
class Answer:
    text: str
    mode: str                      # agent | fallback | basic
    model: str | None
    steps: list[str] = field(default_factory=list)
    blocks: list[dict] = field(default_factory=list)


def _merge_blocks(acc: list[dict], new: list[dict]) -> list[dict]:
    """Keep the latest card of each kind (a later list replaces an earlier one, a case is added once)."""
    for b in new:
        if b["type"] == "case":
            acc = [x for x in acc if not (x["type"] == "case" and x["case"]["case_id"] == b["case"]["case_id"])]
        else:
            acc = [x for x in acc if x["type"] != b["type"]]
        acc.append(b)
    return acc


def _focus(blocks: list[dict]) -> list[dict]:
    """When the answer opened a case, show the case card(s) only, not the list consulted on the way."""
    cases = [b for b in blocks if b["type"] == "case"]
    return cases or blocks


async def run_with_provider(llm: LLM, p: Provider, text: str, lang: str, toolbox: Toolbox, store: Store,
                            timeout: float) -> Answer:
    messages = [{"role": "system", "content": SYSTEM[lang]}, {"role": "user", "content": text}]
    steps: list[str] = []
    blocks: list[dict] = []
    for _ in range(MAX_STEPS):
        msg = await llm.complete(p, messages, TOOL_SPECS, timeout)
        calls = msg.get("tool_calls") or []
        if not calls:
            return Answer((msg.get("content") or "").strip() or t(lang, "agent.empty"), p.mode, p.label, steps, _focus(blocks))
        messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
        for call in calls:
            name = call.get("function", {}).get("name", "")
            try:
                args = json.loads(call.get("function", {}).get("arguments") or "{}")
                if not isinstance(args, dict):
                    raise ValueError
            except ValueError:
                args = {}
            if name not in TOOL_NAMES:
                result_data, summary, case_id, ok, new_blocks = {"error": f"unknown tool {name}"}, f"unknown tool {name}", None, False, []
            else:
                r = await toolbox.call(name, args)  # SourceUnavailable propagates: PACS down is not a model problem
                result_data, summary, case_id, ok, new_blocks = r.data, r.summary, r.case_id, r.ok, r.blocks
            steps.append(name)
            blocks = _merge_blocks(blocks, new_blocks)
            store.log("tool", name, input=args, output=summary, case_id=case_id, model=p.label, mode=p.mode, ok=ok)
            messages.append({"role": "tool", "tool_call_id": call.get("id", name), "content": json.dumps(result_data, ensure_ascii=False)})
    # step budget exhausted: answer with what the tools returned
    return Answer(t(lang, "agent.empty"), p.mode, p.label, steps, _focus(blocks))


async def answer(llm: LLM, providers: list[Provider], timeouts: dict[str, float], text: str, lang: str,
                 toolbox: Toolbox, store: Store, basic) -> Answer:
    for p in providers:
        try:
            return await run_with_provider(llm, p, text, lang, toolbox, store, timeouts.get(p.name, 60.0))
        except ProviderError as e:
            store.log("chat", "provider_unavailable", output=str(e), model=p.label, mode=p.mode, ok=False)
        except SourceUnavailable:
            raise
    return await basic(text, lang)
