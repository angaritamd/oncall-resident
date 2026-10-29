"""Error taxonomy for RAD·QC v5 datasets (benchmark and training), as defined by Miguel (ANG-174, v2).

Three kinds of case:
- error: four types, each mapped to the checker label in core/oncall_core/qc.py (`TYPES`);
- verify: doble_chequeo, a critical study with a stated reason reported with the normal template. It is NOT an
  error: the checker should ask to verify ("Verificar"), not flag it;
- control (~30 % of a set): correct reports, most of them looking like an error that is not one (the "NO es error"
  list below), so false alarms are measured.
`hard` subtypes are the ones a hard benchmark draws from.

This module is the official taxonomy and case validator for every generator (Glimmer, Wonder, Spark Open):
import SUBTYPES, STUDIES (valid reasons for consultation per study) and validate() from here.
"""
import re
import unicodedata
from dataclasses import dataclass

from oncall_core.qc import TYPES, rule_issues

VERSION = "taxonomy-v3"   # v3: pregunta sin responder = the IMPRESSION does not answer the question explicitly
PROMPT_VERSION = "gen-v3"  # bump when the generation prompt changes; stored in every case
CONTROL_SHARE = 0.30


@dataclass(frozen=True)
class Subtype:
    id: str
    kind: str            # error | verify | control
    label: str | None    # what the checker must say: a qc.TYPES label, "doble_chequeo", or None for a control
    hard: bool
    es: str              # short name shown on /bench
    recipe: str          # instruction for the generator (Spanish: the reports are Spanish)


SUBTYPES = [
    Subtype("lateralidad", "error", "laterality_mismatch", False, "Lateralidad",
            "La IMPRESIÓN cambia el lado (derecho/izquierdo) de un hallazgo descrito en HALLAZGOS."),
    Subtype("medida", "error", "measure_mismatch", False, "Medida",
            "La IMPRESIÓN repite una medida de HALLAZGOS con otro valor (otro número, o la unidad cambiada sin "
            "convertir, p. ej. 1,2 cm → 1,2 mm)."),
    Subtype("omision", "error", "omitted_finding", True, "Omisión con impacto en el manejo",
            "HALLAZGOS describe un hallazgo que cambia el manejo del paciente (requiere seguimiento, estudio "
            "adicional o conducta) y la IMPRESIÓN no lo menciona. No vale omitir algo menor."),
    Subtype("pregunta", "error", "indication_unanswered", True, "Pregunta sin responder",
            "La INDICACIÓN hace una pregunta clínica concreta (p. ej. descartar neumotórax) y la IMPRESIÓN no la "
            "responde explícitamente. No basta con que HALLAZGOS la responda ni con una IMPRESIÓN genérica («estudio "
            "dentro de límites normales»). Sí es respuesta una IMPRESIÓN que nombra la pregunta, aunque sea con "
            "limitación («apéndice no visualizado; no se puede descartar apendicitis»). body_excerpt es la pregunta "
            "copiada de la INDICACIÓN, no de HALLAZGOS."),
    Subtype("doble_chequeo", "verify", "doble_chequeo", True, "Doble chequeo (verificar)",
            "Estudio con motivo crítico explícito en la INDICACIÓN (p. ej. sospecha de TEP, de hemorragia o de "
            "neumotórax a tensión) informado con la plantilla normal: HALLAZGOS normales e IMPRESIÓN normal. No es "
            "un error; pide verificación humana. body_excerpt es el motivo crítico copiado de la INDICACIÓN."),
    # controls: correct reports. Except the first, each one looks like an error that is not one.
    Subtype("control", "control", None, False, "Control sin error",
            "Informe correcto: la IMPRESIÓN es coherente con HALLAZGOS y responde la INDICACIÓN."),
    Subtype("control_negativos", "control", None, True, "Control: negativos pertinentes",
            "Informe correcto donde HALLAZGOS incluye negativos pertinentes (p. ej. «sin derrame pleural») que la "
            "IMPRESIÓN no repite, porque no responden la pregunta de la INDICACIÓN."),
    Subtype("control_subrasgos", "control", None, True, "Control: diagnóstico resumido",
            "Informe correcto donde HALLAZGOS describe los rasgos de un diagnóstico (p. ej. engrosamiento parietal, "
            "líquido pericolecístico, cálculo) y la IMPRESIÓN los resume en el diagnóstico (colecistitis aguda)."),
    Subtype("control_menores", "control", None, True, "Control: hallazgo menor",
            "Informe correcto con un hallazgo menor sin impacto en el manejo en HALLAZGOS (p. ej. cambios "
            "degenerativos leves) que la IMPRESIÓN no menciona."),
    Subtype("control_dimension", "control", None, True, "Control: una dimensión",
            "Informe correcto donde HALLAZGOS da tres dimensiones de una lesión (p. ej. 32 x 25 x 20 mm) y la "
            "IMPRESIÓN da solo la mayor (32 mm)."),
    Subtype("control_parafrasis", "control", None, True, "Control: paráfrasis",
            "Informe correcto donde la IMPRESIÓN dice con otras palabras lo mismo que HALLAZGOS (sin cambiar lado, "
            "medida ni sentido)."),
    Subtype("control_limitacion", "control", None, True, "Control: respondida con limitación",
            "Informe correcto donde la IMPRESIÓN responde la pregunta de la INDICACIÓN con una limitación explícita "
            "(p. ej. «no se identifica TEP central; evaluación subsegmentaria limitada por artefacto respiratorio»)."),
]
BY_ID = {s.id: s for s in SUBTYPES}
ERRORS = [s for s in SUBTYPES if s.kind != "control"]
CONTROLS = [s for s in SUBTYPES if s.kind == "control"]
assert all(s.label in TYPES for s in SUBTYPES if s.kind == "error")

STYLE = ("Informe en español, con el estilo de un radiólogo colombiano (términos y giros usuales en Colombia), "
         "sin nombres de pacientes, médicos ni instituciones, sin fechas ni identificadores.")


@dataclass(frozen=True)
class Study:
    modality: str
    exam: str
    reasons: tuple[str, ...]    # valid reasons for consultation for this study (concrete clinical questions)
    critical: tuple[str, ...]   # critical reasons, for doble_chequeo; empty = the study is never a critical one


# Only reasons that make sense for the modality and region: no "sospecha de TEP" on a knee X-ray.
STUDIES = [
    Study("RX", "RX de tórax",
          ("Tos y fiebre de 5 días; descartar neumonía.", "Disnea; descartar derrame pleural.",
           "Control de catéter venoso central.", "Trauma torácico cerrado; descartar fracturas costales."),
          ("Dolor torácico súbito tras procedimiento; descartar neumotórax a tensión.",)),
    Study("RX", "RX de abdomen",
          ("Distensión y vómito; descartar obstrucción intestinal.", "Control de litiasis renal conocida.",
           "Estreñimiento crónico; valoración de patrón gaseoso."),
          ("Dolor abdominal súbito y defensa; descartar neumoperitoneo.",)),
    Study("RX", "RX de rodilla",
          ("Trauma en rodilla; descartar fractura.", "Dolor crónico; valoración de cambios degenerativos.",
           "Derrame articular; descartar lesión ósea."),
          ()),
    Study("TC", "TC de tórax",
          ("Control de nódulo pulmonar conocido.", "Tos crónica y pérdida de peso; descartar neoplasia.",
           "Estadificación de neoplasia conocida."),
          ()),
    Study("TC", "Angio-TC de tórax",
          ("Dolor torácico y dímero D elevado; descartar tromboembolismo pulmonar.",),
          ("Sospecha de tromboembolismo pulmonar con inestabilidad hemodinámica.",
           "Dolor torácico desgarrante; descartar disección aórtica.")),
    Study("TC", "TC de abdomen y pelvis con contraste",
          ("Dolor en fosa ilíaca derecha; descartar apendicitis.", "Dolor en hipocondrio derecho; descartar colecistitis.",
           "Pérdida de peso; descartar masa abdominal.", "Fiebre posoperatoria; descartar colección."),
          ("Trauma abdominal cerrado con hipotensión; descartar lesión de víscera sólida.",)),
    Study("TC", "TC de cráneo simple",
          ("Cefalea crónica de reciente cambio de patrón.", "Trauma craneal leve; descartar lesión intracraneal."),
          ("Déficit neurológico súbito; descartar hemorragia intracraneal.",
           "Trauma craneoencefálico con deterioro de la conciencia; descartar hematoma.")),
]


DIMS = re.compile(r"(\d+(?:[.,]\d+)?)((?:\s*[x×]\s*\d+(?:[.,]\d+)?)+)\s*(mm|cm)\b", re.I)


def unit_each(text: str) -> str:
    """'32 x 25 x 20 mm' -> '32 mm x 25 mm x 20 mm': every dimension with its unit, for generators that compare
    individual dimensions. The checker itself takes the largest one (qc.py)."""
    def rep(m):
        nums = [m.group(1)] + re.findall(r"\d+(?:[.,]\d+)?", m.group(2))
        return " x ".join(f"{n} {m.group(3)}" for n in nums)
    return DIMS.sub(rep, text)


# words of a clinical question that do not name what is asked about (sides too: "neumotórax derecho" is not
# answered by "catéter venoso central derecho")
QUESTION_STOP = {"descartar", "sospecha", "evaluar", "valorar", "valoracion", "control", "aguda", "agudo", "agudos",
                 "agudas", "solicita", "presencia", "posible", "signos", "paciente", "conocido", "conocida",
                 "derecho", "derecha", "izquierdo", "izquierda", "bilateral"}


def _fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def question_stems(question: str) -> set[str]:
    """5-letter stems of the words that name what a clinical question asks about."""
    return {w[:5] for w in re.findall(r"[a-z]{5,}", _fold(question)) if w not in QUESTION_STOP}


def addresses(question: str, impression: str) -> bool:
    """Whether the IMPRESSION names what the question asks about, by 5-letter stems without accents. "descartar
    apendicitis aguda" is answered by "sin signos de apendicitis" and by "apéndice no visualizado; no se puede
    descartar apendicitis", not by "estudio dentro de límites normales". The findings never count."""
    words = {w[:5] for w in re.findall(r"[a-z]{5,}", _fold(impression))}
    return bool(question_stems(question) & words)


def validate(subtype: Subtype | str, data: dict) -> str | None:
    """Why a generated case is rejected, or None. `data` = {indication, findings, impression, error}.
    Quotes must be literal; measurement and laterality errors must be provable by the checker's rules; any other case
    must not trip them; controls carry no error."""
    st = BY_ID[subtype] if isinstance(subtype, str) else subtype
    if not isinstance(data, dict):
        return "no JSON object"
    ind, fin, imp = (str(data.get(k) or "").strip() for k in ("indication", "findings", "impression"))
    if not (ind and fin and imp):
        return "missing section"
    err = data.get("error")
    rules = {i.rule for i in rule_issues(fin, imp)}
    if st.kind == "control":
        if err:
            return "control with an error"
        if rules:
            return f"control trips the rules: {sorted(rules)}"
        return None
    if not isinstance(err, dict):
        return "error missing"
    body, imp_x = str(err.get("body_excerpt") or "").strip(), str(err.get("impression_excerpt") or "").strip()
    src = ind if st.label in ("indication_unanswered", "doble_chequeo") else fin
    if not body or body not in src:
        return "body_excerpt not literal"
    if imp_x and imp_x not in imp:
        return "impression_excerpt not literal"
    # an unanswered question: the impression must not name it (findings that answer it do not count). An excerpt
    # that names nothing ("se solicita") could never be answered, so it is refused instead of passing
    if st.label == "indication_unanswered":
        if not question_stems(body):
            return "body_excerpt names no clinical question"
        if addresses(body, imp):
            return "question answered in the impression"
    if st.label in ("measure_mismatch", "laterality_mismatch") and st.label not in rules:
        return f"{st.label} not provable by the rules"
    if st.label not in ("measure_mismatch", "laterality_mismatch") and rules:
        return f"extra provable error: {sorted(rules)}"
    return None
