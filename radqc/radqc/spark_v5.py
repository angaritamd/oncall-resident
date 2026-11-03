"""Casos sintéticos RAD·QC v5 con Muse Spark Open vía Baseten (ANG-178).

Esquema nuevo, escrito desde cero para ANG-178 (no reutiliza sets viejos):
cada caso trae modalidad (RX tórax | TC tórax), motivo de consulta, marca de
crítico del tecnólogo (sí/no), un informe "correcto" y hasta 3 variantes con
errores inyectados; cada variante lista sus errores {tipo, descripción, campo}.

Tipos de error: lateralidad, medida, omision_manejo (omisión con impacto en el
manejo), pregunta_sin_responder, y el caso especial doble_chequeo (estudio
crítico con motivo, informado con plantilla normal → "verificar", NO es error).

Lo que NO es error (el prompt lo prohíbe como error inyectado): negativos
pertinentes omitidos en la impresión salvo que respondan la pregunta;
subrasgos de un diagnóstico resumido; hallazgos menores sin impacto; una sola
dimensión en vez de tres; paráfrasis; pregunta respondida con limitación.

Todo es sintético: el generador solo envía prompts de generación al endpoint
externo y solo recibe casos sintéticos. Salida solo para evaluación:
cada registro lleva synthetic=true y never_train=true.

Uso (la llave se inyecta solo dentro del comando, nunca se imprime):
  SPARK_OPEN_URL=... SPARK_OPEN_MODEL=... \\
  SPARK_OPEN_API_KEY="$(security find-generic-password -s baseten-hack -w)" \\
  python -m radqc.spark_v5 --n 20 --seed 178 --out gen/v5_piloto.jsonl
"""
import argparse
import asyncio
import json
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from oncall_core.spark_open import (
    SparkOpenConfig,
    achat,
    log_cost,
    parse_json_content,
    token_counts,
)

PROMPT_VERSION = "v5-piloto-1"

MODALIDADES = ("RX tórax", "TC tórax")

TIPOS = ("lateralidad", "medida", "omision_manejo", "pregunta_sin_responder", "doble_chequeo")
CAMPOS = ("indicacion", "hallazgos", "impresion")

# Motivos sintéticos escritos para este piloto (no describen imágenes reales).
MOTIVOS_RX = [
    "Tos seca de 3 semanas sin fiebre.",
    "Dolor torácico derecho tras caída de bicicleta.",
    "Disnea de esfuerzo de 2 meses de evolución.",
    "Fiebre y tos productiva de 4 días.",
    "Control de neumonía tratada hace un mes.",
    "Descartar derrame pleural en paciente con disnea.",
    "Dolor pleurítico izquierdo con tos.",
    "Contacto estrecho con tuberculosis; tamizaje.",
]
MOTIVOS_TC = [
    "Nódulo pulmonar visto en RX; caracterizar.",
    "Pérdida de peso y tos persistente de 2 meses.",
    "Descartar tromboembolismo pulmonar.",
    "Masa hiliar en RX; evaluar extensión.",
    "Hemoptisis leve recurrente.",
    "Control de nódulo sólido de 8 mm.",
    "Derrame pleural loculado; evaluar.",
    "Adenopatías mediastinales en RX previa.",
]
MOTIVOS_CRITICOS = [
    "Disnea súbita y dolor torácico derecho.",
    "Hemoptisis franca en curso.",
    "Fiebre alta con hipotensión y tos; descartar neumonía complicada.",
    "Dolor torácico opresivo con desaturación.",
]

TIPO_ES = {
    "lateralidad": "cambia el lado (derecho/izquierdo) de un hallazgo entre HALLAZGOS e IMPRESIÓN",
    "medida": "repite una medida de HALLAZGOS en la IMPRESIÓN con otro número o unidad sin convertir",
    "omision_manejo": "omite en la IMPRESIÓN un hallazgo anormal de HALLAZGOS que cambiaría el manejo",
    "pregunta_sin_responder": "la INDICACIÓN pregunta algo concreto y la IMPRESIÓN no lo responde ni lo descarta",
    "doble_chequeo": "CASO ESPECIAL, NO es error: estudio crítico con motivo claro, informado con plantilla "
                     "normal; la variante se marca para verificar (doble chequeo), no como error",
}


@dataclass(frozen=True)
class Plan:
    id: str
    modalidad: str
    motivo: str
    tecnologo_critico: bool
    receta: tuple  # tipos de error esperados, uno por variante; () = control sin error


def plan(n: int, *, seed: int, prefix: str = "V5") -> list[Plan]:
    """Reparto determinista: ~30 % controles sin error; el resto cubre los 5 tipos."""
    rng = random.Random(seed)
    recetas = (["limpio"] * 6 + ["lateralidad"] * 4 + ["medida"] * 3
               + ["omision_manejo"] * 3 + ["pregunta_sin_responder"] * 2 + ["doble_chequeo"] * 2)
    while len(recetas) < n:
        recetas += recetas
    recetas = recetas[:n]
    rng.shuffle(recetas)
    # hasta 3 variantes: un caso con 3, dos casos con 2 (el resto con 1)
    extras = {"medida": ["lateralidad", "omision_manejo"], "lateralidad": ["medida"]}
    out = []
    multi = 0
    for i, r in enumerate(recetas):
        if r == "limpio":
            receta: tuple = ()
        elif r in extras and multi < 3:
            multi += 1
            receta = tuple([r] + extras[r][: (2 if multi == 1 else 1)])
        else:
            receta = (r,)
        modalidad = rng.choice(MODALIDADES)
        critico = r == "doble_chequeo" or rng.random() < 0.3
        if r == "doble_chequeo":
            motivo = rng.choice(MOTIVOS_CRITICOS)
        elif critico:
            motivo = rng.choice(MOTIVOS_CRITICOS + (MOTIVOS_RX if modalidad == "RX tórax" else MOTIVOS_TC))
        else:
            motivo = rng.choice(MOTIVOS_RX if modalidad == "RX tórax" else MOTIVOS_TC)
        out.append(Plan(f"{prefix}-{i + 1:04d}", modalidad, motivo, critico, receta))
    return out


def prompt_for(spec: Plan) -> list[dict]:
    if not spec.receta:
        receta_txt = ("CONTROL SIN ERROR: el informe correcto y UNA sola variante que también es "
                      "correcta (variantes: []). El informe debe ser coherente y completo.")
        variantes_txt = "variantes: [] (caso control, sin variantes con error)"
    else:
        lines = []
        for j, t in enumerate(spec.receta, 1):
            lines.append(f"  Variante {j}: tipo {t} → {TIPO_ES[t]}")
        receta_txt = "Variantes con error a construir:\n" + "\n".join(lines)
        variantes_txt = (f"variantes: una por cada tipo pedido ({len(spec.receta)}), cada una con su informe "
                         "completo y su lista errores [{tipo, descripcion, campo}]; campo es la sección "
                         "donde está el error: indicacion | hallazgos | impresion. La variante doble_chequeo "
                         "lleva es_error=false y accion=verificar; las demás es_error=true.")
    critico_txt = "SÍ (estudio crítico avisado por el tecnólogo)" if spec.tecnologo_critico else "no"
    content = f"""Genera UN caso radiológico SINTÉTICO en español (Colombia), ficticio, sin nombres de pacientes ni instituciones.

Estudio: {spec.modalidad}
Motivo de consulta: {spec.motivo}
Marca de crítico del tecnólogo: {critico_txt}

{receta_txt}

Reglas de estilo:
- Estilo de radiólogo colombiano, conciso. Cada informe (el correcto y cada variante) tiene INDICACIÓN (1 frase, basada en el motivo), HALLAZGOS (3 a 6 frases) e IMPRESIÓN (1 a 3 frases).
- Medidas con número y unidad (mm o cm) cuando haya lesiones medibles.
- El informe "correcto" es coherente y completo.

Qué NO es error (no lo inyectes como error; puede aparecer en informes correctos):
negativos pertinentes omitidos en la impresión salvo que respondan la pregunta; subrasgos de un diagnóstico resumido; hallazgos menores sin impacto en el manejo; una sola dimensión en vez de tres; paráfrasis entre hallazgos e impresión; pregunta respondida con limitación explícita.

{variantes_txt}

Responde SOLO con JSON, sin texto fuera:
{{"informe_correcto": {{"indicacion": "...", "hallazgos": "...", "impresion": "..."}},
 "variantes": [{{"informe": {{"indicacion": "...", "hallazgos": "...", "impresion": "..."}},
 "errores": [{{"tipo": "...", "descripcion": "una frase", "campo": "..."}}], "es_error": true}}]}}"""
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


def _sections(d: dict) -> tuple[str, str, str] | None:
    if not isinstance(d, dict):
        return None
    secs = tuple(str(d.get(k) or "").strip() for k in ("indicacion", "hallazgos", "impresion"))
    return secs if all(secs) else None


def validate(spec: Plan, data: dict) -> str | None:
    """Por qué un caso generado se rechaza, o None. Estructural; la clínica la revisa Miguel."""
    if not isinstance(data, dict):
        return "no JSON object"
    if _sections(data.get("informe_correcto")) is None:
        return "informe_correcto incompleto"
    variantes = data.get("variantes")
    if not isinstance(variantes, list) or len(variantes) != len(spec.receta):
        return f"se esperaban {len(spec.receta)} variantes"
    for var, esperado in zip(variantes, spec.receta):
        if not isinstance(var, dict) or _sections(var.get("informe")) is None:
            return "variante sin informe completo"
        errores = var.get("errores")
        if not isinstance(errores, list) or not (1 <= len(errores) <= 3):
            return "variante sin lista de 1-3 errores"
        for e in errores:
            if not isinstance(e, dict) or e.get("tipo") not in TIPOS:
                return f"tipo de error inválido: {(e or {}).get('tipo')!r}"
            if e["tipo"] != esperado and not (len(spec.receta) > 1 and e["tipo"] in TIPOS[:4]):
                return f"tipo {e['tipo']!r} no pedido (se pedía {esperado!r})"
            if not str(e.get("descripcion") or "").strip():
                return "error sin descripción"
            if e.get("campo") not in CAMPOS:
                return f"campo inválido: {e.get('campo')!r}"
        if esperado == "doble_chequeo":
            if var.get("es_error") is not False:
                return "doble_chequeo debe llevar es_error=false (no es error, es verificar)"
        elif var.get("es_error") is False:
            return "solo doble_chequeo puede llevar es_error=false"
    if not spec.receta and variantes:
        return "control con variantes"
    texto = json.dumps(data, ensure_ascii=False)
    if any(p.search(texto) for p in FORBIDDEN):
        return "posible nombre o institución"
    return None


async def one(http, cfg: SparkOpenConfig, spec: Plan, cost_log: str, tries: int = 2):
    attempts = []
    for _ in range(tries):
        t0 = time.monotonic()
        try:
            ans = await achat(prompt_for(spec), config=cfg, temperature=0.8,
                              max_tokens=6000, timeout=180.0, client=http)
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
        why = validate(spec, data) if data is not None else "no JSON"
        attempts.append({"id": spec.id, "ok": why is None, "why": why, "seconds": secs,
                         "tokens_in": tin, "tokens_out": tout, "reasoning_tokens": rtok})
        log_cost(cost_log, f"v5 {spec.id}", ans, seconds=secs)
        if why is None:
            return {
                "id": spec.id, "modalidad": spec.modalidad, "motivo_de_consulta": spec.motivo,
                "tecnologo_critico": spec.tecnologo_critico,
                "informe_correcto": data["informe_correcto"], "variantes": data["variantes"],
                "semilla": SEED_HOLDER[0], "prompt_version": PROMPT_VERSION,
                "synthetic": True, "never_train": True, "split": "bench",
                "provenance": {"backend": "spark-open", "model": ans.model,
                               "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
            }, attempts
    return None, attempts


SEED_HOLDER = [178]


async def run(args) -> dict:
    import httpx

    SEED_HOLDER[0] = args.seed
    cfg = SparkOpenConfig.from_env()
    specs = plan(args.n, seed=args.seed)
    if args.only:  # regenera algunos IDs del mismo plan (misma modalidad, motivo y receta)
        wanted = set(args.only.split(","))
        specs = [s for s in specs if s.id in wanted]
    cost_log = args.cost_log or os.path.join(os.path.dirname(args.out) or ".", "costos.jsonl")
    sem = asyncio.Semaphore(args.concurrency)
    t0 = time.monotonic()
    async with httpx.AsyncClient() as http:
        async def guarded(s):
            async with sem:
                return await one(http, cfg, s, cost_log)
        results = await asyncio.gather(*(guarded(s) for s in specs))
    records = [r for r, _ in results if r]
    attempts = [a for _, att in results for a in att]
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = {
        "backend": "spark-open", "model": os.environ.get("SPARK_OPEN_MODEL", ""),
        "prompt_version": PROMPT_VERSION, "seed": args.seed,
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
