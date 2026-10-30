"""Clinical questions in a report's INDICATION: which pathology they ask about, whether it is critical, and whether the
IMPRESSION or the FINDINGS answer it (taxonomy-v4, defined by Miguel).

Shared by the checker (qc.py drops a model "indication_unanswered" for a non-critical question the findings answer) and
by the dataset validator in radqc/radqc/taxonomia.py, which re-exports these names, so both apply the same rule.
"""
import re
import unicodedata


def _fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


# Pathologies a clinical question can ask about: (asked about when the question matches, answered only when the
# impression matches). Answers name the PATHOLOGY, never the anatomy: "parénquima pulmonar" does not answer "descartar
# TEP", "sin alteraciones pleuropulmonares" does not answer "descartar derrame pleural". Patterns run on folded text
# (lowercase, no accents). Covers every reason in radqc's STUDIES; anything else falls back to QUESTION_STOP/ANATOMY below.
PATHOLOGIES = [
    ("tep", r"tromboembol|embolia|\btep\b", r"tromboembol|embol|\btep\b|trombo"),
    ("derrame", r"derrame", r"derrame"),
    ("neumonia", r"neumoni", r"neumoni|consolidaci"),
    ("neumotorax", r"neumotorax", r"neumotorax"),
    ("fractura", r"fractur", r"fractur"),
    ("obstruccion", r"obstrucci|oclusi", r"obstrucci|oclusi"),
    ("neumoperitoneo", r"neumoperitoneo|aire libre", r"neumoperitoneo|aire libre"),
    ("apendicitis", r"apendicitis", r"apendicitis"),
    ("colecistitis", r"colecistitis", r"colecistitis"),
    ("neoplasia", r"neoplas|\bmasa|tumor|malign", r"neoplas|\bmasa|tumor|malign|neoforma"),
    ("coleccion", r"coleccion|absceso", r"coleccion|absceso"),
    ("diseccion", r"diseccion", r"diseccion"),
    ("hemorragia", r"hemorrag|sangrad|hematoma", r"hemorrag|sangrad|hematoma"),
    ("lesion", r"\blesion", r"\blesion|fractur|laceraci|hematoma|contusi"),
    ("litiasis", r"litiasis|calculo", r"litiasis|calculo|\blito"),
    ("degenerativo", r"degenerativ|artros", r"degenerativ|artros"),
    ("nodulo", r"nodulo", r"nodulo"),
    ("cateter", r"cateter", r"cateter"),
    ("gas", r"gaseos|\bgas\b", r"gaseos|\bgas\b"),
    ("acv", r"\bacv\b|ictus|cerebrovascular|infarto cerebral|isquemi\w* cerebral",
     r"\bacv\b|ictus|cerebrovascular|infarto|isquemi"),
    ("isquemia_mesenterica", r"isquemia mesenteric", r"isquemi"),
    ("torsion", r"torsion", r"torsion"),
]

# Critical questions (taxonomy-v4, Miguel): an acute pathology that changes immediate management (surgery,
# anticoagulation, thrombolysis, urgent drainage). A critical question must be answered in the IMPRESSION; a
# non-critical one may be answered in the findings alone. Only pathologies the studies in radqc's STUDIES can ask about
# (no testicular torsion, ectopic pregnancy or cord compression: no ultrasound or spine study here). Kept apart from
# Study.critical, which drives doble_chequeo. (name, asked about when the question matches, answered only when the
# impression matches): each critical question has its own answer pattern, never the broad PATHOLOGIES row ("lesion"
# also matches a fracture or a contusion, which do not answer "descartar lesión intracraneal"). Cholecystitis left in
# taxonomy-v4.1 (Miguel, after M6-0006): CT is not the reference test, so a "negative for cholecystitis" in the impression
# gives false reassurance; the findings answering it is enough, and a present cholecystitis the impression leaves out
# is an omission.
CRITICAL_QUESTIONS = [
    ("tep", r"tromboembol|embolia|\btep\b", r"tromboembol|embol|\btep\b|trombo"),
    ("diseccion", r"diseccion", r"diseccion"),
    # intracranial injury after trauma, mild or not, is the hemorrhage question
    ("hemorragia", r"hemorrag|sangrad|hematoma|lesion\w* intracraneal",
     r"hemorrag|sangrad|hematoma|lesion\w* intracraneal"),
    ("neumoperitoneo", r"neumoperitoneo|aire libre", r"neumoperitoneo|aire libre"),
    ("apendicitis", r"apendicitis", r"apendicitis"),
    ("neumotorax", r"neumotorax", r"neumotorax"),
    ("viscera", r"viscera solida", r"viscera|laceraci|hemoperitoneo|lesion\w* (esplenic|hepatic|renal)"),
    ("acv", r"\bacv\b|ictus|cerebrovascular|infarto cerebral|isquemi\w* cerebral",
     r"\bacv\b|ictus|cerebrovascular|infarto|isquemi"),
    ("isquemia_mesenterica", r"isquemia mesenteric", r"isquemi"),
    ("torsion_ovarica", r"torsion (ovaric|anexial|de(l)? ovario)", r"torsion"),
]
# bowel obstruction is critical only in an acute presentation; a chronic one, or one that cannot be told, is not
OBSTRUCTION = r"obstrucci|oclusi"  # also its answer pattern
ACUTE, CHRONIC = r"agud|subit|distensi|vomit|emesis", r"cronic"

# signs the FINDINGS may answer a question with besides naming the pathology (only for non-critical questions)
BODY_SIGNS = {"obstruccion": r"dilataci\w* de (las )?asas|niveles? hidroaere",
              "degenerativo": r"osteofit|pinzamiento|esclerosis subcondral",
              "colecistitis": r"pericolecist|perivesicular|pared\w* (de la )?vesicul|"
                              r"vesicula\w* (biliar )?(de paredes|sin|con)"}

# fallback for a question outside PATHOLOGIES: its words minus the ones that do not name a pathology (question
# verbs, sides, anatomy and regions)
QUESTION_STOP = {"descartar", "sospecha", "evaluar", "valorar", "valoracion", "control", "aguda", "agudo", "agudos",
                 "agudas", "solicita", "presencia", "posible", "signos", "paciente", "conocido", "conocida",
                 "derecho", "derecha", "izquierdo", "izquierda", "bilateral"}
ANATOMY = {"pulmo", "pleur", "torax", "torac", "abdom", "pelvi", "crane", "cereb", "encef", "rodil", "renal", "hepat",
           "cardi", "media", "paren", "estru", "regio", "osea", "oseos", "intra", "visce", "solid", "artic"}


def _fallback_stems(question: str) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-z]{5,}", _fold(question)) if w not in QUESTION_STOP and w[:5] not in ANATOMY}


def asked(question: str) -> list[tuple[str, str]]:
    """(pathology, answer pattern) for each pathology the question asks about."""
    q = _fold(question)
    return [(name, ans) for name, ask, ans in PATHOLOGIES if re.search(ask, q)]


def names_question(question: str) -> bool:
    """Whether a quoted question names something to answer (a pathology, or a non-anatomy word)."""
    return bool(asked(question) or _fallback_stems(question))


def addresses(question: str, impression: str) -> bool:
    """Whether the IMPRESSION answers the question: it names the pathology asked about ("sin signos de apendicitis",
    "apéndice no visualizado; no se puede descartar apendicitis"). Naming only the anatomy or the region ("parénquima
    pulmonar", "sin alteraciones pleuropulmonares", "estudio dentro de límites normales") is not an answer, and the
    findings never count."""
    imp = _fold(impression)
    found = asked(question)
    if found:
        return any(re.search(ans, imp) for _, ans in found)
    return bool(_fallback_stems(question) & {w[:5] for w in re.findall(r"[a-z]{5,}", imp)})


def is_critical(question: str, indication: str = "") -> bool:
    """Whether the question asks about a critical pathology; `indication` gives the context for obstruction."""
    q, ctx = _fold(question), _fold(indication or question)
    return bool(_critical_answers(question, indication))


def _critical_answers(question: str, indication: str = "") -> list[str]:
    """The answer patterns of the critical pathologies the question asks about (empty: not a critical question)."""
    q, ctx = _fold(question), _fold(indication or question)
    out = [ans for _, ask, ans in CRITICAL_QUESTIONS if re.search(ask, q)]
    if re.search(OBSTRUCTION, q) and re.search(ACUTE, ctx) and not re.search(CHRONIC, ctx):
        out.append(OBSTRUCTION)
    return out


def answers_in_impression(question: str, indication: str, impression: str) -> bool:
    """addresses(), with a critical question answered only by its own CRITICAL_QUESTIONS pattern."""
    crit = _critical_answers(question, indication)
    if crit:
        return any(re.search(ans, _fold(impression)) for ans in crit)
    return addresses(question, impression)


def critical_unanswered(indication: str, impression: str) -> bool:
    """Whether the indication asks a critical question the impression does not answer."""
    return any(is_critical(q, indication) and not answers_in_impression(q, indication, impression)
               for q in _questions(indication))


def answered_in_findings(question: str, findings: str) -> bool:
    """Whether the FINDINGS answer the question: they name the pathology asked about, or one of its BODY_SIGNS."""
    fin = _fold(findings)
    return addresses(question, findings) or any(
        name in BODY_SIGNS and re.search(BODY_SIGNS[name], fin) for name, _ in asked(question))


def _questions(indication: str) -> list[str]:
    """The pathologies an indication asks about, each as the clause that names it ("lesion intracraneal", not
    "lesion": the rest of the clause can make it critical)."""
    ind = _fold(indication)
    return [re.split(r"[;,.]", ind[m.start():])[0] for _, ask, _ in PATHOLOGIES if (m := re.search(ask, ind))]


def non_critical_answered(question: str, indication: str, findings: str, impression: str) -> bool:
    """For the checker: whether a quoted question is a non-critical one already answered, so a model "unanswered"
    warning about it can be dropped. Fails closed (keeps the warning) unless the quote names known pathologies
    (PATHOLOGIES, never the word fallback), none of them critical, every one answered in the findings or the
    impression, and no critical question of the whole indication is left unanswered in the impression."""
    found = asked(question)
    if not found or is_critical(question, indication) or critical_unanswered(indication, impression):
        return False
    fin, imp = _fold(findings), _fold(impression)
    return all(re.search(ans, imp) or re.search(ans, fin) or (name in BODY_SIGNS and re.search(BODY_SIGNS[name], fin))
               for name, ans in found)
