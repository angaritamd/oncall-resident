# ANG-178 — Resumen del dataset v5 de entrenamiento

Generación con Muse Spark Open en Baseten (`meta-models/muse-spark-open-1026`), `hard_only`, taxonomía v4.1 (`gen-v4.1`). Carril cerrado el 2026-11-01.

## Bloques (aceptados → finales)

| Bloque | Seed | Aceptados | Finales |
|---|---|---|---|
| Tanda 1 | 178 | 96 | 95 |
| Tanda 2 | 179 | 98 | 86 |
| 200 | 181 | 90 | 85 |
| 300 | 182 | 88 | 84 |
| 400 | 183 | 88 | 85 |
| 500 | 184 | 88 | 84 |
| 600 | 185 | 92 | 84 |
| 700 | 186 | 99 | 94 |

Total: 739 aceptados → **697 finales**. Llamadas: 873 (<150 por bloque sumando repos). Tokens: 1,05 M entrada / 4,61 M salida / 4,33 M razonamiento.

Distribución final: omisión 164 (110 hueso/tumor, 54 otras), doble chequeo 178, pregunta 133, controles 222.

## Reglas de validación (código)

- `validate_case` (`radqc/radqc/spark_v5.py`): informe correcto limpio; `body_excerpt` e `impression_excerpt` literales; doble_chequeo = plantilla normal literal; medida 3D en RX exige dos proyecciones nombradas; sin nombres ni instituciones; mínimo 3 doble_chequeo por tramo de 20.
- `assert_trainable`: split `train`, `never_train: false`, backend `spark-open`.

## Reglas clínicas (Miguel)

- Omisión = error si está en HALLAZGOS y no en IMPRESIÓN con impacto en el manejo; los tumores cuentan.
- Hallazgos menores sin impacto no son error (regla 3).
- Preguntas no críticas de hueso, tumor, gonartrosis o neoplasia quedan fuera, salvo 6 excepciones de tanda 2 (T2-0005, 0027, 0029, 0063, 0083, 0088).
- RX-3D válida con dos proyecciones ortogonales.
- Bloques 600/700: sin omisiones de hueso ni tumor; variedad de hallazgo y tamaño (sin aneurisma aórtico de 48 mm ni lítica de 32 mm).

## Exclusiones

- Tope de aneurismas de 48 mm, bloque 600 (no consolidados): B6-0065, 0069, 0081, 0089.
- Regla 3, bloque 600: B6-0004, 0027, 0046 (derrames articulares), B6-0016 (Baker).
- Líticas de 30–35 mm en metáfisis (21): T2-0013, 0020, 0025, 0034, 0036, 0041, 0046, 0068, 0074, 0076; B2-0006, 0014; B3-0005, 0017, 0072; B4-0041, 0079; B5-0011, 0033, 0059, 0094. Quedan 6 (B2-0001, 0090, 0063; B3-0009; B5-0009, 0025).
- Pregunta de neumonía ambigua, cuerpo normal sin nombrar consolidación (5): B4-0025, B2-0045, B2-0053, B3-0031, B7-0015.
- Pregunta no crítica de hueso, bloque 700 (2): B7-0010, B7-0016. Se quedan B7-0023, 0043 (fractura no es veto), B7-0006 y B7-0087 (TEP crítico).
- Omisión de derrame articular de rodilla, bloque 700 (2): B7-0047 (38 mm), B7-0067 (24 mm). Pleural moderado y pericárdicos se quedan; B7-0094 se queda (su omitido es el aneurisma poplíteo).
- Nunca consolidados: T1-0064, T2-0004, T2-0015, B2-0031. Corrección de ID: B3-0073 → B3-0071 (opacidad nodular a tumor).
- Nunca aceptado: B7-0062 (8 intentos, medida 3D en RX sin dos proyecciones).
- Se quedan por decisión de Miguel: T1-0021, B6-0082, B6-0059, B6-0088.
