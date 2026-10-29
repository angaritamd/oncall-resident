"""Synthetic RAD·QC cases: one Spanish draft report per spec, with at most one planted mechanical error.

Data rules (ANG-174, Meta Model API Terms §10.1(ix) and §1):
- Outputs of the Meta Model API (Muse Wonder / Spark) are used ONLY for evaluation: they go to the `bench` split and
  every record carries `never_train: true`.
- The training split is generated only with Glimmer self-hosted on our Modal (Apache-2.0, outside the API Terms).
`check_policy` enforces both before any call is made, and `assert_trainable` refuses API outputs at training time.

Run (the key comes from the environment, never printed):
  python -m radqc.generate --backend meta --model muse-wonder-1.0 --split bench --n 20 --hard-only --out data/bench/pilot.jsonl
"""
import argparse
import asyncio
import json
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from oncall_core.qc import rule_issues

from .taxonomy import BY_ID, STUDIES, SUBTYPES, Subtype

ALLOWED_SPLITS = {"meta": {"bench"}, "glimmer": {"train", "bench"}}
# USD per 1M tokens (input, cached input, output), from dev.meta.ai/docs/pricing-rate-limits (Standard mode)
PRICES = {"muse-wonder-1.0": (4.00, 0.20, 20.00), "muse-spark-1.3": (1.25, 0.15, 4.25)}


class PolicyError(Exception):
    pass


def check_policy(backend: str, split: str) -> None:
    if split not in ALLOWED_SPLITS.get(backend, set()):
        raise PolicyError(f"backend {backend!r} may not write the {split!r} split "
                          "(Meta Model API outputs are for evaluation only; training data comes from self-hosted Glimmer)")


def assert_trainable(records: list[dict]) -> None:
    """Called by the training script on every input file: no API output may ever be trained on."""
    bad = [r.get("id") for r in records if r.get("never_train") or r.get("provenance", {}).get("backend") != "glimmer"
           or r.get("split") != "train"]
    if bad:
        raise PolicyError(f"{len(bad)} records are not trainable (API output or not in the train split): {bad[:5]}")


@dataclass
class Spec:
    id: str
    subtype: Subtype
    modality: str
    exam: str
    sex: str
    age: int


def plan(n: int, *, hard_only: bool, seed: int, prefix: str) -> list[Spec]:
    """Round-robin over subtypes (stratified), studies drawn with a fixed seed so a plan is reproducible."""
    rng = random.Random(seed)
    subs = [s for s in SUBTYPES if s.hard] if hard_only else list(SUBTYPES)
    out = []
    for i in range(n):
        modality, exam = rng.choice(STUDIES)
        out.append(Spec(f"{prefix}-{i + 1:04d}", subs[i % len(subs)], modality, exam, rng.choice("FM"), rng.randint(18, 90)))
    return out


PROMPT = """Escribe UN informe radiológico SINTÉTICO en español, ficticio (sin nombres, fechas ni identificadores), para:
- Estudio: {exam} ({modality}); paciente {sex}, {age} años.
- Caso a construir: {recipe}

Reglas:
- Estilo de informe real latinoamericano, conciso: INDICACIÓN de 1 frase; HALLAZGOS de 3 a 6 frases; IMPRESIÓN de 1 a 3 frases.
- Medidas con número y unidad (mm o cm) cuando haya lesiones medibles.
- El error (si lo hay) debe ser el ÚNICO error del informe y verse natural, como un descuido real al dictar.
- body_excerpt: copia EXACTA (carácter por carácter) del fragmento de HALLAZGOS (o de la INDICACIÓN si el error es de indicación) que prueba el error.
- impression_excerpt: copia EXACTA del fragmento de la IMPRESIÓN implicado ("" si el error es que algo falta).
- Si el caso es "sin error", "error" es null.

Responde SOLO con JSON:
{{"indication": "...", "findings": "...", "impression": "...", "error": {{"body_excerpt": "...", "impression_excerpt": "...", "explanation": "una frase"}} }}"""


def messages(spec: Spec) -> list[dict]:
    sex = "mujer" if spec.sex == "F" else "hombre"
    return [{"role": "user", "content": PROMPT.format(exam=spec.exam, modality=spec.modality, sex=sex, age=spec.age,
                                                      recipe=spec.subtype.recipe)}]


def validate(spec: Spec, data: dict) -> str | None:
    """Why a generated case is rejected, or None. Quotes must be literal; rule-provable types must be provable."""
    if not isinstance(data, dict):
        return "no JSON object"
    ind, fin, imp = (str(data.get(k) or "").strip() for k in ("indication", "findings", "impression"))
    if not (ind and fin and imp):
        return "missing section"
    err = data.get("error")
    st = spec.subtype
    rules = {i.rule for i in rule_issues(fin, imp)}
    if st.type is None:
        if err:
            return "clean case with an error"
        if rules:
            return f"clean case trips the rules: {sorted(rules)}"
        return None
    if not isinstance(err, dict):
        return "error missing"
    body, imp_x = str(err.get("body_excerpt") or "").strip(), str(err.get("impression_excerpt") or "").strip()
    src = ind if st.type == "indication_unanswered" else fin
    if not body or body not in src:
        return "body_excerpt not literal"
    if imp_x and imp_x not in imp:
        return "impression_excerpt not literal"
    if st.type in ("measure_mismatch", "laterality_mismatch") and st.type not in rules:
        return f"{st.type} not provable by the rules"
    if st.type not in ("measure_mismatch", "laterality_mismatch") and rules:
        return f"extra provable error: {sorted(rules)}"
    return None


def cost(model: str, usage: dict | None) -> tuple[int, int, float | None]:
    usage = usage or {}
    tin, tout = int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)
    p = PRICES.get(model)
    if not p:
        return tin, tout, None  # self-hosted: billed by GPU time, not per token
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
    return tin, tout, round(((tin - cached) * p[0] + cached * p[1] + tout * p[2]) / 1e6, 6)


async def one(http: httpx.AsyncClient, base: str, key: str, model: str, spec: Spec, backend: str, split: str,
              tries: int = 2) -> tuple[dict | None, list[dict]]:
    """(record or None, one attempt row per call, with tokens, cost and rejection reason)."""
    attempts = []
    for _ in range(tries):
        t0 = time.monotonic()
        r = await http.post(f"{base}/chat/completions", headers={"authorization": f"Bearer {key}"},
                            json={"model": model, "messages": messages(spec), "temperature": 0.8, "max_tokens": 4000},
                            timeout=180)
        secs = round(time.monotonic() - t0, 1)
        if r.status_code != 200:
            attempts.append({"id": spec.id, "ok": False, "why": f"HTTP {r.status_code}", "seconds": secs})
            continue
        body = r.json()
        tin, tout, usd = cost(model, body.get("usage"))
        content = body["choices"][0]["message"].get("content") or ""
        m = re.search(r"\{.*\}", content, re.S)
        try:
            data = json.loads(m.group(0)) if m else None
        except ValueError:
            data = None
        why = validate(spec, data) if data is not None else "no JSON"
        attempts.append({"id": spec.id, "ok": why is None, "why": why, "seconds": secs,
                         "tokens_in": tin, "tokens_out": tout, "cost_usd": usd})
        if why is None:
            err = data.get("error")
            return {
                "id": spec.id, "split": split, "subtype": spec.subtype.id, "type": spec.subtype.type,
                "hard": spec.subtype.hard, "modality": spec.modality, "exam": spec.exam, "sex": spec.sex, "age": spec.age,
                "indication": data["indication"].strip(), "findings": data["findings"].strip(),
                "impression": data["impression"].strip(),
                "expected": None if not err else {"type": spec.subtype.type, **{k: str(err.get(k) or "").strip() for k in
                                                                                ("body_excerpt", "impression_excerpt", "explanation")}},
                "never_train": backend != "glimmer",
                "synthetic": True,
                "provenance": {"backend": backend, "model": model, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
            }, attempts
    return None, attempts


async def run(args) -> dict:
    check_policy(args.backend, args.split)
    if args.backend == "meta":
        base, key = os.environ.get("MODEL_API_BASE_URL", "https://api.meta.ai/v1").rstrip("/"), os.environ["MODEL_API_KEY"]
    else:
        base, key = os.environ["GLIMMER_BASE_URL"].rstrip("/"), os.environ["GLIMMER_API_KEY"]
    specs = plan(args.n, hard_only=args.hard_only, seed=args.seed, prefix=args.prefix)
    if args.only:  # regenerate some IDs of the same plan (same study, sex and age)
        specs = [s for s in specs if s.id in set(args.only.split(","))]
    sem = asyncio.Semaphore(args.concurrency)
    t0 = time.monotonic()
    async with httpx.AsyncClient() as http:
        async def guarded(s):
            async with sem:
                return await one(http, base, key, args.model, s, args.backend, args.split)
        results = await asyncio.gather(*(guarded(s) for s in specs))
    records = [r for r, _ in results if r]
    attempts = [a for _, att in results for a in att]
    with open(args.out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = {
        "backend": args.backend, "model": args.model, "split": args.split, "requested": len(specs), "accepted": len(records),
        "calls": len(attempts), "rejected": [a for a in attempts if not a["ok"]],
        "tokens_in": sum(a.get("tokens_in", 0) for a in attempts), "tokens_out": sum(a.get("tokens_out", 0) for a in attempts),
        "cost_usd": round(sum(a.get("cost_usd") or 0 for a in attempts), 4), "wall_seconds": round(time.monotonic() - t0, 1),
        "seconds_per_call": sorted(a["seconds"] for a in attempts),
    }
    with open(args.out.replace(".jsonl", ".summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=sorted(ALLOWED_SPLITS), required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--split", choices=["bench", "train"], required=True)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--hard-only", action="store_true")
    ap.add_argument("--seed", type=int, default=174)
    ap.add_argument("--prefix", default="B5")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--only", help="comma-separated IDs of the plan to (re)generate")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    try:
        s = asyncio.run(run(args))
    except PolicyError as e:
        sys.exit(f"policy: {e}")
    print(json.dumps({k: v for k, v in s.items() if k != "seconds_per_call"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
