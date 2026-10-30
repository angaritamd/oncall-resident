"""Score the deployed checker on the benchmark: rules + Glimmer, production parameters, no Meta fallback.

`run` goes inside the hack core container (oncall_core from /srv, this package copied next to it). It writes one JSONL
per pass with, per case, the raw model answer and the issue types of the whole system (rules + model, merged) and of
Glimmer alone (model only), so the passes can be scored again without calls when labels change. `summary` scores them
with radqc.score: mean and range across passes, per subtype, whole system and Glimmer alone.

Cost cap: Glimmer is billed by GPU time, so the cap is a time cap. No call starts once the GPU time so far, plus one
call (QcContext.budget) and the scale-down window, would pass --max-usd at --gpu-usd-hour.

  PYTHONPATH=/tmp/radqc:/srv python -m radqc.baseline run --bench bench-v2.jsonl --out out --passes 3 --max-usd 2.5
  PYTHONPATH=.:../core python -m radqc.baseline summary --bench data/bench/bench-v2.jsonl out/pass*.jsonl
"""
import argparse
import asyncio
import json
import time

from radqc.score import load, report

TIMEOUT, CONCURRENCY, SCALEDOWN_S = 45.0, 4, 300  # QcContext.budget; calls at a time; Modal scaledown_window
H100_USD_HOUR = 3.95                               # Modal H100 list price


def types(issues) -> list[str]:
    return sorted({i.rule for i in issues})


async def run(bench: str, out: str, passes: int, max_usd: float, gpu_usd_hour: float, model: str | None) -> dict:
    from oncall_core import qc
    from oncall_core.llm import LLM, ProviderError, providers_from_env

    glimmer = [p for p in providers_from_env() if p.name == "glimmer"][0]  # never the Meta fallback
    if model:  # a LoRA served next to the base model
        glimmer = glimmer.__class__(glimmer.name, glimmer.mode, glimmer.base_url, glimmer.api_key, model)
    cases = load(bench)
    llm = LLM()
    t_wake = time.monotonic()
    stop_after = max_usd / gpu_usd_hour * 3600 - SCALEDOWN_S - TIMEOUT

    async def one(c, sem):
        async with sem:
            if time.monotonic() - t_wake > stop_after:
                return {"id": c["id"], "error": "cost cap"}
            rules = qc.rule_issues(c["findings"], c["impression"])
            s = time.monotonic()
            try:
                msg = await llm.complete(glimmer, qc.qc_messages("es", c["indication"], c["findings"], c["impression"]),
                                         None, TIMEOUT, max_tokens=1200)
            except ProviderError as e:
                return {"id": c["id"], "error": str(e), "seconds": round(time.monotonic() - s, 1), "rules": types(rules)}
            content = msg.get("content") if isinstance(msg, dict) else None
            model_issues = qc.parse_model_issues(content, c["indication"], c["findings"], c["impression"])
            u = msg.get("_usage") or {}
            return {"id": c["id"], "raw": content, "finish": msg.get("_finish"),
                    "seconds": round(time.monotonic() - s, 1),
                    "tokens_in": u.get("prompt_tokens"), "tokens_out": u.get("completion_tokens"),
                    "rules": types(rules), "glimmer": [{"type": t} for t in types(model_issues)],
                    "system": [{"type": t} for t in types(qc.merge(rules, model_issues))]}

    log = {"model": glimmer.model, "wake_ok": await llm.ping(glimmer, timeout=900),
           "wake_seconds": round(time.monotonic() - t_wake, 1), "passes": []}
    print(json.dumps(log), flush=True)
    if not log["wake_ok"]:
        return log  # Modal down or out of credit: nothing to score, no pass files
    sem = asyncio.Semaphore(CONCURRENCY)
    for k in range(1, passes + 1):
        t = time.monotonic()
        rows = await asyncio.gather(*(one(c, sem) for c in cases))
        with open(f"{out}/pass{k}.jsonl", "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        p = {"pass": k, "ok": sum("error" not in r for r in rows),
             "errors": [(r["id"], r["error"]) for r in rows if "error" in r], "seconds": round(time.monotonic() - t, 1)}
        log["passes"].append(p)
        print(json.dumps(p), flush=True)
    log["gpu_seconds_est"] = round(time.monotonic() - t_wake + SCALEDOWN_S)
    log["usd_est"] = round(log["gpu_seconds_est"] / 3600 * gpu_usd_hour, 2)
    print(json.dumps({k: log[k] for k in ("gpu_seconds_est", "usd_est")}), flush=True)
    return log


def summary(bench: str, paths: list[str]) -> dict:
    """Mean and range across passes, per subtype, for both scopes. A case without a prediction counts as wrong."""
    cases, runs = load(bench), []
    for path in paths:
        rows = [r for r in load(path) if "error" not in r]
        runs.append(report(cases, {r["id"]: {i["type"] for i in r["system"]} for r in rows},
                           {r["id"]: {i["type"] for i in r["glimmer"]} for r in rows}))
    out = {}
    for scope in ("sistema_completo", "glimmer_solo"):
        rows = {}
        for k in runs[0][scope]["by_subtype"]:
            hits = [int(r[scope]["by_subtype"][k].split("/")[0]) for r in runs]
            rows[k] = {"n": int(runs[0][scope]["by_subtype"][k].split("/")[1]), "mean": round(sum(hits) / len(hits), 2),
                       "range": [min(hits), max(hits)]}
        total = [r[scope]["correct"] for r in runs]
        out[scope] = {"n": runs[0][scope]["n"], "mean": round(sum(total) / len(total), 2), "range": [min(total), max(total)],
                      "by_subtype": rows, "missing": [r[scope]["missing"] for r in runs]}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--bench", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--passes", type=int, default=3)
    r.add_argument("--max-usd", type=float, required=True)
    r.add_argument("--gpu-usd-hour", type=float, default=H100_USD_HOUR)
    r.add_argument("--model", help="served model name (a LoRA); default: GLIMMER_MODEL")
    s = sub.add_parser("summary")
    s.add_argument("--bench", required=True)
    s.add_argument("passes", nargs="+")
    args = ap.parse_args(argv)
    if args.cmd == "run":
        asyncio.run(run(args.bench, args.out, args.passes, args.max_usd, args.gpu_usd_hour, args.model))
    else:
        print(json.dumps(summary(args.bench, args.passes), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
