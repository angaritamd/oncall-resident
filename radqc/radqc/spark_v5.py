"""Casos sintéticos RAD·QC v5 para ENTRENAMIENTO con Muse Spark Open vía Baseten (ANG-178).

Esquema taxonomía-v4 (oficial, radqc/taxonomia.py): cada caso es un estudio con un
subtipo oficial (SUBTYPES), un motivo válido para ese estudio (STUDIES: nada de
TEP en rodilla) y el informe reportado con su error
{body_excerpt literal, impression_excerpt literal, explanation}.

- Controles (~30 %): sin variante reportada (error null).
- doble_chequeo: estudio con motivo crítico de STUDIES; la variante es la
  PLANTILLA NORMAL del estudio, literal (sin hallazgos), no una paráfrasis del
  informe correcto. El código lo exige carácter por carácter (normalizado).
- Registros de entrenamiento: split=train, never_train=false,
  generator=spark-open (assert_trainable los acepta).

Todo es sintético: solo prompts de generación al endpoint externo y solo casos
sintéticos de vuelta. Llave solo del Llavero (baseten-hack), nunca impresa;
config 100 % por env (SPARK_OPEN_URL, SPARK_OPEN_MODEL, SPARK_OPEN_API_KEY).

Uso (la llave se inyecta solo dentro del comando, nunca se imprime):
  SPARK_OPEN_URL=... SPARK_OPEN_MODEL=... \\
  SPARK_OPEN_API_KEY="$(security find-generic-password -s baseten-hack -w)" \\
  python -m radqc.spark_v5 --n 20 --seed 178 --out gen/v5_train_piloto.jsonl
"""
import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

from oncall_core.spark_open import (
    SparkOpenConfig,
    achat,
    log_cost,
    parse_json_content,
    token_counts,
)

from .generate import Spec, plan as official_plan
from .taxonomia import (
    CRITICAL_ES,
    PROMPT_VERSION,
    STUDIES,
    STYLE,
    SUBTYPES,
    VERSION as TAXONOMY_VERSION,
    validate,
)

CONTROL = next(s for s in SUBTYPES if s.id == "control")
KNOWN_SUBTYPES = {s.id for s in SUBTYPES}

# Plantilla normal por estudio: hallazgos e impresión de un estudio sin
# alteraciones. La variante de doble_chequeo debe copiarla exactamente.
NORMAL_TEMPLATES = {
    "RX de tórax": {
        "findings": ("Pulmones bien expandidos, sin consolidaciones, atelectasias ni derrame "
                     "pleural. Silueta cardiomediastínica de tamaño y contorno normales. Sin "
                     "neumotórax. Estructuras óseas del tórax sin lesiones agudas."),
        "impression": "Radiografía de tórax sin alteraciones agudas.",
    },
    "RX de abdomen": {
        "findings": ("Distribución normal del gas intestinal, sin niveles hidroaéreos ni "
                     "neumoperitoneo. Siluetas renales y psoas de aspecto usual. Sin litiasis "
                     "radiopaca evidente. Estructuras óseas sin lesiones agudas."),
        "impression": "Radiografía de abdomen sin alteraciones agudas.",
    },
    "RX de rodilla": {
        "findings": ("Sin fracturas ni luxaciones. Espacios articulares conservados. Sin "
                     "derrame articular evidente. Partes blandas sin alteraciones."),
        "impression": "Radiografía de rodilla sin alteraciones agudas.",
    },
    "TC de tórax": {
        "findings": ("Parénquima pulmonar sin nódulos, consolidaciones ni derrame pleural. Sin "
                     "adenopatías mediastinales o hiliares patológicas. Estructuras "
                     "cardiovasculares y óseas sin alteraciones agudas."),
        "impression": "TC de tórax sin alteraciones agudas.",
    },
    "Angio-TC de tórax": {
        "findings": ("Arterias pulmonares principales, lobares y segmentarias opacificadas de "
                     "forma homogénea, sin defectos de llenado. Aorta torácica de calibre y "
                     "contornos normales. Parénquima pulmonar sin consolidaciones. Sin derrame "
                     "pleural."),
        "impression": "Angio-TC de tórax sin tromboembolismo pulmonar ni disección aórtica.",
    },
    "TC de abdomen y pelvis con contraste": {
        "findings": ("Hígado, bazo, páncreas, glándulas suprarrenales y riñones de tamaño y "
                     "realce normales. Sin apendicolito ni engrosamiento apendicular. Vesícula "
                     "biliar sin litiasis. Sin colecciones ni líquido libre."),
        "impression": "TC de abdomen y pelvis sin alteraciones agudas.",
    },
    "TC de cráneo simple": {
        "findings": ("Parénquima cerebral de densidad normal, sin hemorragias, colecciones ni "
                     "efecto de masa. Sistema ventricular y cisternas de tamaño normal. Línea "
                     "media centrada. Sin fracturas."),
        "impression": "TC de cráneo simple sin alteraciones agudas.",
    },
}
assert set(NORMAL_TEMPLATES) == {s.exam for s in STUDIES}, "plantilla normal por cada estudio"


def norm(s: str) -> str:
    return " ".join(str(s or "").split())


def _sections(d: dict) -> tuple[str, str, str] | None:
    if not isinstance(d, dict):
        return None
    secs = tuple(str(d.get(k) or "").strip() for k in ("indication", "findings", "impression"))
    return secs if all(secs) else None


def build_messages(spec: Spec) -> list[dict]:
    sex = "mujer" if spec.sex == "F" else "hombre"
    if spec.subtype.kind == "control":
        variante_txt = 'Si el caso es un control sin error, "variant" es null.'
        extra = ""
    else:
        variante_txt = ('La VARIANT es el informe reportado: igual al correcto salvo por el ÚNICO '
                        'error pedido, que debe verse natural, como un descuido real al dictar.')
        extra = ""
    if spec.subtype.id == "doble_chequeo":
        tpl = NORMAL_TEMPLATES[spec.exam]
        extra = (f'\n- CASO DE DOBLE CHEQUEO: la variante es la plantilla normal del estudio, '
                 f'copiada EXACTAMENTE, sin cambiar ni una palabra (no parafrasees el informe '
                 f'correcto):\n  HALLAZGOS: "{tpl["findings"]}"\n  IMPRESIÓN: "{tpl["impression"]}"\n'
                 f'  La INDICACIÓN de la variante es una frase que contiene el motivo textualmente.')
    content = f"""Escribe UN caso radiológico SINTÉTICO y ficticio (taxonomía-v4):
- Estudio: {spec.exam} ({spec.modality}); paciente {sex}, {spec.age} años.
- Motivo de consulta: {spec.reason} (la INDICACIÓN parte de este motivo; no lo cambies por otro).
- Caso a construir: {spec.subtype.recipe}

Reglas:
- {STYLE}
- Conciso: INDICACIÓN de 1 frase; HALLAZGOS de 3 a 6 frases; IMPRESIÓN de 1 a 3 frases.
- Medidas con número y unidad (mm o cm) cuando haya lesiones medibles.
- El informe "correcto" es coherente y completo.
{variante_txt}
- Pregunta CRÍTICA = patología aguda que cambia la conducta inmediata: {CRITICAL_ES}.
- La obstrucción intestinal solo es crítica con indicación aguda; si es crónica o no consta agudeza, es NO crítica.
- NO son errores (no los cuentes como tales): negativos pertinentes que la IMPRESIÓN no repite (salvo que respondan una pregunta crítica), rasgos resumidos en un diagnóstico, hallazgos menores sin impacto, una sola dimensión en vez de tres, paráfrasis, una IMPRESIÓN que nombra la pregunta aunque sea con limitación («apéndice no visualizado; no se puede descartar apendicitis»), una pregunta NO crítica respondida solo en HALLAZGOS.
- SÍ es error de pregunta: una pregunta CRÍTICA que la IMPRESIÓN no responde explícitamente, aunque HALLAZGOS la responda, la IMPRESIÓN sea genérica («estudio dentro de límites normales») o solo nombre la región o la anatomía («parénquima pulmonar sin consolidaciones» ante «descartar tromboembolismo pulmonar»); o una pregunta NO crítica que ni HALLAZGOS ni IMPRESIÓN responden. Responder es nombrar la patología preguntada.
- En pregunta CRÍTICA, cuando HALLAZGOS sí responde la pregunta pero la IMPRESIÓN no, la "explanation" debe decirlo explícitamente («el cuerpo responde pero la conclusión no»).
- body_excerpt: copia EXACTA (carácter por carácter) del fragmento de HALLAZGOS de la variante que prueba el error, o de la INDICACIÓN si el caso es de pregunta o de doble chequeo. En doble_chequeo cita el motivo crítico PRINCIPAL (el del motivo de consulta, p. ej. «descartar disección aórtica»), no un motivo secundario («sospecha de tromboembolismo pulmonar agudo»).
- impression_excerpt: copia EXACTA del fragmento de la IMPRESIÓN de la variante implicado ("" si lo que pasa es que algo falta).{extra}

Responde SOLO con JSON, sin texto fuera:
{{"correct_report": {{"indication": "...", "findings": "...", "impression": "..."}},
 "variant": {{"report": {{"indication": "...", "findings": "...", "impression": "..."}},
 "error": {{"body_excerpt": "...", "impression_excerpt": "...", "explanation": "una frase"}} }} }}"""
    return [{"role": "user", "content": content}]


# Nombres de pacientes o instituciones (con frontera de palabra: la "correlación
# clínica" legítima no dispara el filtro; "Clínica San ..." sí).
FORBIDDEN_RES = [
    r"\b[hH]ospital(?:es)?\s+[A-ZÁÉÍÓÚÑ]",
    r"\b[Cc]l[ií]nica\s+[A-ZÁÉÍÓÚÑ]",
    r"\b(?:IPS|EPS)\b",
    r"\b[Dd]r[as]?[.:]",
    r"\b[Ff]undaci[oó]n\s+[A-ZÁÉÍÓÚÑ]",
    r"\b(?:[Pp]aciente|[Ss]e[ñn]or|[Ss]e[ñn]ora|[Dd]on|[Dd]o[ñn]a)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+",
]
FORBIDDEN = tuple(re.compile(p) for p in FORBIDDEN_RES)


def validate_case(spec: Spec, data: dict) -> str | None:
    """Por qué un caso generado se rechaza, o None. Delega en taxonomia.validate;
    además exige el informe correcto limpio y, en doble_chequeo, la plantilla
    normal literal."""
    if spec.subtype.id not in KNOWN_SUBTYPES:
        return f"subtipo desconocido: {spec.subtype.id!r}"
    if not isinstance(data, dict):
        return "no JSON object"
    correct = _sections(data.get("correct_report"))
    if correct is None:
        return "correct_report incompleto"
    why_clean = validate(CONTROL, {"indication": correct[0], "findings": correct[1],
                                   "impression": correct[2], "error": None})
    if why_clean is not None:
        return f"correct_report no limpio: {why_clean}"
    variant = data.get("variant")
    if spec.subtype.kind == "control":
        if variant is not None:
            return "control con variante"
        return None
    if not isinstance(variant, dict):
        return "falta la variante"
    rep = _sections(variant.get("report"))
    if rep is None:
        return "variante sin informe completo"
    err = variant.get("error")
    if not isinstance(err, dict):
        return "variante sin error"
    why = validate(spec.subtype, {"indication": rep[0], "findings": rep[1],
                                  "impression": rep[2], "error": err})
    if why is not None:
        return why
    if spec.subtype.id == "doble_chequeo":
        tpl = NORMAL_TEMPLATES[spec.exam]
        if norm(rep[1]) != norm(tpl["findings"]) or norm(rep[2]) != norm(tpl["impression"]):
            return "doble_chequeo no usa la plantilla normal literal"
    texto = json.dumps(data, ensure_ascii=False)
    if any(p.search(texto) for p in FORBIDDEN):
        return "posible nombre o institución"
    return None


def build_record(spec: Spec, data: dict, *, model: str, plan_seed: int) -> dict:
    """Registro de entrenamiento a partir de un caso ya validado."""
    variant = data.get("variant")
    if spec.subtype.kind == "control" or not isinstance(variant, dict):
        report, err = data["correct_report"], None
    else:
        report, err = variant["report"], variant["error"]
    expected = None if err is None else {
        "type": spec.subtype.label,
        "severity": "verify" if spec.subtype.kind == "verify" else "error",
        **{k: str(err.get(k) or "").strip()
           for k in ("body_excerpt", "impression_excerpt", "explanation")},
    }
    return {
        "id": spec.id, "split": "train",
        "subtype": spec.subtype.id, "kind": spec.subtype.kind, "type": spec.subtype.label,
        "hard": spec.subtype.hard,
        "modality": spec.modality, "exam": spec.exam, "reason": spec.reason,
        "sex": spec.sex, "age": spec.age,
        "indication": report["indication"].strip(), "findings": report["findings"].strip(),
        "impression": report["impression"].strip(), "error": err, "expected": expected,
        "correct_report": {k: str(data["correct_report"][k]).strip()
                            for k in ("indication", "findings", "impression")},
        "never_train": False, "synthetic": True, "generator": "spark-open",
        "provenance": {"backend": "spark-open", "model": model,
                       "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "plan_seed": plan_seed, "case_seed": spec.seed,
                       "prompt_version": PROMPT_VERSION, "taxonomy_version": TAXONOMY_VERSION},
    }


async def one(http, cfg: SparkOpenConfig, spec: Spec, cost_log: str, plan_seed: int, tries: int = 2):
    attempts = []
    for _ in range(tries):
        t0 = time.monotonic()
        try:
            ans = await achat(build_messages(spec), config=cfg, temperature=0.8,
                              max_tokens=10000, timeout=180.0, client=http)
        except Exception as e:  # noqa: BLE001 - se registra y se reintenta
            attempts.append({"id": spec.id, "ok": False, "why": f"{type(e).__name__}: {e}",
                             "seconds": round(time.monotonic() - t0, 1)})
            continue
        secs = round(time.monotonic() - t0, 1)
        tin, tout, rtok = token_counts(ans.usage)
        try:
            data = parse_json_content(ans.content)
        except Exception:
            data = None
        why = validate_case(spec, data) if data is not None else "no JSON"
        attempts.append({"id": spec.id, "ok": why is None, "why": why, "seconds": secs,
                         "tokens_in": tin, "tokens_out": tout, "reasoning_tokens": rtok})
        log_cost(cost_log, f"v5-train {spec.id}", ans, seconds=secs)
        if why is None:
            return build_record(spec, data, model=ans.model, plan_seed=plan_seed), attempts
    return None, attempts


async def run(args) -> dict:
    import httpx

    cfg = SparkOpenConfig.from_env()
    specs = official_plan(args.n, hard_only=args.hard_only, seed=args.seed, prefix=args.prefix)
    if args.only:  # regenera algunos IDs del mismo plan (mismo estudio, motivo y semilla)
        wanted = set(args.only.split(","))
        specs = [s for s in specs if s.id in wanted]
    elif len(specs) >= 20 and sum(1 for s in specs if s.subtype.id == "doble_chequeo") < 3:
        raise SystemExit("plan sin suficientes doble_chequeo (se piden al menos 3)")
    cost_log = args.cost_log or os.path.join(os.path.dirname(args.out) or ".", "costos.jsonl")
    sem = asyncio.Semaphore(args.concurrency)
    t0 = time.monotonic()
    async with httpx.AsyncClient() as http:
        async def guarded(s):
            async with sem:
                return await one(http, cfg, s, cost_log, args.seed)
        results = await asyncio.gather(*(guarded(s) for s in specs))
    records = [r for r, _ in results if r]
    attempts = [a for _, att in results for a in att]
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = {
        "backend": "spark-open", "model": os.environ.get("SPARK_OPEN_MODEL", ""),
        "split": "train", "prompt_version": PROMPT_VERSION, "taxonomy_version": TAXONOMY_VERSION,
        "seed": args.seed, "hard_only": args.hard_only,
        "requested": len(specs), "accepted": len(records), "calls": len(attempts),
        "rejected": [a for a in attempts if not a["ok"]],
        "tokens_in": sum(a.get("tokens_in", 0) for a in attempts),
        "tokens_out": sum(a.get("tokens_out", 0) for a in attempts),
        "reasoning_tokens": sum(a.get("reasoning_tokens", 0) for a in attempts),
        "wall_seconds": round(time.monotonic() - t0, 1),
    }
    with open(args.out.replace(".jsonl", ".summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=178)
    ap.add_argument("--prefix", default="T5")
    ap.add_argument("--hard-only", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default=None, help="IDs del plan a (re)generar, separados por coma")
    ap.add_argument("--cost-log", default=None)
    args = ap.parse_args(argv)
    try:
        s = asyncio.run(run(args))
    except Exception as e:  # noqa: BLE001 - la CLI muestra el error y para
        sys.exit(f"spark_v5: {type(e).__name__}: {e}")
    print(json.dumps(s, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
