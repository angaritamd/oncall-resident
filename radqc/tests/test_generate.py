import pytest

from radqc.generate import FIXED, MIXES, Budget, PolicyError, assert_trainable, check_policy, plan, worst_call_usd
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


# pregunta sin responder (taxonomy-v3): only the IMPRESSION counts; B5-0019 is the reference case
B5_0019 = {
    "indication": "Mujer de 53 años con dolor en fosa ilíaca derecha, se solicita descartar apendicitis aguda.",
    "findings": "Apéndice cecal de calibre normal (5 mm), sin engrosamiento parietal, sin realce anómalo ni cambios "
                "inflamatorios en la grasa periapendicular. Se observa quiste ovárico derecho de 32 mm, de contenido "
                "líquido homogéneo y paredes finas. No se evidencia líquido libre ni colecciones intraabdominales.",
    "impression": "Quiste ovárico derecho de 32 mm, de aspecto simple.",
    "error": {"body_excerpt": "descartar apendicitis aguda", "impression_excerpt": ""},
}


def test_b5_0019_as_is_is_an_unanswered_question():
    assert validate(spec("pregunta"), B5_0019) is None  # the findings answer it; the impression does not


def test_impression_that_answers_is_not_an_error():
    answered = {**B5_0019, "impression": "Apéndice normal, sin signos de apendicitis. Quiste ovárico derecho de 32 mm."}
    assert validate(spec("pregunta"), answered) == "question answered in the impression"


def test_generic_normal_impression_is_an_error():
    generic = {**B5_0019, "impression": "Estudio dentro de límites normales."}
    assert validate(spec("pregunta"), generic) is None


def test_impression_with_a_limitation_is_not_an_error():
    limited = {**B5_0019, "findings": "Apéndice cecal no visualizado. Quiste ovárico derecho de 32 mm.",
               "impression": "Apéndice no visualizado; no se puede descartar apendicitis. Quiste ovárico derecho de 32 mm."}
    assert validate(spec("pregunta"), limited) == "question answered in the impression"


def test_pilot_questions_validated_by_miguel_stay_errors():
    import json
    from pathlib import Path
    pilot = {r["id"]: r for r in map(json.loads, Path(__file__).parents[1].joinpath("data/bench/pilot.jsonl").read_text().splitlines())}
    for cid in ("B5-0004", "B5-0009", "B5-0014", "B5-0019"):
        r = pilot[cid]
        assert validate(spec("pregunta"), {**r, "error": r["expected"]}) is None, cid


def test_bench_v2_mix_and_even_studies():
    import collections
    p = plan(60, hard_only=False, seed=274, prefix="B6", mix=MIXES["bench-v2"])
    assert collections.Counter(s.subtype.id for s in p) == collections.Counter(MIXES["bench-v2"])
    per_study = collections.Counter(s.exam for s in p)
    assert len(per_study) == len(STUDIES) and max(per_study.values()) - min(per_study.values()) <= 1
    by_exam = {st.exam: st for st in STUDIES}
    dc = collections.Counter(s.exam for s in p if s.subtype.id == "doble_chequeo")
    assert all(by_exam[e].critical for e in dc) and max(dc.values()) - min(dc.values()) <= 1


def test_budget_stops_before_the_cap():
    b = Budget(5.0, reserve_usd=0.24)
    b.spent = 4.70
    assert b.allows()
    b.spent = 4.77
    assert not b.allows() and b.hit
    assert Budget(None).allows()


def test_spend_cap_needs_a_price_and_reserves_the_worst_case():
    check_policy("meta", "bench", "muse-wonder-1.0", 5.0)
    with pytest.raises(PolicyError):
        check_policy("meta", "bench", "muse-wonder-2.0", 5.0)
    assert 0.08 < worst_call_usd("muse-wonder-1.0") < 0.09


def test_an_excerpt_that_names_no_question_is_refused():
    empty = {**B5_0019, "indication": "Se solicita estudio. Descartar apendicitis aguda.",
             "error": {"body_excerpt": "Se solicita", "impression_excerpt": ""}}
    assert validate(spec("pregunta"), empty) == "body_excerpt names no clinical question"


# MUSE (ANG-178) training pilot, copied here only for the test: the impression names the anatomy, not the pathology
T5_0007 = {
    "indication": "Hombre de 41 años con dolor torácico y dímero D elevado, se solicita angio-TC de tórax para descartar "
                  "tromboembolismo pulmonar.",
    "findings": "Angio-TC de tórax con adecuada opacificación del tronco de la arteria pulmonar y sus ramas principales y "
                "segmentarias. No se identifican defectos de llenado endoluminales compatibles con tromboembolismo "
                "pulmonar. Parénquima pulmonar sin consolidaciones, sin derrame pleural y sin neumotórax. Se observa "
                "pequeño nódulo subpleural en el lóbulo inferior derecho de 6 mm, sin calcificaciones ni cavitación.",
    "impression": "Parénquima pulmonar sin consolidaciones ni derrame pleural. Nódulo subpleural de 6 mm en lóbulo "
                  "inferior derecho, de aspecto inespecífico, se sugiere correlación clínica y seguimiento ambulatorio.",
    "error": {"body_excerpt": "descartar tromboembolismo pulmonar", "impression_excerpt": ""},
}
T5_0017 = {
    "indication": "Mujer de 26 años con disnea, se solicita descartar derrame pleural.",
    "findings": "Radiografía de tórax PA y lateral con técnica y grado de inspiración adecuados. Silueta "
                "cardiomediastínica de tamaño y contornos conservados. Parénquima pulmonar sin opacidades alveolares ni "
                "intersticiales de aspecto patológico. Senos costofrénicos y cardiofrénicos libres, sin signos de "
                "derrame pleural.",
    "impression": "Estudio sin alteraciones pleuropulmonares significativas. Silueta cardiomediastínica dentro de "
                  "límites normales.",
    "error": {"body_excerpt": "descartar derrame pleural", "impression_excerpt": ""},
}


def test_anatomy_or_region_in_the_impression_is_not_an_answer():
    assert validate(spec("pregunta"), T5_0007) is None  # "parénquima pulmonar" does not answer TEP (critical)
    answered = {**T5_0007, "impression": "Sin signos de tromboembolismo pulmonar. Nódulo subpleural de 6 mm."}
    assert validate(spec("pregunta"), answered) == "question answered in the impression"
    answered = {**T5_0017, "impression": "Sin derrame pleural."}
    assert validate(spec("pregunta"), answered) == "question answered in the impression"
    # derrame pleural is not critical: "pleuropulmonares" still does not answer it, but with the findings silent too
    silent = {**T5_0017, "findings": "Radiografía de tórax PA y lateral con técnica adecuada. Silueta cardiomediastínica "
                                     "de tamaño y contornos conservados."}
    assert validate(spec("pregunta"), silent) is None


# taxonomy-v4: pregunta by criticality. The rest of the ANG-178 pilot cases Miguel reviewed, copied here for the test
T5_0008 = {
    "indication": "Hombre de 53 años con estreñimiento crónico; valoración de patrón gaseoso, descartar obstrucción "
                  "intestinal.",
    "findings": "Radiografía simple de abdomen en proyección anteroposterior con técnica adecuada. Se observa abundante "
                "materia fecal en marco cólico con leve distensión del colon descendente y sigmoides. Patrón gaseoso "
                "intestinal sin dilatación de asas de intestino delgado ni niveles hidroaéreos. No se identifica "
                "neumoperitoneo ni calcificaciones anómalas y las estructuras óseas visualizadas no muestran alteraciones "
                "agudas.",
    "impression": "Coprostasis severa con abundante materia fecal en marco cólico. No se evidencia neumoperitoneo.",
    "error": {"body_excerpt": "descartar obstrucción intestinal", "impression_excerpt": ""},
}
T5_0011 = {  # control_menores: trauma craneal leve, a critical question the impression answers
    "indication": "Mujer de 80 años con trauma craneal leve, estudio solicitado para descartar lesión intracraneal.",
    "findings": "TC simple de cráneo sin contraste endovenoso con adecuada visualización del parénquima cerebral. No se "
                "observan hematomas intra o extraaxiales, focos de contusión ni edema cerebral asociado. Sistema "
                "ventricular y cisternas basales de morfología y amplitud conservadas, sin desviación de la línea media "
                "y sin fracturas craneales evidentes. Como hallazgo incidental se observan calcificaciones ateromatosas "
                "leves de los sifones carotídeos y cambios involutivos encefálicos leves acordes a la edad.",
    "impression": "TC simple de cráneo sin evidencia de lesión intracraneal hemorrágica aguda ni efecto de masa. No se "
                  "identifican fracturas craneales.",
    "error": None,
}
T5_0013 = {
    "indication": "Hombre de 33 años con disnea, se solicita radiografía de tórax para descartar derrame pleural.",
    "findings": "Parénquima pulmonar adecuadamente expandido, sin consolidaciones ni opacidades alveolares. Se identifica "
                "granuloma calcificado de 4 mm en el lóbulo inferior derecho, sin cambios respecto a estudios previos. "
                "Silueta cardiomediastínica de tamaño y morfología dentro de límites normales. No se evidencia derrame "
                "pleural ni engrosamiento pleural, con senos costofrénicos y cardiofrénicos libres.",
    "impression": "Granuloma calcificado de 4 mm en lóbulo inferior derecho sin relevancia clínica. Silueta "
                  "cardiomediastínica dentro de límites normales.",
    "error": {"body_excerpt": "para descartar derrame pleural", "impression_excerpt": ""},
}
T5_0016 = {
    "indication": "Hombre de 49 años con trauma en rodilla derecha, remitido para descartar fractura.",
    "findings": "Radiografías AP y lateral de rodilla derecha. No se identifican trazos de fractura ni luxación. Relaciones "
                "articulares femorotibiales y patelofemorales conservadas, sin derrame articular evidente. Cambios "
                "osteoartrósicos incipientes con leve osteofitosis marginal.",
    "impression": "Gonartrosis incipiente sin alteraciones en la alineación.",
    "error": {"body_excerpt": "para descartar fractura", "impression_excerpt": ""},
}


def test_critical_questions():
    from radqc.taxonomia import is_critical
    for q in ("descartar tromboembolismo pulmonar", "descartar disección aórtica", "descartar hemorragia intracraneal",
              "descartar lesión intracraneal", "descartar neumoperitoneo", "descartar apendicitis aguda",
              "descartar colecistitis", "descartar neumotórax a tensión", "descartar lesión de víscera sólida",
              "descartar ACV isquémico agudo", "descartar isquemia mesentérica", "descartar torsión ovárica"):
        assert is_critical(q), q
    for q in ("descartar derrame pleural", "descartar neumonía", "descartar fractura", "descartar lesión ósea",
              "descartar neoplasia", "descartar colección", "descartar masa abdominal"):
        assert not is_critical(q), q
    # bowel obstruction: critical only in an acute presentation; chronic or unknown is not
    assert is_critical("descartar obstrucción intestinal", "Distensión y vómito; descartar obstrucción intestinal.")
    assert is_critical("descartar obstrucción intestinal", "Dolor abdominal agudo; descartar obstrucción intestinal.")
    assert not is_critical("descartar obstrucción intestinal", T5_0008["indication"])
    assert not is_critical("descartar obstrucción intestinal", "Se solicita descartar obstrucción intestinal.")


def test_pilot_false_alarms_are_no_longer_errors():
    # Miguel's review of the ANG-178 pilot: non-critical questions answered in the findings
    for case in (T5_0008, T5_0013, T5_0016, T5_0017):
        assert validate(spec("pregunta"), case) == "non-critical question answered in the findings"
        assert validate(spec("control_pregunta_cuerpo"), {**case, "error": None}) is None


def test_findings_can_answer_a_non_critical_question_with_its_signs():
    knee = {"indication": "Dolor crónico de rodilla, se solicita descartar cambios degenerativos.",
            "findings": "Interlínea articular conservada, sin pinzamiento. No se identifican osteofitos marginales ni "
                        "esclerosis subcondral.",
            "impression": "Estudio dentro de límites normales.",
            "error": {"body_excerpt": "descartar cambios degenerativos", "impression_excerpt": ""}}
    assert validate(spec("pregunta"), knee) == "non-critical question answered in the findings"


def test_critical_questions_stay_errors_when_only_the_findings_answer():
    assert validate(spec("pregunta"), T5_0007) is None  # TEP
    assert validate(spec("pregunta"), B5_0019) is None  # apendicitis


def test_a_control_must_answer_a_critical_question_in_the_impression():
    assert validate(spec("control_menores"), T5_0011) is None  # trauma craneal leve: the impression names it
    silent = {**T5_0011, "impression": "Cambios involutivos encefálicos leves acordes a la edad."}
    assert validate(spec("control_menores"), silent) == "control leaves a critical question unanswered in the impression"


def test_a_critical_question_is_answered_only_by_its_own_pattern():
    # "fracturas" or "contusión" do not answer "descartar lesión intracraneal" (the broad "lesion" row would)
    fracture = {**T5_0011, "impression": "No se identifican fracturas craneales ni contusiones de tejidos blandos."}
    assert validate(spec("control_menores"), fracture) == "control leaves a critical question unanswered in the impression"
    as_error = {**fracture, "error": {"body_excerpt": "descartar lesión intracraneal", "impression_excerpt": ""}}
    assert validate(spec("pregunta"), as_error) is None
    hematoma = {**T5_0011, "impression": "Sin hematomas intra ni extraaxiales."}
    assert validate(spec("control_menores"), hematoma) is None


def test_every_subtype_but_pregunta_and_doble_chequeo_answers_a_critical_question():
    ind = "Hombre de 60 años con dolor torácico y dímero D elevado, se solicita descartar tromboembolismo pulmonar."
    fin = "No se identifican defectos de llenado. Nódulo de 8 mm en el lóbulo superior derecho."
    omission = {"indication": ind, "findings": fin, "impression": "Sin otros hallazgos relevantes.",
                "error": {"body_excerpt": "Nódulo de 8 mm en el lóbulo superior derecho", "impression_excerpt": ""}}
    assert validate(spec("omision"), omission) == "critical question unanswered in the impression"
    answered = {**omission, "impression": "Sin signos de tromboembolismo pulmonar."}
    assert validate(spec("omision"), answered) is None
    verify = {"indication": ind, "findings": "Estudio sin alteraciones.", "impression": "Estudio dentro de límites normales.",
              "error": {"body_excerpt": "descartar tromboembolismo pulmonar", "impression_excerpt": ""}}
    assert validate(spec("doble_chequeo"), verify) is None


def test_body_answered_control_needs_a_non_critical_question():
    assert validate(spec("control_pregunta_cuerpo"), {**T5_0007, "error": None}) == \
        "control leaves a critical question unanswered in the impression"
    answered = {**T5_0013, "error": None, "impression": "Sin derrame pleural. Granuloma calcificado de 4 mm."}
    assert validate(spec("control_pregunta_cuerpo"), answered) == "no non-critical question answered only in the findings"


def test_body_answered_control_goes_to_studies_with_a_non_critical_question():
    from radqc.taxonomia import asked, is_critical
    p = plan(200, hard_only=False, seed=5, prefix="T")
    ctrl = [s for s in p if s.subtype.id == "control_pregunta_cuerpo"]
    assert ctrl and all(asked(s.reason) and not is_critical(s.reason) for s in ctrl)


def test_every_question_in_studies_names_a_pathology():
    from radqc.taxonomia import asked
    for st in STUDIES:
        for reason in st.reasons + st.critical:
            if "descartar" in reason.lower():
                assert asked(reason), reason


def test_fixed_bench_v2_pc_are_critical_questions_valid_for_their_study():
    from radqc.generate import plan_fixed
    from radqc.taxonomia import is_critical
    specs = plan_fixed("bench-v2-pc", seed=274, prefix="B6", start=61)
    assert [s.id for s in specs] == [f"B6-{i:04d}" for i in range(61, 67)]
    assert all(s.subtype.id == "pregunta" and is_critical(s.reason) for s in specs)
    assert specs == plan_fixed("bench-v2-pc", seed=274, prefix="B6", start=61)  # reproducible
    assert len(FIXED["bench-v2-pc"]) == 6
