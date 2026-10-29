import json

import pytest

from radqc.generate import Spec, assert_trainable, plan as official_plan
from radqc.spark_v5 import (
    NORMAL_TEMPLATES,
    build_messages,
    build_record,
    load_plan_file,
    validate_case,
)
from radqc.taxonomia import BY_ID, STUDIES, SUBTYPES, validate


def study_of(exam):
    return next(s for s in STUDIES if s.exam == exam)


REASON_TEP = study_of("Angio-TC de tórax").critical[0]


def doble_spec():
    st = study_of("Angio-TC de tórax")
    return Spec("T5-0001", BY_ID["doble_chequeo"], st.modality, st.exam, st.critical[0],
                "M", 55, 7)


def correct_angio():
    return {"indication": "Dolor torácico y dímero D elevado; descartar tromboembolismo pulmonar.",
            "findings": ("Arterias pulmonares sin defectos de llenado. Aorta de calibre normal. "
                         "Sin derrame pleural."),
            "impression": "Sin tromboembolismo pulmonar."}


def doble_data(parafrasis=False):
    tpl = NORMAL_TEMPLATES["Angio-TC de tórax"]
    if parafrasis:
        findings = "Los vasos pulmonares se ven permeables y la aorta es de calibre normal."
        impression = "Estudio sin evidencia de TEP."
    else:
        findings, impression = tpl["findings"], tpl["impression"]
    return {"correct_report": correct_angio(),
            "variant": {"report": {"indication": f"{REASON_TEP} Se solicita angio-TC.",
                                   "findings": findings, "impression": impression},
                        "error": {"body_excerpt": REASON_TEP, "impression_excerpt": "",
                                  "explanation": "Estudio crítico informado con plantilla normal."}}}


def test_templates_cover_every_study_and_are_clean():
    assert set(NORMAL_TEMPLATES) == {s.exam for s in STUDIES}
    for exam, tpl in NORMAL_TEMPLATES.items():
        assert validate(BY_ID["control"], {"indication": "Control.", "findings": tpl["findings"],
                                           "impression": tpl["impression"], "error": None}) is None


def test_train_plan_mix_and_study_reasons():
    p = official_plan(20, hard_only=True, seed=178, prefix="T5")
    assert len(p) == 20
    assert sum(1 for s in p if s.subtype.kind == "control") == 6
    assert sum(1 for s in p if s.subtype.id == "doble_chequeo") >= 3
    assert {s.subtype.id for s in p} <= {s.id for s in SUBTYPES}
    for s in p:
        st = next(x for x in STUDIES if x.modality == s.modality and x.exam == s.exam)
        if s.subtype.id == "doble_chequeo":
            assert st.critical and s.reason in st.critical
        else:
            assert s.reason in st.reasons


def test_doble_chequeo_requires_literal_template():
    assert validate_case(doble_spec(), doble_data()) is None
    assert validate_case(doble_spec(), doble_data(parafrasis=True)) == \
        "doble_chequeo no usa la plantilla normal literal"


def test_error_cases_delegate_to_the_official_validator():
    st = study_of("TC de tórax")
    spec = Spec("T5-0002", BY_ID["medida"], st.modality, st.exam, st.reasons[0], "F", 60, 8)
    correct = {"indication": "Control de nódulo pulmonar conocido.",
               "findings": ("Nódulo sólido en el lóbulo superior derecho de 12 mm. "
                            "Sin derrame pleural."),
               "impression": "Nódulo pulmonar derecho de 12 mm. Se sugiere control."}
    bad = {"correct_report": correct,
           "variant": {"report": {**correct,
                                  "impression": "Nódulo pulmonar derecho de 25 mm. Se sugiere control."},
                       "error": {"body_excerpt": "nódulo de 12 mm",
                                 "impression_excerpt": "de 25 mm", "explanation": "x"}}}
    assert validate_case(spec, bad) == "body_excerpt not literal"
    good = {"correct_report": correct,
            "variant": {"report": {**correct,
                                   "impression": "Nódulo pulmonar derecho de 25 mm. Se sugiere control."},
                        "error": {"body_excerpt": "lóbulo superior derecho de 12 mm",
                                  "impression_excerpt": "de 25 mm", "explanation": "Medida cambiada."}}}
    assert validate_case(spec, good) is None


def test_record_is_trainable():
    rec = build_record(doble_spec(), doble_data(), model="m", plan_seed=178)
    assert rec["split"] == "train" and rec["never_train"] is False
    assert rec["generator"] == "spark-open" and rec["provenance"]["backend"] == "spark-open"
    assert_trainable([rec])


def test_plan_file_loads_exact_specs(tmp_path):
    st = study_of("RX de abdomen")
    raw = {"seed": 4, "prefix": "M6",
           "cases": [{"id": "M6-0002", "subtype": "control_pregunta_cuerpo", "exam": st.exam,
                      "reason": st.reasons[2], "sex": "F", "age": 31, "seed": 1124077024}]}
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(raw), encoding="utf-8")
    specs = load_plan_file(str(p))
    assert [(s.id, s.subtype.id, s.modality, s.exam, s.reason, s.sex, s.age, s.seed) for s in specs] == [
        ("M6-0002", "control_pregunta_cuerpo", st.modality, st.exam, st.reasons[2], "F", 31, 1124077024)]
    bad = {"seed": 4, "prefix": "M6",
           "cases": [{"id": "X", "subtype": "no_existe", "exam": st.exam,
                      "reason": st.reasons[0], "sex": "F", "age": 40, "seed": 1}]}
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="subtipo desconocido"):
        load_plan_file(str(p))


def test_prompt_embeds_template_for_verify_and_null_for_control():
    assert NORMAL_TEMPLATES["Angio-TC de tórax"]["findings"] in build_messages(doble_spec())[0]["content"]
    st = study_of("RX de tórax")
    ctrl = Spec("T5-0003", BY_ID["control"], st.modality, st.exam, st.reasons[0], "F", 40, 9)
    assert '"variant" es null' in build_messages(ctrl)[0]["content"]
