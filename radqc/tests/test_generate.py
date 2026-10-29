import pytest

from radqc.generate import PolicyError, Spec, assert_trainable, check_policy, plan, validate
from radqc.taxonomy import BY_ID, SUBTYPES


def spec(sub: str) -> Spec:
    return Spec("T-1", BY_ID[sub], "TC", "TC de tórax", "F", 60)


def test_api_outputs_only_go_to_the_benchmark():
    check_policy("meta", "bench")
    check_policy("glimmer", "train")
    with pytest.raises(PolicyError):
        check_policy("meta", "train")


def test_training_refuses_api_outputs():
    ok = {"id": "a", "split": "train", "never_train": False, "provenance": {"backend": "glimmer"}}
    assert_trainable([ok])
    for bad in ({**ok, "never_train": True}, {**ok, "provenance": {"backend": "meta"}}, {**ok, "split": "bench"}):
        with pytest.raises(PolicyError):
            assert_trainable([ok, bad])


def test_plan_is_stratified_and_reproducible():
    p = plan(20, hard_only=True, seed=1, prefix="B")
    hard = [s for s in SUBTYPES if s.hard]
    assert {s.subtype.id for s in p} == {s.id for s in hard}
    assert [s.subtype.id for s in p].count(hard[0].id) == 4
    assert [(s.exam, s.age) for s in p] == [(s.exam, s.age) for s in plan(20, hard_only=True, seed=1, prefix="B")]


FIN = "Nódulo sólido en el lóbulo superior derecho de 12 mm. No hay derrame pleural."


def test_quotes_must_be_literal():
    d = {"indication": "Control de nódulo.", "findings": FIN, "impression": "Nódulo de 1,2 mm en el lóbulo superior derecho.",
         "error": {"body_excerpt": "nódulo de 12 mm", "impression_excerpt": "Nódulo de 1,2 mm"}}
    assert validate(spec("measure_unit"), d) == "body_excerpt not literal"
    d["error"]["body_excerpt"] = "lóbulo superior derecho de 12 mm"
    assert validate(spec("measure_unit"), d) is None


def test_provable_types_must_be_caught_by_the_rules():
    d = {"indication": "Control.", "findings": FIN, "impression": "Nódulo de 12 mm en el lóbulo superior derecho.",
         "error": {"body_excerpt": "12 mm", "impression_excerpt": "12 mm"}}
    assert validate(spec("measure_number"), d) == "measure_mismatch not provable by the rules"


def test_clean_cases_must_not_trip_the_rules():
    ok = {"indication": "Control.", "findings": FIN, "impression": "Nódulo de 1,2 cm en el lóbulo superior derecho.", "error": None}
    assert validate(spec("clean_tricky"), ok) is None
    bad = {**ok, "impression": "Nódulo de 1,2 cm en el lóbulo superior izquierdo."}
    assert validate(spec("clean_tricky"), bad).startswith("clean case trips the rules")


def test_non_rule_types_must_not_carry_an_extra_provable_error():
    d = {"indication": "Control.", "findings": FIN + " Adenopatía hiliar derecha de 15 mm.",
         "impression": "Nódulo de 10 mm en el lóbulo superior derecho.",
         "error": {"body_excerpt": "Adenopatía hiliar derecha de 15 mm.", "impression_excerpt": ""}}
    assert validate(spec("omission_partial"), d).startswith("extra provable error")
