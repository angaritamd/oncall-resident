import pytest

from radqc.score import glimmer_case, main, report


def case(cid, subtype, kind, type_=None):
    return {"id": cid, "subtype": subtype, "kind": kind, "expected": {"type": type_} if type_ else None}


CASES = [case("1", "lateralidad", "error", "laterality"), case("2", "medida", "error", "measure_mismatch"),
         case("3", "omision", "error", "omitted_finding"), case("4", "pregunta", "error", "indication_unanswered"),
         case("5", "doble_chequeo", "verify", "doble_chequeo"), case("6", "control_negativos", "control"),
         case("7", "control_pregunta_cuerpo", "control"), case("8", "control", "control")]


def test_glimmer_subset_is_hard_only_subtypes_plus_every_control():
    assert [c["id"] for c in CASES if glimmer_case(c)] == ["3", "4", "5", "6", "7", "8"]


def test_system_and_glimmer_are_scored_apart():
    system = {"1": {"laterality"}, "2": set(), "3": {"omitted_finding"}, "4": {"laterality"}, "5": {"doble_chequeo"},
              "6": set(), "7": {"indication_unanswered"}}  # 8 missing
    glimmer = {**system, "4": {"indication_unanswered"}, "8": set()}
    out = report(CASES, system, glimmer)
    s, g = out["sistema_completo"], out["glimmer_solo"]
    assert (s["n"], s["correct"], s["detected"], s["controls_clean"], s["missing"]) == (8, 4, "3/5", "1/3", ["8"])
    assert (g["n"], g["correct"], g["detected"], g["controls_clean"], g["missing"]) == (6, 5, "3/3", "2/3", [])
    assert g["by_subtype"]["control_pregunta_cuerpo"] == "0/1"


def test_glimmer_predictions_are_required():
    # the system's predictions never stand in for Glimmer's
    with pytest.raises(SystemExit):
        main(["--bench", "b.jsonl", "--pred", "p.jsonl"])
