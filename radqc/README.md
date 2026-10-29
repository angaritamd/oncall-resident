# radqc: RAD·QC v5 datasets (ANG-174)

Synthetic Spanish reports with at most one planted **mechanical** error, used to measure and later train the RAD·QC checker (`core/oncall_core/qc.py`). The pre-existing RAD·QC v3 and v4 pilot are **not** part of this repository.

## Data rules

Sources: Meta Model API Terms of Service §1 and §10.1(ix), Hackathon Credit Terms §3.3. Analysis in ANG-174.

| Split | Generated with | Use |
|---|---|---|
| `bench` (hard benchmark) | Muse Wonder through the Meta Model API | Evaluation only. Every record has `never_train: true`. |
| `train` | Muse Glimmer self-hosted on our Modal (Apache-2.0) | Training of the v5 LoRA |

The code enforces these rules:

- `check_policy` refuses to let the API backend write the `train` split.
- `assert_trainable` refuses any record that is not Glimmer output in the `train` split.

## Taxonomy (`radqc/taxonomy.py`)

Nine subtypes, each mapped to one of the checker's five labels. "Hard" subtypes are the ones the benchmark weights up.

| Subtype | Checker label | Hard |
|---|---|---|
| measure_number | measure_mismatch | |
| measure_unit (1,2 cm → 1,2 mm) | measure_mismatch | ✓ |
| laterality | laterality_mismatch | |
| omission_total | omitted_finding | |
| omission_partial (two findings, the impression keeps one) | omitted_finding | ✓ |
| normal_template (normal template signed on an abnormal study) | normal_template_abnormal | ✓ |
| indication_unanswered | indication_unanswered | ✓ |
| clean | — | |
| clean_tricky (same size in another unit, bilateral finding, minor finding left out) | — | ✓ |

## Validation of each generated case (`radqc/generate.py`)

- The quoted excerpts must appear literally in the report.
- Measurement and laterality errors must be provable by the deterministic rules.
- Any other error type must not trip the rules.
- A clean case must pass the rules clean.

Rejected cases are regenerated once.

## Pilot: hard benchmark (`data/bench/pilot.jsonl`)

20 cases, 4 per hard subtype, generated with `muse-wonder-1.0`. Miguel validates them on `/bench`.

```
python -m radqc.generate --backend meta --model muse-wonder-1.0 --split bench --n 20 --hard-only --out data/bench/pilot.jsonl
```

Tests: `uv run --locked pytest -q`
