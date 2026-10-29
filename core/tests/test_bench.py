"""RAD·QC benchmark validation on /bench: cases from the JSONL file, one verdict per case."""
import json

from fastapi.testclient import TestClient

from oncall_core.main import create_app
from oncall_core.store import Store

from test_core import CASES, UIDS, FakeSource

RAD = {"x-resident-login": "rad@example.com"}
CASE = {"id": "B5-0001", "subtype": "omission_partial", "type": "omitted_finding", "hard": True, "modality": "TC",
        "exam": "TC de tórax", "sex": "F", "age": 60, "indication": "Control.", "findings": "Dos nódulos.",
        "impression": "Un nódulo.", "expected": {"type": "omitted_finding", "body_excerpt": "Dos nódulos.",
                                                 "impression_excerpt": "", "explanation": "Falta uno."},
        "never_train": True, "provenance": {"backend": "meta", "model": "muse-wonder-1.0"}}


def client(tmp_path):
    f = tmp_path / "bench.jsonl"
    f.write_text(json.dumps(CASE, ensure_ascii=False) + "\n", encoding="utf-8")
    return TestClient(create_app(FakeSource(list(UIDS.values())), str(CASES), store=Store(":memory:"), providers=[],
                                 env={"BENCH_FILE": str(f)}))


def test_lists_cases_without_provenance(tmp_path):
    v = client(tmp_path).get("/api/bench").json()
    assert (v["total"], v["validated"], v["valid"]) == (1, 0, 0)
    c = v["cases"][0]
    assert c["id"] == "B5-0001" and c["model"] == "muse-wonder-1.0" and c["verdict"] is None
    assert "never_train" not in c and "provenance" not in c


def test_verdict_needs_identity_and_last_one_wins(tmp_path):
    c = client(tmp_path)
    assert c.post("/api/bench/B5-0001", json={"verdict": "valid"}).status_code == 403
    assert c.post("/api/bench/B5-9999", json={"verdict": "valid"}, headers=RAD).status_code == 404
    assert c.post("/api/bench/B5-0001", json={"verdict": "maybe"}, headers=RAD).status_code == 422
    c.post("/api/bench/B5-0001", json={"verdict": "valid"}, headers=RAD)
    r = c.post("/api/bench/B5-0001", json={"verdict": "invalid", "note": " falta lateralidad "}, headers=RAD).json()
    assert (r["verdict"], r["note"], r["by"]) == ("invalid", "falta lateralidad", "rad@example.com")
    v = c.get("/api/bench").json()
    assert (v["validated"], v["valid"]) == (1, 0) and v["cases"][0]["verdict"]["verdict"] == "invalid"


def test_missing_file_is_an_empty_bench(tmp_path):
    c = TestClient(create_app(FakeSource([]), str(CASES), store=Store(":memory:"), providers=[],
                              env={"BENCH_FILE": str(tmp_path / "none.jsonl")}))
    assert c.get("/api/bench").json() == {"cases": [], "total": 0, "validated": 0, "valid": 0}
