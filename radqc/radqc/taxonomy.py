"""Error taxonomy for RAD·QC v5 datasets (benchmark and training).

Each subtype maps to one of the five checker types in core/oncall_core/qc.py (`TYPES`), which is the label the
checker must produce. Subtypes only decide how the error is planted and how hard it is to see; "clean" cases carry
no error and measure false alarms. `hard` subtypes are the ones the benchmark weights up: partial omissions and a
normal template signed on an abnormal study.
"""
from dataclasses import dataclass

from oncall_core.qc import TYPES


@dataclass(frozen=True)
class Subtype:
    id: str
    type: str | None     # checker label in qc.TYPES; None = clean case (no error)
    hard: bool
    es: str              # short name shown on /bench
    recipe: str          # instruction for the generator (Spanish: the reports are Spanish)


SUBTYPES = [
    Subtype("measure_number", "measure_mismatch", False, "Medida distinta",
            "La IMPRESIÓN repite una medida de HALLAZGOS con otro número (p. ej. 12 mm → 21 mm)."),
    Subtype("measure_unit", "measure_mismatch", True, "Medida: unidad cambiada",
            "La IMPRESIÓN cambia la unidad sin convertir (p. ej. 1,2 cm en HALLAZGOS → 1,2 mm en IMPRESIÓN)."),
    Subtype("laterality", "laterality_mismatch", False, "Lateralidad",
            "La IMPRESIÓN cambia el lado (derecho/izquierdo) de un hallazgo de HALLAZGOS."),
    Subtype("omission_total", "omitted_finding", False, "Omisión total",
            "Un hallazgo anormal de HALLAZGOS no aparece en la IMPRESIÓN; la IMPRESIÓN sí resume los demás."),
    Subtype("omission_partial", "omitted_finding", True, "Omisión parcial",
            "HALLAZGOS describe dos hallazgos anormales relacionados (p. ej. dos nódulos, o masa más adenopatía); "
            "la IMPRESIÓN menciona solo uno, de forma que parece completa."),
    Subtype("normal_template", "normal_template_abnormal", True, "Plantilla normal firmada",
            "HALLAZGOS describe un hallazgo anormal claro, pero la IMPRESIÓN es la frase de plantilla normal "
            "(p. ej. «Estudio dentro de límites normales.»)."),
    Subtype("indication_unanswered", "indication_unanswered", True, "Indicación sin responder",
            "La INDICACIÓN pregunta por algo concreto (p. ej. descartar neumotórax) y la IMPRESIÓN no lo "
            "menciona ni lo descarta, aunque HALLAZGOS sí lo aborda. body_excerpt es la pregunta copiada de la INDICACIÓN, "
            "no de HALLAZGOS."),
    Subtype("clean", None, False, "Sin error",
            "Informe correcto: IMPRESIÓN coherente con HALLAZGOS y con la INDICACIÓN."),
    Subtype("clean_tricky", None, True, "Sin error (trampa)",
            "Informe correcto que PARECE tener un error: la misma medida en otra unidad (12 mm = 1,2 cm), un "
            "hallazgo menor e intrascendente fuera de la IMPRESIÓN, o un hallazgo bilateral resumido como tal."),
]
BY_ID = {s.id: s for s in SUBTYPES}
assert all(s.type is None or s.type in TYPES for s in SUBTYPES)

# studies the demo and the generators cover (Spanish exam names)
STUDIES = [
    ("RX", "RX de tórax"), ("RX", "RX de abdomen"), ("RX", "RX de rodilla"),
    ("TC", "TC de tórax"), ("TC", "TC de abdomen y pelvis con contraste"), ("TC", "TC de cráneo simple"),
    ("TC", "Angio-TC de tórax"),
]
