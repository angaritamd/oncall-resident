"""Benchmark score, reported apart for the whole system and for Glimmer alone (Miguel, ANG-174).

- Whole system: every case of the benchmark (bench-v2: 65), checked by rules + Lev + Glimmer.
- Glimmer alone: the subtypes Glimmer is trained on (hard_only: omisión, pregunta, doble_chequeo) plus every control
  (bench-v2: 49). Laterality and measurement errors are covered by the rules and Lev, so they are left out.

A case is right when a control gets no issue, and an error or doble_chequeo gets an issue of its expected type.
A case without a prediction counts as wrong and is listed.

Predictions: JSONL, one line per case: {"id": "B6-0001", "issues": [{"type": "omitted_finding"}, ...]}
("rule" is accepted for "type", as in qc.Issue).

Run:
  python -m radqc.score --bench data/bench/bench-v2.jsonl --pred system.jsonl --pred-glimmer glimmer.jsonl [--json]
Both are required: the system's predictions never stand in for Glimmer's, so «Glimmer solo» is always Glimmer's own.
"""
import argparse
import json
from collections import defaultdict

from radqc.taxonomia import BY_ID


def glimmer_case(case: dict) -> bool:
    """Whether a case is in Glimmer's subset: a hard_only subtype or a control."""
    st = BY_ID[case["subtype"]]
    return st.hard or st.kind == "control"


def load(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def predicted(lines: list[dict]) -> dict[str, set[str]]:
    return {p["id"]: {str(i.get("type") or i.get("rule")) for i in p.get("issues") or []} for p in lines}


def right(case: dict, types: set[str]) -> bool:
    if case["kind"] == "control":
        return not types
    return case["expected"]["type"] in types


def score(cases: list[dict], preds: dict[str, set[str]]) -> dict:
    by_sub, missing = defaultdict(lambda: [0, 0]), []
    for c in cases:
        if c["id"] not in preds:
            missing.append(c["id"])
        ok = c["id"] in preds and right(c, preds[c["id"]])
        by_sub[c["subtype"]][0] += ok
        by_sub[c["subtype"]][1] += 1

    def part(kinds):
        ids = [c for c in cases if c["kind"] in kinds]
        return sum(c["id"] in preds and right(c, preds[c["id"]]) for c in ids), len(ids)

    correct = sum(v[0] for v in by_sub.values())
    found, flagged = part({"error", "verify"}), part({"control"})
    return {"n": len(cases), "correct": correct, "accuracy": round(correct / len(cases), 3) if cases else None,
            "detected": f"{found[0]}/{found[1]}", "controls_clean": f"{flagged[0]}/{flagged[1]}",
            "by_subtype": {k: f"{v[0]}/{v[1]}" for k, v in sorted(by_sub.items())}, "missing": missing}


def report(cases: list[dict], system: dict[str, set[str]], glimmer: dict[str, set[str]]) -> dict:
    return {"sistema_completo": score(cases, system),
            "glimmer_solo": score([c for c in cases if glimmer_case(c)], glimmer)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True)
    ap.add_argument("--pred", required=True, help="the whole system's predictions (JSONL)")
    ap.add_argument("--pred-glimmer", required=True, help="Glimmer's predictions alone (JSONL)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    cases, system = load(args.bench), predicted(load(args.pred))
    out = report(cases, system, predicted(load(args.pred_glimmer)))
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return
    for name, s in (("Sistema completo", out["sistema_completo"]), ("Glimmer solo", out["glimmer_solo"])):
        print(f"{name}: {s['correct']}/{s['n']} ({s['accuracy']:.1%}) · detectados {s['detected']} · "
              f"controles sin aviso {s['controls_clean']}")
        print("  " + " · ".join(f"{k} {v}" for k, v in s["by_subtype"].items()))
        if s["missing"]:
            print(f"  sin predicción ({len(s['missing'])}): {', '.join(s['missing'])}")


if __name__ == "__main__":
    main()
