"""Tool-using resident: tries each provider in order and falls back to basic (rule) mode.

Every tool call is executed here (never by the model) and recorded in the store with time, tool, input,
short output, study ID and the model that asked for it, so each answer can be verified afterwards."""
import asyncio
import json
import time
from dataclasses import dataclass, field

from adapters.base import SourceUnavailable

from .i18n import t
from .llm import LLM, Provider, ProviderError, log_usage
from .prompts import SYSTEM
from .store import Store
from .commands import claims_change, looks_like_edit
from .tools import MUTATING, TOOL_NAMES, TOOL_SPECS, Toolbox, loggable_args

MAX_STEPS = 4
MIN_CALL_S = 3.0  # below this much time left, a provider call is not attempted
BASIC_RESERVE_S = 10.0  # part of the answer budget kept for basic mode


@dataclass
class Answer:
    text: str
    mode: str                      # agent | fallback | basic
    model: str | None
    steps: list[str] = field(default_factory=list)
    blocks: list[dict] = field(default_factory=list)
    retry: bool = False            # nothing was changed: the app offers to resend the same instruction


def _merge_blocks(acc: list[dict], new: list[dict]) -> list[dict]:
    """Keep the latest card of each kind (a later list replaces an earlier one, a case is added once)."""
    for b in new:
        if b["type"] == "case":
            acc = [x for x in acc if not (x["type"] == "case" and x["case"]["case_id"] == b["case"]["case_id"])]
        elif b["type"] == "report":
            acc = [x for x in acc if not (x["type"] == "report" and x["report"]["case_id"] == b["report"]["case_id"])]
        else:
            acc = [x for x in acc if x["type"] != b["type"]]
        acc.append(b)
    return acc


def _focus(blocks: list[dict]) -> list[dict]:
    """Show the most specific cards: a report beats the case it belongs to, a case beats the list consulted on
    the way."""
    reports = [b for b in blocks if b["type"] == "report"]
    if reports:
        return reports
    cases = [b for b in blocks if b["type"] == "case"]
    return cases or blocks


async def run_with_provider(llm: LLM, p: Provider, text: str, lang: str, toolbox: Toolbox, store: Store,
                            timeout: float, deadline: float | None = None, context: str = "") -> Answer:
    """`timeout` bounds each model call; `deadline` (monotonic) bounds the whole answer across tool rounds.
    `context` (active case, current draft) is screen state, sent as a separate message before the request."""
    messages = [{"role": "system", "content": SYSTEM[lang]}]
    if context:
        messages.append({"role": "user", "content": context})
    messages.append({"role": "user", "content": text})
    steps: list[str] = []
    blocks: list[dict] = []
    confirms: list[str] = []  # deterministic confirmations from tools that really changed something
    facts: list[str] = []  # one-line tool summaries: the answer if the model returns no text

    def text_or_facts(content: str | None) -> str:
        return (content or "").strip() or ("; ".join(facts[-2:]) + "." if facts else t(lang, "agent.empty"))

    mutation_failed: list[str] = []  # why a requested change did not happen (tool error / no real change)

    def no_change(reason: str | None = None) -> Answer:
        """Never confirm a change that no tool made: say so and offer to retry."""
        text = t(lang, "agent.no_change") + (f" {reason}" if reason else "")
        return Answer(text, p.mode, p.label, steps, _focus(blocks), retry=True)

    for _ in range(MAX_STEPS):
        left = timeout if deadline is None else min(timeout, deadline - time.monotonic())
        if left < MIN_CALL_S:
            raise ProviderError("answer deadline reached")
        msg = await llm.complete(p, messages, TOOL_SPECS, left)
        if not isinstance(msg, dict):
            raise ProviderError("malformed message")
        log_usage(store, p, msg.get("_usage"), "agent")
        calls = msg.get("tool_calls") or []
        if not isinstance(calls, list) or not all(isinstance(c, dict) and isinstance(c.get("function", {}), dict) for c in calls):
            raise ProviderError("malformed tool call")
        if not calls:
            content = (msg.get("content") or "").strip()
            if mutation_failed:
                return no_change(mutation_failed[-1])
            # no tool changed anything (read-only tools at most): cut off by the token limit, empty, text that
            # claims a change, or a request to change the report → never confirmed
            if claims_change(content) or looks_like_edit(text) or (not steps and (msg.get("_finish") == "length" or not content)):
                return no_change()
            return Answer(text_or_facts(content), p.mode, p.label, steps, _focus(blocks))
        messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
        for call in calls:
            name = call.get("function", {}).get("name", "")
            raw = call.get("function", {}).get("arguments") or "{}"
            try:
                args = raw if isinstance(raw, dict) else json.loads(raw) if isinstance(raw, str) else {}
            except ValueError:
                args = {}
            if not isinstance(args, dict):
                args = {}
            if name not in TOOL_NAMES:
                result_data, summary, case_id, ok, new_blocks = {"error": f"unknown tool {name}"}, f"unknown tool {name}", None, False, []
            else:
                try:
                    r = await toolbox.call(name, args)
                except SourceUnavailable:
                    # audit the attempted call, then propagate: PACS down is not a model problem.
                    # An audit write failure must never mask the PACS error.
                    try:
                        store.log("tool", name, input=loggable_args(name, args), output="PACS unavailable", case_id=args.get("case_id"),
                                  model=p.label, mode=p.mode, ok=False)
                    except Exception:
                        pass
                    raise
                result_data, summary, case_id, ok, new_blocks = r.data, r.summary, r.case_id, r.ok, r.blocks
            steps.append(name)
            if ok:
                facts.append(summary)
            blocks = _merge_blocks(blocks, new_blocks)
            store.log("tool", name, input=loggable_args(name, args), output=summary, case_id=case_id, model=p.label, mode=p.mode, ok=ok)
            messages.append({"role": "tool", "tool_call_id": call.get("id", name), "content": json.dumps(result_data, ensure_ascii=False)})
            if name in MUTATING:
                if ok and getattr(r, "changed", False):
                    confirms.append(r.confirm or summary)
                elif not ok:
                    mutation_failed.append(summary)
                else:
                    mutation_failed.append(t(lang, "agent.unchanged"))
        if confirms:
            # a tool really changed the report: answer with its result, no second model turn; a part that failed
            # in the same round is said too, and offered again
            failed = [f'{t(lang, "agent.no_change")} {m}' for m in mutation_failed]
            return Answer(" ".join(confirms + failed), p.mode, p.label, steps, _focus(blocks), retry=bool(failed))
    # step budget exhausted: answer with what the tools returned (never a change that did not happen)
    if mutation_failed:
        return no_change(mutation_failed[-1])
    return Answer(text_or_facts(None), p.mode, p.label, steps, _focus(blocks))


async def answer(llm: LLM, providers: list[Provider], timeouts: dict[str, float], text: str, lang: str,
                 toolbox: Toolbox, store: Store, basic, budget_s: float = 100.0, context: str = "") -> Answer:
    """`budget_s` caps the whole answer (all providers and tool rounds) so basic mode is always reached
    before the app's request timeout."""
    # model work (calls and tools) must finish before `deadline`; the rest is reserved for basic mode
    deadline = time.monotonic() + max(budget_s - BASIC_RESERVE_S, 0.0)
    for p in providers:
        left = deadline - time.monotonic()
        if left < MIN_CALL_S:
            break
        try:
            return await asyncio.wait_for(
                run_with_provider(llm, p, text, lang, toolbox, store, timeouts.get(p.name, 60.0), deadline, context), left)
        except (ProviderError, TimeoutError) as e:
            if isinstance(e, TimeoutError):
                e = ProviderError("answer deadline reached")
            # provider identity only in `model` (admin-only); the visible output is a generic reason
            store.log("chat", "provider_unavailable", output=str(e), model=p.label, mode=p.mode, ok=False)
        except SourceUnavailable:
            raise
    return await basic(text, lang)
