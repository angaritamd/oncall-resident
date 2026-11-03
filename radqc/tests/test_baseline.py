import json

from radqc.baseline import H100_USD_HOUR, SCALEDOWN_S, TIMEOUT, summary


def test_summary_gives_mean_and_range_across_passes(tmp_path):
    bench = tmp_path / "b.jsonl"
    cases = [{"id": "1", "subtype": "omision", "kind": "error", "expected": {"type": "omitted_finding"}},
             {"id": "2", "subtype": "control_negativos", "kind": "control", "expected": None},
             {"id": "3", "subtype": "medida", "kind": "error", "expected": {"type": "measure_mismatch"}}]
    bench.write_text("\n".join(json.dumps(c) for c in cases))
    hit = {"system": [{"type": "omitted_finding"}], "glimmer": [{"type": "omitted_finding"}]}
    miss = {"system": [], "glimmer": []}
    passes = [[{"id": "1", **hit}, {"id": "2", **miss}, {"id": "3", "system": [{"type": "measure_mismatch"}], "glimmer": []}],
              [{"id": "1", **miss}, {"id": "2", **miss}, {"id": "3", "error": "HTTP 404"}]]
    paths = []
    for i, rows in enumerate(passes):
        p = tmp_path / f"pass{i}.jsonl"
        p.write_text("\n".join(json.dumps(r) for r in rows))
        paths.append(str(p))
    s = summary(str(bench), paths)
    assert s["sistema_completo"]["n"] == 3 and s["sistema_completo"]["range"] == [1, 3]
    assert s["sistema_completo"]["by_subtype"]["omision"] == {"n": 1, "mean": 0.5, "range": [0, 1]}
    assert s["glimmer_solo"]["n"] == 2 and s["sistema_completo"]["missing"] == [[], ["3"]]


def test_the_cost_cap_leaves_room_for_the_scale_down():
    # US$ 2.50 on an H100: about 38 min of GPU, so calls stop starting ~32 min after the wake-up
    stop_after = 2.5 / H100_USD_HOUR * 3600 - SCALEDOWN_S - TIMEOUT
    assert 1900 < stop_after < 2000
