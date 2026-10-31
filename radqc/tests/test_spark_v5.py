from radqc.spark_v5 import Plan, plan, validate


def good_report():
    return {"indicacion": "Tos de 3 semanas.",
            "hallazgos": "Nódulo sólido en el lóbulo superior derecho de 12 mm, de bordes lisos. Sin derrame pleural. Sin adenopatías.",
            "impresion": "Nódulo pulmonar derecho de 12 mm. Se sugiere control."}


def test_plan_reserves_thirty_percent_controls():
    p = plan(20, seed=178)
    assert len(p) == 20
    assert sum(1 for s in p if not s.receta) == 6
    assert {s.modalidad for s in p} == {"RX tórax", "TC tórax"}
    assert all(s.motivo for s in p)
    assert [s.id for s in p] == [s.id for s in plan(20, seed=178)]
    dc = [s for s in p if s.receta == ("doble_chequeo",)]
    assert dc and all(s.tecnologo_critico for s in dc)


def test_clean_case_has_no_variants():
    spec = Plan("V5-0001", "RX tórax", "Tos.", False, ())
    assert validate(spec, {"informe_correcto": good_report(), "variantes": []}) is None
    bad = {"informe_correcto": good_report(),
           "variantes": [{"informe": good_report(),
                          "errores": [{"tipo": "medida", "descripcion": "x", "campo": "impresion"}],
                          "es_error": True}]}
    assert validate(spec, bad) == "se esperaban 0 variantes"


def test_error_variant_must_match_recipe():
    spec = Plan("V5-0002", "TC tórax", "Nódulo.", False, ("lateralidad",))
    var = {"informe": {**good_report(),
                        "impresion": "Nódulo pulmonar izquierdo de 12 mm. Se sugiere control."},
           "errores": [{"tipo": "lateralidad", "descripcion": "Lado cambiado en la impresión.",
                        "campo": "impresion"}],
           "es_error": True}
    assert validate(spec, {"informe_correcto": good_report(), "variantes": [var]}) is None
    wrong = {**var, "errores": [{"tipo": "medida", "descripcion": "x", "campo": "impresion"}]}
    assert validate(spec, {"informe_correcto": good_report(), "variantes": [wrong]}).startswith("tipo")


def test_doble_chequeo_is_verify_not_error():
    spec = Plan("V5-0003", "RX tórax", "Disnea súbita.", True, ("doble_chequeo",))
    var = {"informe": good_report(),
           "errores": [{"tipo": "doble_chequeo", "descripcion": "Estudio crítico con plantilla normal.",
                        "campo": "impresion"}],
           "es_error": False}
    assert validate(spec, {"informe_correcto": good_report(), "variantes": [var]}) is None
    marked_error = {**var, "es_error": True}
    assert validate(spec, {"informe_correcto": good_report(), "variantes": [marked_error]}).startswith(
        "doble_chequeo")


def test_rejects_institutions_and_bad_fields():
    spec = Plan("V5-0004", "RX tórax", "Tos.", False, ("medida",))
    rep = good_report()
    var = {"informe": {**rep, "impresion": "Nódulo de 21 mm. Control en el Hospital San José."},
           "errores": [{"tipo": "medida", "descripcion": "Medida cambiada.", "campo": "impresion"}],
           "es_error": True}
    assert validate(spec, {"informe_correcto": rep, "variantes": [var]}).startswith("posible nombre")
    var2 = {**var, "informe": {**rep, "impresion": "Nódulo de 21 mm."},
            "errores": [{"tipo": "medida", "descripcion": "x", "campo": "titulo"}]}
    assert validate(spec, {"informe_correcto": rep, "variantes": [var2]}).startswith("campo")


def test_clinical_language_is_not_an_institution():
    spec = Plan("V5-0005", "RX tórax", "Tos.", False, ("medida",))
    rep = {"indicacion": "Tos.",
           "hallazgos": "Nódulo de 12 mm. Se sugiere correlación clínica y control.",
           "impresion": "Nódulo de 21 mm. Correlación clínica."}
    var = {"informe": rep,
           "errores": [{"tipo": "medida", "descripcion": "Medida cambiada.", "campo": "impresion"}],
           "es_error": True}
    assert validate(spec, {"informe_correcto": rep, "variantes": [var]}) is None
    named = {"informe": {**rep, "impresion": "Nódulo de 21 mm. Paciente Juan Pérez."},
             "errores": [{"tipo": "medida", "descripcion": "x", "campo": "impresion"}],
             "es_error": True}
    assert validate(spec, {"informe_correcto": rep, "variantes": [named]}).startswith("posible nombre")
