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
