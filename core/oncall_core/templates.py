"""Report proposals from templates, chosen in code from the exam and the reason for the order.

The resident does not read images, so a proposal is a structured template for the radiologist to verify, never
a statement of fact: every proposal is shown as "Propuesta · verificar" and cannot be signed until the radiologist
accepts it ("de acuerdo"). When the technologist flagged the study critical, the part that answers that flag is
left as a blank to dictate ("[Dictar: …]") instead of proposing a normal finding against it.
"""
import re
import unicodedata

BLANK = re.compile(r"\[(?:Dictar|Dictate):[^\]]*\]")

_TEMPLATES = {
    ("CR", "es"): {
        "findings": ["Campos pulmonares sin consolidaciones ni masas.", "Sin derrame pleural ni neumotórax.",
                     "Silueta cardiomediastínica de tamaño normal.", "Estructuras óseas sin alteraciones agudas."],
        "impression": "Sin hallazgos agudos en el tórax.",
        "critical": {1: "[Dictar: pleura y neumotórax — {note}]"},
    },
    ("CR", "en"): {
        "findings": ["Lungs without consolidation or masses.", "No pleural effusion or pneumothorax.",
                     "Normal cardiomediastinal silhouette.", "No acute osseous abnormality."],
        "impression": "No acute chest findings.",
        "critical": {1: "[Dictate: pleura and pneumothorax — {note}]"},
    },
    ("CT", "es"): {
        "findings": ["Parénquima pulmonar sin consolidaciones ni nódulos.", "Vía aérea central permeable.",
                     "Sin derrame pleural ni pericárdico.", "Sin adenopatías mediastínicas ni hiliares.",
                     "Estructuras óseas sin lesiones agudas."],
        "impression": "Sin hallazgos agudos en la TC de tórax.",
        "critical": {0: "[Dictar: parénquima — {note}]"},
    },
    ("CT", "en"): {
        "findings": ["Lung parenchyma without consolidation or nodules.", "Patent central airways.",
                     "No pleural or pericardial effusion.", "No mediastinal or hilar lymphadenopathy.",
                     "No acute osseous lesion."],
        "impression": "No acute findings on chest CT.",
        "critical": {0: "[Dictate: parenchyma — {note}]"},
    },
}


def _norm(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", (text or "").lower()) if not unicodedata.combining(c))


def kind_of(modalities: tuple | list, exam: str | None) -> str:
    e = _norm(exam or "")
    if "CT" in modalities or e.startswith(("tc", "ct")):
        return "CT"
    return "CR"


def propose(modalities, exam: str | None, critical: bool, tech_note: str | None, lang: str) -> dict:
    """Returns technique, findings and impression of a template proposal, plus the template id."""
    k = kind_of(modalities, exam)
    tpl = _TEMPLATES[(k, "en" if lang == "en" else "es")]
    findings = list(tpl["findings"])
    impression = tpl["impression"]
    if critical:
        note = (tech_note or "").strip().rstrip(".")[:120] or ("critical flag" if lang == "en" else "marca crítica")
        for i, blank in tpl["critical"].items():
            findings[i] = blank.format(note=note)
        impression = "[Dictate: impression]" if lang == "en" else "[Dictar: impresión]"
    technique = (exam or k).rstrip(".") + "."
    return {"template": f"{k.lower()}-{'critical' if critical else 'normal'}", "technique": technique,
            "findings": " ".join(findings), "impression": impression}


def blanks(*texts: str) -> list[str]:
    return [m.group(0) for t in texts for m in BLANK.finditer(t or "")]
