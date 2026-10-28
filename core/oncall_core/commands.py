"""Short reading-flow commands (typed or spoken), matched in code before the model is asked.

They act on the case open on screen and never sign: "firma" gets a refusal that points to the button.
"""
import re

from .intents import _norm

_WORDS_MAX = 6
# state-changing commands match the whole utterance: "de acuerdo pero cambia…" carries more content and goes to
# the model; only the sign refusal matches a prefix (anything starting with "firma" is refused, never acted on)
_PATTERNS = [
    ("sign", re.compile(r"^(firma|firmalo|firmala|firmar|sign)\b")),
    ("accept", re.compile(r"^(de acuerdo|ok|okay|vale|conforme|acepto|correcto|esta bien|agreed|i agree|accept|looks good)$")),
    ("review", re.compile(r"^(revisa|revisalo|revisala|review|check it|run qc)$")),
    ("next", re.compile(r"^(abre|abrir|open|pasa|pasame|dame)( (el|al|the))? (siguiente|next)( (caso|estudio|case|study))?$")),
]


def match(text: str) -> str | None:
    n = re.sub(r"[¿?¡!.,;:]", " ", _norm(text)).strip()
    n = re.sub(r"\s+", " ", n)
    if not n or len(n.split()) > _WORDS_MAX:
        return None
    for name, rx in _PATTERNS:
        if rx.search(n):
            return name
    return None


_EDIT = re.compile(r"\b(cambia|cambiar|corrige|corregir|pon|poner|agrega|agregar|anade|quita|quitar|elimina|borra|reemplaza|"
                   r"edita|modifica|mide|miden|change|fix|replace|remove|add|measures?)\b|\d+([.,]\d+)?\s*(mm|cm|milimetros?|centimetros?)\b")
_CLAIM = re.compile(r"\b(hecho|listo|aplique|aplicado|actualice|actualizado|cambie|cambiado|corregi|corregido|modifique|"
                    r"edite|anote|done|updated|changed|applied|fixed)\b")


def looks_like_edit(text: str) -> bool:
    """The radiologist asked to change the report (dictated a value or used an editing verb)."""
    return bool(_EDIT.search(_norm(text or "")))


def claims_change(text: str) -> bool:
    """The model's text says something was changed."""
    return bool(_CLAIM.search(_norm(text or "")))


# "Hallazgos: … Impresión: …" — the radiologist's own words go into the draft verbatim
_DICTATION = re.compile(r"^\s*(?:hallazgos|findings)\s*:\s*(?P<f>.+?)(?:\s*(?:impresi[oó]n|impression)\s*:\s*(?P<i>.*))?\s*$",
                        re.I | re.S)


def dictation(text: str) -> tuple[str, str | None] | None:
    """(findings, impression or None) when the text is a structured dictation."""
    m = _DICTATION.match(text or "")
    if not m or not m.group("f").strip():
        return None
    imp = (m.group("i") or "").strip()
    return m.group("f").strip(), imp or None


# ---- measurements dictated in words: "el nódulo mide 12 mm", "la masa mide doce milímetros" --------------------
_UNITS = {"mm": "mm", "milimetro": "mm", "milimetros": "mm", "cm": "cm", "centimetro": "cm", "centimetros": "cm"}
_ONES = {"cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8,
         "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16,
         "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiuno": 21, "veintidos": 22,
         "veintitres": 23, "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26, "veintisiete": 27, "veintiocho": 28,
         "veintinueve": 29}
_TENS = {"treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90}
_MEASURE = re.compile(r"^(?:el|la|los|las)?\s*(?P<what>[a-z]+(?: [a-z]+){0,3}?)\s+(?:mide|miden|mide de|tiene)\s+(?P<num>.+?)\s+"
                      r"(?P<unit>mm|cm|milimetros?|centimetros?)$")


def _number(words: str) -> str | None:
    """'12' · '1,5' · 'doce' · 'treinta y dos' · 'uno coma cinco' → digits (decimal comma kept as in Spanish)."""
    w = words.strip()
    if re.fullmatch(r"\d+(?:[.,]\d+)?", w):
        return w.replace(".", ",")
    if " coma " in w:
        a, b = w.split(" coma ", 1)
        ia, ib = _number(a), _number(b)
        return f"{ia},{ib}" if ia and ib and "," not in ia + ib else None
    if w in _ONES:
        return str(_ONES[w])
    m = re.fullmatch(r"([a-z]+)(?: y ([a-z]+))?", w)
    if m and m.group(1) in _TENS and (m.group(2) is None or (m.group(2) in _ONES and _ONES[m.group(2)] < 10)):
        return str(_TENS[m.group(1)] + (_ONES[m.group(2)] if m.group(2) else 0))
    return None


def measurement(text: str) -> tuple[str, str, str] | None:
    """(structure, value, unit) for a short dictation of one measurement, else None."""
    n = re.sub(r"[¿?¡!;:]", " ", _norm(text or "")).strip().rstrip(".")
    n = re.sub(r"\s+", " ", n)
    m = _MEASURE.match(n)
    if not m:
        return None
    value = _number(m.group("num"))
    if not value:
        return None
    return m.group("what"), value, _UNITS[m.group("unit")]


_NUM_UNIT = re.compile(r"(\d+(?:[.,]\d+)?)\s*(mm|cm)\b")


def measurement_edit(findings: str, structure: str, value: str, unit: str) -> tuple[str, str] | None:
    """(find, replace) when exactly one sentence of the findings names the structure and carries exactly one
    measurement; anything else (none, several, other structures) is ambiguous → the model decides."""
    stem = _norm(structure).split()[-1]
    stem = stem[:-2] if stem.endswith("es") and len(stem) > 5 else stem[:-1] if stem.endswith("s") else stem
    sentences = [s for s in re.split(r"(?<=[.;])\s+", findings) if s.strip()]
    hits = [s for s in sentences if re.search(rf"\b{re.escape(stem)}", _norm(s)) and len(_NUM_UNIT.findall(s)) == 1]
    named = [s for s in sentences if re.search(rf"\b{re.escape(stem)}", _norm(s))]
    if len(hits) != 1 or len(named) != 1 or findings.count(hits[0]) != 1:
        return None
    old = hits[0]
    # an unchanged sentence (the draft already says it) comes back as (old, old): the caller says so
    return old, _NUM_UNIT.sub(f"{value} {unit}", old, count=1)
