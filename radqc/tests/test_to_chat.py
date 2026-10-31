import json

import pytest

from radqc.generate import PolicyError
from radqc.to_chat import build

IND = "Hombre de 60 años con dolor torácico; descartar neumonía."
FIN = "Consolidación en el lóbulo inferior derecho. Nódulo de 8 mm en el lóbulo superior izquierdo."


def rec(cid, subtype, expected=None, **kw):
    r = {"id": cid, "split": "train", "subtype": subtype, "never_train": False, "indication": IND, "findings": FIN,
         "impression": "Consolidación en el lóbulo inferior derecho.", "expected": expected,
         "provenance": {"backend": "spark-open"}}
    return r | kw


def err(type_, body):
    return {"type": type_, "severity": "error", "body_excerpt": body, "impression_excerpt": "", "explanation": "x"}


def test_hard_only_examples_in_the_checker_format():
    records = [rec("T-1", "omision", err("omitted_finding", "Nódulo de 8 mm en el lóbulo superior izquierdo.")),
               rec("T-2", "control_negativos"), rec("T-3", "lateralidad", err("laterality_mismatch", "derecho")),
               rec("T-4", "medida", err("measure_mismatch", "8 mm"))]
    train, val, s = build(records, val=0.0, seed=1)
    assert [e["id"] for e in train] == ["T-1", "T-2"] and val == [] and s["left_out_rules"] == 2
    m = train[0]["messages"]
    assert [x["role"] for x in m] == ["system", "user", "assistant"]
    assert json.loads(m[-1]["content"])["issues"][0]["type"] == "omitted_finding"
    assert json.loads(train[1]["messages"][-1]["content"]) == {"issues": []}
    assert {(e["split"], e["never_train"], e["backend"]) for e in train} == {("train", False, "spark-open")}


def test_an_answer_the_parser_would_drop_is_refused():
    invented = rec("T-5", "omision", err("omitted_finding", "Neumotórax a tensión."))  # not in the findings
    verify = rec("T-6", "doble_chequeo", err("doble_chequeo", "descartar neumonía"))  # quoted from the INDICATION
    off_source = rec("T-7", "doble_chequeo", err("doble_chequeo", "Consolidación en el lóbulo inferior derecho."))
    train, _, s = build([invented, verify, off_source], val=0.0, seed=1)
    assert s["refused_by_parser"] == ["T-5", "T-7"] and [e["id"] for e in train] == ["T-6"]
    assert "doble_chequeo" in s["checker_types"]  # serving/train_v5.py checks it in the manifest


def test_only_trainable_records():
    with pytest.raises(PolicyError):
        build([rec("B-1", "control", split="bench", never_train=True, provenance={"backend": "meta"})], 0.0, 1)


def test_val_split_is_by_case_and_reproducible():
    records = [rec(f"T-{i}", "control_negativos") for i in range(20)]
    a, b = build(records, 0.1, 7), build(records, 0.1, 7)
    assert [e["id"] for e in a[1]] == [e["id"] for e in b[1]] and len(a[1]) == 2 and len(a[0]) == 18


def test_main_writes_a_manifest_with_the_sha256_of_both_files(tmp_path):
    import hashlib

    from radqc.to_chat import main
    src = tmp_path / "in.jsonl"
    src.write_text("\n".join(json.dumps(rec(f"T-{i}", "control_negativos")) for i in range(10)))
    main(["--inp", str(src), "--out", str(tmp_path / "train_chat"), "--val", "0.2"])
    s = json.loads((tmp_path / "train_chat.summary.json").read_text())
    for n in ("train", "val"):
        f = tmp_path / f"train_chat.{n}.jsonl"
        assert s["sha256"][f.name] == hashlib.sha256(f.read_bytes()).hexdigest()
