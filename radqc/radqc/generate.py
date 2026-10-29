"""Synthetic RAD·QC cases: one Spanish draft report per spec, with at most one planted mechanical error.

Data rules (ANG-174, Meta Model API Terms §10.1(ix) and §1):
- Outputs of the Meta Model API (Muse Wonder / Spark) are used ONLY for evaluation: they go to the `bench` split and
  every record carries `never_train: true`.
- Training data comes only from open-weight models we serve ourselves, outside the API Terms (§1): Spark Open on
  Baseten (ANG-178, radqc/radqc/spark_v5.py) generates the v5 training set; Glimmer no longer generates cases.
`check_policy` enforces both before any call is made, and `assert_trainable` refuses API outputs at training time.

Run (the key comes from the environment, never printed):
  python -m radqc.generate --backend meta --model muse-wonder-1.0 --split bench --n 20 --hard-only --out data/bench/pilot.jsonl
Every record keeps its plan seed, per-case seed, prompt version and taxonomy version (provenance).
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

from .taxonomia import (BY_ID, CRITICAL_ES, CONTROL_SHARE, CONTROLS, ERRORS, PROMPT_VERSION, STUDIES, STYLE, Subtype,
                        VERSION as TAXONOMY_VERSION, asked, is_critical, validate)

ALLOWED_SPLITS = {"meta": {"bench"}, "glimmer": {"train", "bench"}}
TRAINABLE_BACKENDS = {"glimmer", "spark-open"}  # self-served open weights; never "meta" (the Model API)
# USD per 1M tokens (input, cached input, output), from dev.meta.ai/docs/pricing-rate-limits (Standard mode)
PRICES = {"muse-wonder-1.0": (4.00, 0.20, 20.00), "muse-spark-1.3": (1.25, 0.15, 4.25)}


class PolicyError(Exception):
    pass


def check_policy(backend: str, split: str, model: str | None = None, max_usd: float | None = None) -> None:
    if split not in ALLOWED_SPLITS.get(backend, set()):
        raise PolicyError(f"backend {backend!r} may not write the {split!r} split "
                          "(Meta Model API outputs are for evaluation only; training data comes from self-hosted Glimmer)")
    # a spend cap on a per-token model without a known price would count every call as free
    if backend == "meta" and max_usd is not None and model not in PRICES:
        raise PolicyError(f"no price for {model!r}: add it to PRICES before capping spend")


def assert_trainable(records: list[dict]) -> None:
    """Called by the training script on every input file: no API output may ever be trained on."""
    bad = [r.get("id") for r in records if r.get("never_train") or r.get("split") != "train"
           or r.get("provenance", {}).get("backend") not in TRAINABLE_BACKENDS]
    if bad:
        raise PolicyError(f"{len(bad)} records are not trainable (API output or not in the train split): {bad[:5]}")


@dataclass
class Spec:
    id: str
    subtype: Subtype
    modality: str
    exam: str
    reason: str          # reason for consultation, from the study's valid ones
    sex: str
    age: int
    seed: int            # per-case seed, also sent to the model


# fixed subtype counts for a named set (approved by Miguel); without one, plan() stratifies round-robin
MIXES = {
    "bench-v2": {"lateralidad": 8, "medida": 8, "omision": 9, "pregunta": 9, "doble_chequeo": 8,
                 "control_negativos": 3, "control_subrasgos": 3, "control_menores": 3, "control_dimension": 3,
                 "control_parafrasis": 3, "control_limitacion": 3},
}


# fixed cases for a named set: (subtype, study, reason), each reason one of STUDIES (approved by Miguel). bench-v2-pc
# adds 6 critical-question pregunta cases to bench-v2 after taxonomy-v4 (B6-0061..0066)
FIXED = {
    "bench-v2-pc": [
        ("pregunta", "RX de tórax", "Dolor torácico súbito tras procedimiento; descartar neumotórax a tensión."),
        ("pregunta", "RX de abdomen", "Dolor abdominal súbito y defensa; descartar neumoperitoneo."),
        ("pregunta", "RX de abdomen", "Distensión y vómito; descartar obstrucción intestinal."),
        ("pregunta", "TC de abdomen y pelvis con contraste", "Dolor en fosa ilíaca derecha; descartar apendicitis."),
        ("pregunta", "TC de abdomen y pelvis con contraste", "Dolor en hipocondrio derecho; descartar colecistitis."),
        ("pregunta", "Angio-TC de tórax", "Dolor torácico desgarrante; descartar disección aórtica."),
    ],
}


def plan_fixed(name: str, *, seed: int, prefix: str, start: int = 1) -> list[Spec]:
    """The FIXED[name] cases, numbered from `start`; sexes, ages and per-case seeds come from `seed`."""
    rng = random.Random(seed)
    by_exam = {s.exam: s for s in STUDIES}
    out = []
    for i, (sid, exam, reason) in enumerate(FIXED[name]):
        study = by_exam[exam]
        if reason not in study.reasons + study.critical:
            raise ValueError(f"{reason!r} is not a reason for {exam}")
        out.append(Spec(f"{prefix}-{start + i:04d}", BY_ID[sid], study.modality, exam, reason, rng.choice("FM"),
                        rng.randint(18, 90), rng.randrange(2**31)))
    return out


def _reasons(sid: str, study) -> tuple[str, ...]:
    """doble_chequeo needs a critical reason; the body-answered control a non-critical question; everything else uses a
    routine reason valid for that study."""
    if sid == "doble_chequeo":
        return study.critical
    if sid == "control_pregunta_cuerpo":
        return tuple(r for r in study.reasons if asked(r) and not is_critical(r))
    return study.reasons


def plan(n: int, *, hard_only: bool, seed: int, prefix: str, mix: dict[str, int] | None = None) -> list[Spec]:
    """Subtypes: `mix` counts, or ~30 % controls and the rest errors and doble_chequeo, round-robin over each group.
    Studies are spread evenly: doble_chequeo goes round-robin over the studies with a critical reason, every other
    case to the study with the fewest cases so far. Ages, sexes, reasons and per-case seeds come from `seed`, so a
    plan is reproducible."""
    rng = random.Random(seed)
    if mix:
        if sum(mix.values()) != n:
            raise ValueError(f"the mix has {sum(mix.values())} cases, not {n}")
        subs = [BY_ID[sid] for sid, k in mix.items() for _ in range(k)]
    else:
        errors = [s for s in ERRORS if s.hard or not hard_only]
        controls = [s for s in CONTROLS if s.hard or not hard_only]
        k = round(n * CONTROL_SHARE)
        subs = [controls[i % len(controls)] for i in range(k)] + [errors[i % len(errors)] for i in range(n - k)]
    rng.shuffle(subs)
    order = rng.sample(STUDIES, len(STUDIES))  # tie-break order
    load = {s.exam: 0 for s in STUDIES}
    studies = [None] * len(subs)
    # subtypes that need a particular kind of reason go round-robin over the studies that have one
    for sid in ("doble_chequeo", "control_pregunta_cuerpo"):
        fit = [s for s in order if _reasons(sid, s)]
        for j, i in enumerate(i for i, sub in enumerate(subs) if sub.id == sid):
            studies[i] = fit[j % len(fit)]
            load[studies[i].exam] += 1
    for i, sub in enumerate(subs):
        if studies[i] is None:
            studies[i] = min(order, key=lambda s: load[s.exam])
            load[studies[i].exam] += 1
    out = []
    for i, (sub, study) in enumerate(zip(subs, studies)):
        reason = rng.choice(_reasons(sub.id, study))
        out.append(Spec(f"{prefix}-{i + 1:04d}", sub, study.modality, study.exam, reason, rng.choice("FM"),
                        rng.randint(18, 90), rng.randrange(2**31)))
    return out


PROMPT = """Escribe UN informe radiológico SINTÉTICO y ficticio para:
- Estudio: {exam} ({modality}); paciente {sex}, {age} años.
- Motivo de consulta: {reason} (la INDICACIÓN parte de este motivo; no lo cambies por otro).
- Caso a construir: {recipe}

Reglas:
- {style}
- Conciso: INDICACIÓN de 1 frase; HALLAZGOS de 3 a 6 frases; IMPRESIÓN de 1 a 3 frases.
- Medidas con número y unidad (mm o cm) cuando haya lesiones medibles.
- Si el caso lleva un error, debe ser el ÚNICO error del informe y verse natural, como un descuido real al dictar.
- Pregunta CRÍTICA = patología aguda que cambia la conducta inmediata: {critical}.
- NO son errores (no los cuentes como tales): negativos pertinentes que la IMPRESIÓN no repite (salvo que respondan una pregunta crítica), rasgos resumidos en un diagnóstico, hallazgos menores sin impacto, una sola dimensión en vez de tres, paráfrasis, una IMPRESIÓN que nombra la pregunta aunque sea con limitación («apéndice no visualizado; no se puede descartar apendicitis»), una pregunta NO crítica respondida solo en HALLAZGOS.
- SÍ es error de pregunta: una pregunta CRÍTICA que la IMPRESIÓN no responde explícitamente, aunque HALLAZGOS la responda, la IMPRESIÓN sea genérica («estudio dentro de límites normales») o solo nombre la región o la anatomía («parénquima pulmonar sin consolidaciones» ante «descartar tromboembolismo pulmonar»); o una pregunta NO crítica que ni HALLAZGOS ni IMPRESIÓN responden. Responder es nombrar la patología preguntada.
- body_excerpt: copia EXACTA (carácter por carácter) del fragmento de HALLAZGOS que prueba el error, o de la INDICACIÓN si el caso es de pregunta o de doble chequeo.
- impression_excerpt: copia EXACTA del fragmento de la IMPRESIÓN implicado ("" si lo que pasa es que algo falta).
- Si el caso es un control sin error, "error" es null.

Responde SOLO con JSON:
{{"indication": "...", "findings": "...", "impression": "...", "error": {{"body_excerpt": "...", "impression_excerpt": "...", "explanation": "una frase"}} }}"""


def messages(spec: Spec) -> list[dict]:
    sex = "mujer" if spec.sex == "F" else "hombre"
    return [{"role": "user", "content": PROMPT.format(exam=spec.exam, modality=spec.modality, sex=sex, age=spec.age,
                                                      reason=spec.reason, recipe=spec.subtype.recipe,
                                                      style=STYLE, critical=CRITICAL_ES)}]


def cost(model: str, usage: dict | None) -> tuple[int, int, float | None]:
    usage = usage or {}
    tin, tout = int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)
    p = PRICES.get(model)
    if not p:
        return tin, tout, None  # self-hosted: billed by GPU time, not per token
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
    return tin, tout, round(((tin - cached) * p[0] + cached * p[1] + tout * p[2]) / 1e6, 6)


MAX_TOKENS = 4000
PROMPT_TOKENS_MAX = 600  # the generation prompt is ~330-400 tokens


def worst_call_usd(model: str) -> float:
    """The most one call can cost: a full prompt and max_tokens of output at list price."""
    p = PRICES[model]
    return (PROMPT_TOKENS_MAX * p[0] + MAX_TOKENS * p[2]) / 1e6


class Budget:
    """Stops new calls before the cap: a call is not started once spent + `reserve` (the worst case of the calls
    still in flight) would pass it."""

    def __init__(self, cap_usd: float | None, reserve_usd: float = 0.0):
        self.cap, self.reserve, self.spent, self.hit = cap_usd, reserve_usd, 0.0, False

    def allows(self) -> bool:
        if self.cap is not None and self.spent + self.reserve >= self.cap:
            self.hit = True
        return not self.hit


async def one(http: httpx.AsyncClient, base: str, key: str, model: str, spec: Spec, backend: str, split: str,
              plan_seed: int, budget: Budget, tries: int = 2) -> tuple[dict | None, list[dict]]:
    """(record or None, one attempt row per call, with tokens, cost and rejection reason)."""
    attempts = []
    for _ in range(tries):
        if not budget.allows():
            return None, attempts
        t0 = time.monotonic()
        r = await http.post(f"{base}/chat/completions", headers={"authorization": f"Bearer {key}"},
                            json={"model": model, "messages": messages(spec), "temperature": 0.8, "max_tokens": MAX_TOKENS,
                                  "seed": spec.seed},
                            timeout=180)
        secs = round(time.monotonic() - t0, 1)
        if r.status_code != 200:
            attempts.append({"id": spec.id, "ok": False, "why": f"HTTP {r.status_code}", "seconds": secs})
            continue
        body = r.json()
        tin, tout, usd = cost(model, body.get("usage"))
        budget.spent += usd or 0
        content = body["choices"][0]["message"].get("content") or ""
        m = re.search(r"\{.*\}", content, re.S)
        try:
            data = json.loads(m.group(0)) if m else None
        except ValueError:
            data = None
        why = validate(spec.subtype, data) if data is not None else "no JSON"
        attempts.append({"id": spec.id, "ok": why is None, "why": why, "seconds": secs,
                         "tokens_in": tin, "tokens_out": tout, "cost_usd": usd})
        if why is None:
            err = data.get("error")
            return {
                "id": spec.id, "split": split, "subtype": spec.subtype.id, "kind": spec.subtype.kind,
                "type": spec.subtype.label, "hard": spec.subtype.hard, "modality": spec.modality, "exam": spec.exam,
                "reason": spec.reason, "sex": spec.sex, "age": spec.age,
                "indication": data["indication"].strip(), "findings": data["findings"].strip(),
                "impression": data["impression"].strip(),
                "expected": None if spec.subtype.kind == "control" else {
                    "type": spec.subtype.label, "severity": "verify" if spec.subtype.kind == "verify" else "error",
                    **{k: str(err.get(k) or "").strip() for k in ("body_excerpt", "impression_excerpt", "explanation")}},
                "never_train": backend != "glimmer",
                "synthetic": True,
                "provenance": {"backend": backend, "model": model, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "plan_seed": plan_seed, "case_seed": spec.seed, "prompt_version": PROMPT_VERSION,
                               "taxonomy_version": TAXONOMY_VERSION},
            }, attempts
    return None, attempts


async def run(args) -> dict:
    check_policy(args.backend, args.split, args.model, args.max_usd)
    if args.backend == "meta":
        base, key = os.environ.get("MODEL_API_BASE_URL", "https://api.meta.ai/v1").rstrip("/"), os.environ["MODEL_API_KEY"]
    else:
        base, key = os.environ["GLIMMER_BASE_URL"].rstrip("/"), os.environ["GLIMMER_API_KEY"]
    if args.fixed:
        specs = plan_fixed(args.fixed, seed=args.seed, prefix=args.prefix, start=args.start)
    else:
        specs = plan(args.n, hard_only=args.hard_only, seed=args.seed, prefix=args.prefix, mix=MIXES.get(args.mix))
    if args.only:  # regenerate some IDs of the same plan (same study, sex and age)
        specs = [s for s in specs if s.id in set(args.only.split(","))]
    sem = asyncio.Semaphore(args.concurrency)
    # reserve: the worst case of every call that may be in flight (Wonder: ~US$ 0.082 each)
    budget = Budget(args.max_usd, reserve_usd=worst_call_usd(args.model) * args.concurrency if args.max_usd else 0.0)
    t0 = time.monotonic()
    async with httpx.AsyncClient() as http:
        async def guarded(s):
            async with sem:
                return await one(http, base, key, args.model, s, args.backend, args.split, args.seed, budget)
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
        "max_usd": args.max_usd, "stopped_by_budget": budget.hit,
        "prompt_version": PROMPT_VERSION, "taxonomy_version": TAXONOMY_VERSION,
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
    ap.add_argument("--mix", choices=sorted(MIXES), help="fixed subtype counts (e.g. bench-v2: 60 cases)")
    ap.add_argument("--fixed", choices=sorted(FIXED), help="a fixed list of cases instead of a plan (e.g. bench-v2-pc)")
    ap.add_argument("--start", type=int, default=1, help="first case number for --fixed")
    ap.add_argument("--max-usd", type=float, help="stop starting calls before this spend (per-token models)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    try:
        s = asyncio.run(run(args))
    except PolicyError as e:
        sys.exit(f"policy: {e}")
    print(json.dumps({k: v for k, v in s.items() if k != "seconds_per_call"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
