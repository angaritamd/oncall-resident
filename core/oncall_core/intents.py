"""Rule-based intent matching (day 1: no LLM)."""
import re
import unicodedata

CASE_RE = re.compile(r"\bdemo-?\s?(\d{4})\b", re.I)
# Study Instance UID (used as the id of studies without order metadata)
UID_RE = re.compile(r"\b([0-2](?:\.\d+){2,})\b")


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


REVIEW_RE = re.compile(
    r"\b(revisa (todos los|los) estudios|revision del turno|revisar el turno|review all( studies)?|shift review)\b")


def match(text: str) -> tuple[str, str | None]:
    """Returns (intent, case_id|None). Intents: worklist, why, open, review_all, help."""
    n = _norm(text)
    m = CASE_RE.search(n)
    u = UID_RE.search(n)
    case_id = f"DEMO-{m.group(1)}" if m else u.group(1) if u else None
    if REVIEW_RE.search(n):
        return "review_all", None
    if re.search(r"\b(por ?que|why)\b", n) and re.search(r"(prioridad|primero|priority|first|orden|order)", n):
        return "why", case_id
    if re.search(r"\b(abr(e|ir)|open|ver caso|show case)\b", n) or (case_id and len(n.split()) <= 2):
        return "open", case_id
    if re.search(r"(pendiente|que tengo|lista de trabajo|worklist|pending|to ?do|what do i have)", n):
        return "worklist", None
    return "help", None
