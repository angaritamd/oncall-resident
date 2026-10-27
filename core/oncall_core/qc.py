"""RAD·QC: mechanical checks of a draft report. Never edits the report by itself.

Two layers:
- rules (deterministic): measurement and laterality conflicts between FINDINGS and IMPRESSION, with the
  exact fragments as proof -> severity "error" ("Error demostrado") and an exact proposed correction;
- model (Glimmer, prompt written from scratch): the four mechanical types -> severity "verify"
  ("Verificar"); any quoted fragment that is not literally in the report is discarded.
"""
import json
import re
from dataclasses import asdict, dataclass

SENT = re.compile(r"[^.;\n]+[.;]?")
MEASURE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(mm|cm)\b", re.I)
SIDE = re.compile(r"\b(derech[oa]s?|izquierd[oa]s?|right|left)\b", re.I)
SWAP = {"derecho": "izquierdo", "derecha": "izquierda", "derechos": "izquierdos", "derechas": "izquierdas",
        "izquierdo": "derecho", "izquierda": "derecha", "izquierdos": "derechos", "izquierdas": "derechas",
        "right": "left", "left": "right"}
TYPES = ("measure_mismatch", "laterality_mismatch", "omitted_finding", "normal_template_abnormal", "indication_unanswered")


@dataclass
class Issue:
    rule: str
    severity: str                 # "error" (proven by rules) | "verify" (model)
    body_excerpt: str             # exact fragment of FINDINGS (or INDICATION for indication_unanswered)
    impression_excerpt: str       # exact fragment of IMPRESSION
    body_label: str = "findings"  # findings | indication
    explanation: str = ""
    fix_find: str | None = None   # exact text in IMPRESSION to replace
    fix_replace: str | None = None
    marks: list | None = None     # tokens to highlight: [{"section": ..., "text": ...}]
    source: str = "rules"

    def key(self) -> tuple:
        return (self.rule, self.body_excerpt.strip(), self.impression_excerpt.strip())

    def asdict(self) -> dict:
        return asdict(self)


def sentences(text: str) -> list[str]:
    return [m.group(0).strip() for m in SENT.finditer(text or "") if m.group(0).strip()]


def _mm(value: str, unit: str) -> float:
    v = float(value.replace(",", "."))
    return v * 10 if unit.lower() == "cm" else v


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-záéíóúñü]{4,}", s.lower())}


def _closest(target: str, candidates: list[str]) -> str:
    return max(candidates, key=lambda c: len(_words(c) & _words(target))) if candidates else ""


def measure_issues(findings: str, impression: str) -> list[Issue]:
    f_sents = [s for s in sentences(findings) if MEASURE.search(s)]
    if not f_sents:
        return []
    f_values = {_mm(*m.groups()) for s in f_sents for m in MEASURE.finditer(s)}
    out = []
    for isent in sentences(impression):
        for m in MEASURE.finditer(isent):
            if _mm(*m.groups()) in f_values:
                continue
            fsent = _closest(isent, f_sents)
            fm = list(MEASURE.finditer(fsent))
            fix = None
            if len(fm) == 1:  # one measurement in the matching finding: propose it, same unit as written there
                fix = isent[: m.start()] + fm[0].group(0) + isent[m.end():]
            out.append(Issue("measure_mismatch", "error", fsent, isent,
                             fix_find=isent if fix else None, fix_replace=fix,
                             marks=[{"section": "findings", "text": f.group(0)} for f in fm] + [{"section": "impression", "text": m.group(0)}]))
    return out


def _sides(s: str) -> set[str]:
    return {"R" if w.lower().startswith(("derech", "right")) else "L" for w in SIDE.findall(s)}


def _swap(s: str) -> str:
    def rep(m):
        w = m.group(0)
        new = SWAP[w.lower()]
        return new.capitalize() if w[0].isupper() else new
    return SIDE.sub(rep, s)


def laterality_issues(findings: str, impression: str) -> list[Issue]:
    f_sides = _sides(findings)
    if len(f_sides) != 1:  # bilateral or no side in the findings: nothing provable
        return []
    side = next(iter(f_sides))
    f_sents = [s for s in sentences(findings) if SIDE.search(s)]
    out = []
    for isent in sentences(impression):
        i_sides = _sides(isent)
        if i_sides and side not in i_sides:
            fsent = _closest(isent, f_sents)
            out.append(Issue("laterality_mismatch", "error", fsent, isent, fix_find=isent, fix_replace=_swap(isent),
                             marks=[{"section": "findings", "text": w} for w in SIDE.findall(fsent)]
                             + [{"section": "impression", "text": w} for w in SIDE.findall(isent)]))
    return out


def rule_issues(findings: str, impression: str) -> list[Issue]:
    return measure_issues(findings, impression) + laterality_issues(findings, impression)


QC_PROMPT = {
    "es": """Eres RAD·QC, un revisor de errores MECÁNICOS en borradores de informes de radiología. No opinas sobre el diagnóstico ni sobre las imágenes.
Revisa solo estos tipos:
- measure_mismatch: una medida distinta entre HALLAZGOS e IMPRESIÓN.
- laterality_mismatch: lado (derecho/izquierdo) distinto entre HALLAZGOS e IMPRESIÓN.
- omitted_finding: un hallazgo anormal de HALLAZGOS que no aparece en la IMPRESIÓN.
- normal_template_abnormal: la IMPRESIÓN dice normal/sin hallazgos pero HALLAZGOS describe algo anormal.
- indication_unanswered: la IMPRESIÓN no responde a la pregunta de la INDICACIÓN.
Responde SOLO con JSON: {"issues": [{"type": "...", "body_excerpt": "...", "impression_excerpt": "...", "explanation": "..."}]}
body_excerpt e impression_excerpt deben ser copias EXACTAS (carácter por carácter) de fragmentos del texto; para indication_unanswered, body_excerpt es un fragmento exacto de la INDICACIÓN. Si no hay errores: {"issues": []}. No propongas texto nuevo. explanation: una frase.""",
    "en": """You are RAD·QC, a checker for MECHANICAL errors in draft radiology reports. You do not judge the diagnosis or the images.
Check only these types:
- measure_mismatch: a measurement differs between FINDINGS and IMPRESSION.
- laterality_mismatch: side (right/left) differs between FINDINGS and IMPRESSION.
- omitted_finding: an abnormal finding in FINDINGS that the IMPRESSION leaves out.
- normal_template_abnormal: the IMPRESSION says normal/no findings while FINDINGS describes something abnormal.
- indication_unanswered: the IMPRESSION does not answer the question in the INDICATION.
Answer ONLY with JSON: {"issues": [{"type": "...", "body_excerpt": "...", "impression_excerpt": "...", "explanation": "..."}]}
body_excerpt and impression_excerpt must be EXACT (character for character) copies of fragments of the text; for indication_unanswered, body_excerpt is an exact fragment of the INDICATION. If there are no errors: {"issues": []}. Do not propose new text. explanation: one sentence.""",
}


def qc_messages(lang: str, indication: str, findings: str, impression: str) -> list[dict]:
    doc = f"INDICACIÓN/INDICATION:\n<<<{indication}>>>\n\nHALLAZGOS/FINDINGS:\n<<<{findings}>>>\n\nIMPRESIÓN/IMPRESSION:\n<<<{impression}>>>"
    return [{"role": "system", "content": QC_PROMPT[lang]}, {"role": "user", "content": doc}]


def parse_model_issues(raw: str | None, indication: str, findings: str, impression: str) -> list[Issue]:
    """Keeps only well-formed issues whose quotes are literally in the report (no invented fragments)."""
    if not raw:
        return []
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        data = json.loads(m.group(0)) if m else {}
    except ValueError:
        return []
    out = []
    for it in data.get("issues", []) if isinstance(data, dict) else []:
        if not isinstance(it, dict) or it.get("type") not in TYPES:
            continue
        body, imp = str(it.get("body_excerpt") or "").strip(), str(it.get("impression_excerpt") or "").strip()
        body_src = indication if it["type"] == "indication_unanswered" else findings
        if body and body not in body_src:
            continue
        if imp and imp not in impression:
            continue
        if not body and not imp:
            continue
        out.append(Issue(it["type"], "verify", body, imp,
                         body_label="indication" if it["type"] == "indication_unanswered" else "findings",
                         explanation=str(it.get("explanation") or "")[:240], source="model"))
    return out


def merge(rules: list[Issue], model: list[Issue]) -> list[Issue]:
    """Rule findings are proven; a model issue of a type the rules already caught is dropped, as are duplicates."""
    proven = {i.rule for i in rules}
    seen, out = set(), []
    for i in rules + [m for m in model if m.rule not in proven]:
        if i.key() not in seen:
            seen.add(i.key())
            out.append(i)
    return out
