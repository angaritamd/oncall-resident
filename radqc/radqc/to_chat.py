"""Training set for the v5 LoRA (ANG-174/178): Spark Open train records -> chat examples in the checker's own format.

Each example is exactly what qc.py sends Glimmer (QC_PROMPT["es"] + qc_messages) and the answer it should give: the
JSON qc.parse_model_issues reads ({"issues": [...]}; a control gets {"issues": []}). The answer must survive the
parser, so an example whose quotes are not literal in the report is refused.

Rules (Miguel):
- Only trainable records: `assert_trainable` (split=train, never_train=false, an open-weight backend we serve).
- hard_only: laterality and measurement are covered by the rules and Lev, so those subtypes are left out; controls stay.

  PYTHONPATH=.:../core python -m radqc.to_chat --inp gen/v5_train.jsonl --out gen/train_chat.jsonl --val 0.1
writes gen/train_chat.train.jsonl and gen/train_chat.val.jsonl (split by case, reproducible with --seed) plus a summary.
"""
import argparse
import hashlib
import json
import random
from collections import Counter

from oncall_core import qc
from radqc.generate import assert_trainable

LEFT_OUT = {"lateralidad", "medida"}  # covered by the rules + Lev (hard_only training)


def answer(record: dict) -> str:
    """The assistant turn: the issues JSON the checker parses."""
    e = record.get("expected")
    issues = [] if not e else [{k: e.get(k, "") for k in ("type", "body_excerpt", "impression_excerpt", "explanation")}]
    return json.dumps({"issues": issues}, ensure_ascii=False)


def example(record: dict) -> dict:
    ind, fin, imp = record["indication"], record["findings"], record["impression"]
    msgs = qc.qc_messages("es", ind, fin, imp) + [{"role": "assistant", "content": answer(record)}]
    # the policy fields travel with the example: serving/train_v5.py checks them again before training
    return {"id": record["id"], "subtype": record["subtype"], "split": record["split"],
            "never_train": record["never_train"], "backend": record["provenance"]["backend"], "messages": msgs}


def survives_parser(record: dict) -> bool:
    """A control parses to no issue; an error parses back to its own type (literal quotes, a known type)."""
    got = qc.parse_model_issues(answer(record), record["indication"], record["findings"], record["impression"])
    if not record.get("expected"):
        return got == []
    return [i.rule for i in got] == [record["expected"]["type"]]


def build(records: list[dict], val: float, seed: int) -> tuple[list[dict], list[dict], dict]:
    assert_trainable(records)
    kept = [r for r in records if r["subtype"] not in LEFT_OUT]
    refused = [r["id"] for r in kept if not survives_parser(r)]
    kept = [r for r in kept if r["id"] not in refused]
    rng = random.Random(seed)
    ids = sorted(r["id"] for r in kept)
    rng.shuffle(ids)
    val_ids = set(ids[:round(len(ids) * val)])
    train = [example(r) for r in kept if r["id"] not in val_ids]
    valid = [example(r) for r in kept if r["id"] in val_ids]
    summary = {"records": len(records), "left_out_rules": sum(r["subtype"] in LEFT_OUT for r in records),
               "refused_by_parser": refused, "train": len(train), "val": len(valid),
               "by_subtype": dict(Counter(r["subtype"] for r in kept)), "seed": seed}
    return train, valid, summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--inp", required=True, nargs="+", help="Spark Open train JSONL file(s)")
    ap.add_argument("--out", required=True, help="base name: writes <out>.train.jsonl, <out>.val.jsonl, <out>.summary.json")
    ap.add_argument("--val", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=174)
    args = ap.parse_args(argv)
    records = [json.loads(line) for path in args.inp for line in open(path, encoding="utf-8") if line.strip()]
    train, valid, summary = build(records, args.val, args.seed)
    base = args.out.removesuffix(".jsonl")
    for name, rows in (("train", train), ("val", valid)):
        with open(f"{base}.{name}.jsonl", "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # manifest: serving/train_v5.py refuses files whose sha256 does not match what this run wrote
    summary["sha256"] = {f"train_chat.{n}.jsonl": hashlib.sha256(open(f"{base}.{n}.jsonl", "rb").read()).hexdigest()
                         for n in ("train", "val")}
    with open(f"{base}.summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
