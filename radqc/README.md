# radqc: RAD·QC v5 datasets (ANG-174)

Synthetic Spanish reports with at most one planted **mechanical** error, used to measure and later train the RAD·QC checker (`core/oncall_core/qc.py`). The pre-existing RAD·QC v3 and v4 pilot are **not** part of this repository.

## Data rules

Sources: Meta Model API Terms of Service §1 and §10.1(ix), Hackathon Credit Terms §3.3. Analysis in ANG-174.

| Split | Generated with | Use |
|---|---|---|
| `bench` (hard benchmark) | Muse Wonder through the Meta Model API | Evaluation only. Every record has `never_train: true`. |
| `train` | Spark Open on Baseten (ANG-178, `radqc/spark_v5.py`) | Training of the v5 LoRA |

Glimmer no longer generates cases. Its 30-case pilot (Oct 29) is kept only as a reference, outside the repo, and never trained on.

The code enforces these rules:

- `check_policy` refuses to let the API backend write the `train` split.
- `assert_trainable` refuses any record that is not in the `train` split or does not come from an open-weight model we serve ourselves (`glimmer`, `spark-open`).

## Taxonomy and validator (`radqc/taxonomia.py`, taxonomy-v3)

This is the official module for every generator: `from radqc.taxonomia import SUBTYPES, STUDIES, validate`. The taxonomy was defined by Miguel.

| Kind | Subtypes | What the checker must say |
|---|---|---|
| Error | lateralidad, medida, omisión con impacto en el manejo, pregunta sin responder | The `qc.py` label (laterality / measure / omitted_finding / indication_unanswered) |
| Verify | doble_chequeo: a critical study with a stated reason, reported with the normal template | "Verificar". It is not an error. |
| Control (~30 %) | control, plus traps: pertinent negatives, a summarized diagnosis, a minor finding, one dimension instead of three, a paraphrase, a question answered with a limitation | Nothing (false-alarm check) |

- **Pregunta sin responder (v3):** the error is that the IMPRESSION does not answer the question explicitly.
  - It is still an error if the findings answer it, or if the impression is generic («estudio dentro de límites normales»).
  - An impression that names the question answers it, even with a limitation («apéndice no visualizado; no se puede descartar apendicitis»).
  - `addresses()` checks this on the impression only. Reference case: B5-0019.
  - An answer must name the PATHOLOGY asked about (`PATHOLOGIES`: TEP/tromboembolismo/embolia/trombo, derrame, apendicitis…). Naming only the anatomy or region («parénquima pulmonar», «sin alteraciones pleuropulmonares») does not count. Reference cases: T5-0007 and T5-0017 from the ANG-178 pilot. Prompt gen-v3.1.
- **Reasons for consultation:** `STUDIES` lists the valid ones per study, plus the critical ones for doble_chequeo. A knee X-ray never gets "sospecha de TEP".
- **Report style:** Spanish, as a Colombian radiologist writes, with no names of patients, physicians or institutions.
- **Provenance:** every case stores `plan_seed`, `case_seed`, `prompt_version` and `taxonomy_version`.

`validate(subtype, case)` checks each case:

- Quotes must be literal (from INDICACIÓN for pregunta and doble_chequeo).
- Measurement and laterality errors must be provable by the `qc.py` rules.
- Any other case must not trip those rules.
- Controls carry no error.

`qc.py` counts a size with several dimensions as its largest one (clinical rule 4).

## Pilot: hard benchmark (`data/bench/pilot.jsonl`)

20 cases, 4 per hard subtype of the earlier taxonomy (v1), generated with `muse-wonder-1.0`. Miguel validates them on `/bench`. The next benchmark (v2: 60 cases, `--mix bench-v2`, studies spread evenly, `--max-usd 5`) is generated with taxonomy-v3.

```
python -m radqc.generate --backend meta --model muse-wonder-1.0 --split bench --n 20 --hard-only --out data/bench/pilot.jsonl
```

Tests: `uv run --locked pytest -q`
