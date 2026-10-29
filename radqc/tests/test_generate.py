import pytest

from radqc.generate import PolicyError, assert_trainable, check_policy, plan
from radqc.taxonomia import STUDIES, unit_each, validate
from radqc.taxonomia import BY_ID, CONTROLS, ERRORS, Subtype


def spec(sub: str) -> Subtype:
    return BY_ID[sub]


def test_api_outputs_only_go_to_the_benchmark():
    check_policy("meta", "bench")
    check_policy("glimmer", "train")
    with pytest.raises(PolicyError):
        check_policy("meta", "train")


def test_training_refuses_api_outputs():
    ok = {"id": "a", "split": "train", "never_train": False, "provenance": {"backend": "glimmer"}}
    assert_trainable([ok, {**ok, "provenance": {"backend": "spark-open"}}])
    for bad in ({**ok, "never_train": True}, {**ok, "provenance": {"backend": "meta"}}, {**ok, "split": "bench"}):
        with pytest.raises(PolicyError):
            assert_trainable([ok, bad])


def test_plan_has_30_percent_controls_and_is_reproducible():
    p = plan(30, hard_only=False, seed=1, prefix="T")
    kinds = [s.subtype.kind for s in p]
    assert kinds.count("control") == 9
    assert {s.subtype.id for s in p} == {s.id for s in ERRORS + CONTROLS}
    again = plan(30, hard_only=False, seed=1, prefix="T")
    assert [(s.subtype.id, s.exam, s.reason, s.age, s.seed) for s in p] == [(s.subtype.id, s.exam, s.reason, s.age, s.seed) for s in again]
    hard = plan(20, hard_only=True, seed=1, prefix="B")
    assert all(s.subtype.hard for s in hard) and [s.subtype.kind for s in hard].count("control") == 6


FIN = "Nódulo sólido en el lóbulo superior derecho de 12 mm. No hay derrame pleural."


def test_quotes_must_be_literal():
    d = {"indication": "Control de nódulo.", "findings": FIN, "impression": "Nódulo de 1,2 mm en el lóbulo superior derecho.",
         "error": {"body_excerpt": "nódulo de 12 mm", "impression_excerpt": "Nódulo de 1,2 mm"}}
    assert validate(spec("medida"), d) == "body_excerpt not literal"
    d["error"]["body_excerpt"] = "lóbulo superior derecho de 12 mm"
    assert validate(spec("medida"), d) is None


def test_provable_types_must_be_caught_by_the_rules():
    d = {"indication": "Control.", "findings": FIN, "impression": "Nódulo de 12 mm en el lóbulo superior derecho.",
         "error": {"body_excerpt": "12 mm", "impression_excerpt": "12 mm"}}
    assert validate(spec("medida"), d) == "measure_mismatch not provable by the rules"


def test_controls_must_not_trip_the_rules():
    ok = {"indication": "Control.", "findings": FIN, "impression": "Nódulo de 1,2 cm en el lóbulo superior derecho.", "error": None}
    assert validate(spec("control_parafrasis"), ok) is None
    bad = {**ok, "impression": "Nódulo de 1,2 cm en el lóbulo superior izquierdo."}
    assert validate(spec("control_parafrasis"), bad).startswith("control trips the rules")
    three = {"indication": "Control.", "findings": "Masa renal derecha de 32 x 25 x 20 mm.", "impression": "Masa renal derecha de 32 mm.", "error": None}
    assert validate(spec("control_dimension"), three) is None


def test_doble_chequeo_quotes_the_critical_reason():
    d = {"indication": "Sospecha de TEP.", "findings": "Arterias pulmonares permeables.", "impression": "Estudio dentro de límites normales.",
         "error": {"body_excerpt": "Arterias pulmonares permeables.", "impression_excerpt": ""}}
    assert validate(spec("doble_chequeo"), d) == "body_excerpt not literal"
    d["error"]["body_excerpt"] = "Sospecha de TEP"
    assert validate(spec("doble_chequeo"), d) is None


def test_non_rule_types_must_not_carry_an_extra_provable_error():
    d = {"indication": "Control.", "findings": FIN + " Adenopatía hiliar derecha de 15 mm.",
         "impression": "Nódulo de 10 mm en el lóbulo superior derecho.",
         "error": {"body_excerpt": "Adenopatía hiliar derecha de 15 mm.", "impression_excerpt": ""}}
    assert validate(spec("omision"), d).startswith("extra provable error")


def test_unit_each_spells_every_dimension():
    assert unit_each("Masa de 32 x 25 x 20 mm y quiste de 1,2×0,8 cm.") == "Masa de 32 mm x 25 mm x 20 mm y quiste de 1,2 cm x 0,8 cm."


def test_reasons_fit_the_study():
    by_exam = {st.exam: st for st in STUDIES}
    for s in plan(200, hard_only=False, seed=3, prefix="T"):
        st = by_exam[s.exam]
        assert s.reason in (st.critical if s.subtype.id == "doble_chequeo" else st.reasons)
    assert not by_exam["RX de rodilla"].critical  # a knee X-ray is never a critical study
