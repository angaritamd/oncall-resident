"""Short reading-flow commands (typed or spoken), matched in code before the model is asked.

They act on the case open on screen and never sign: "firma" gets a refusal that points to the button.
"""
import re

from .intents import _norm

_WORDS_MAX = 6
_PATTERNS = [
    ("sign", re.compile(r"^(firma|firmalo|firmala|firmar|firmalo ya|sign|sign it)\b")),
    ("accept", re.compile(r"^(de acuerdo|ok|okay|vale|conforme|acepto|aceptar|correcto|esta bien|agreed|i agree|accept|looks good)\b")),
    ("review", re.compile(r"^(revisa|revisalo|revisala|revisar|review|check it|run qc)\b")),
    ("next", re.compile(r"^(abre|abrir|open|pasa|pasame|dame)( (el|al|the))? (siguiente|next)\b")),
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
