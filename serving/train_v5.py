"""RAD·QC v5 LoRA for oncall-resident's Glimmer (ANG-174/178): train on Spark Open cases, then score on bench-v2.

Ported from RadMesh's train_v4.py (QLoRA with Unsloth on the bnb-4bit build, L40S). Only the training data and the
measurement change: the examples are the checker's own prompt and answer (radqc/to_chat.py, hard_only), and the
adapter is measured with this repo's served model (FP8 on H100, as in glimmer_app.py) on bench-v2 with the checker
(radqc/baseline.py: 3 passes, whole system and Glimmer alone).

  cd radqc && PYTHONPATH=.:../core python -m radqc.to_chat --inp <Muse's final train JSONL> --out gen/train_chat
  modal run --detach serving/train_v5.py --smoke     # 16 steps, 4 cases per pass: checks the chain (~US$ 0.50)
  modal run --detach serving/train_v5.py --smoke --no-measure   # the training chain only, no H100
  modal run serving/train_v5.py::lora_check          # the saved adapter on the served FP8 model: load + one case
  modal run --detach serving/train_v5.py             # 2 epochs, r=16, lr 2e-4, then measure
  modal volume get oncall-resident-radqc-lora resultados/v5/ ./lora-v5/

Does not touch the oncall-resident-glimmer deployment. Caps: one GPU at a time and a timeout per step (train 2 h on an
L40S, measure 1 h on an H100), so the run cannot pass ~US$ 8 even if everything times out.
"""
import hashlib
import json
import math
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import glimmer_app as ga  # noqa: E402

ROOT = HERE.parent
TRAIN_DIR = Path(os.environ.get("RADQC_TRAIN_DIR", ROOT / "radqc" / "gen"))
BENCH = ROOT / "radqc" / "data" / "bench" / "bench-v2.jsonl"
APP = "oncall-resident-radqc-v5"
BNB4 = "unsloth/Muse-Glimmer-30B-unsloth-bnb-4bit"          # same base and revision as RadMesh v4
BNB4_REVISION = "ecedda395d4d099b477d135a9a573eedaa5a7aad"
LORA_NAME = "radqc-v5"
LORA_MOUNT = "/lora"
ADAPTER = f"{LORA_MOUNT}/{LORA_NAME}"
RESULTS = Path(LORA_MOUNT) / "resultados" / "v5"
MAX_LEN, EVAL_STEPS, RANK = 2048, 15, 16
# vLLM 0.28 wraps the vision tower's linears for LoRA too and its startup profiling runs a dummy video through them
# (lora_shrink assertion, 30 Oct): text only with no image or video, eager (CUDA graphs on did not start in 3 min)
TEXT_ONLY = ["--limit-mm-per-prompt", '{"image": 0, "video": 0}', "--enforce-eager"]
MINUTES = 60
L40S_USD_S, H100_USD_S = 0.000542, 3.95 / 3600

app = modal.App(APP)
lora_volume = modal.Volume.from_name("oncall-resident-radqc-lora", create_if_missing=True)
hf_cache = modal.Volume.from_name("oncall-resident-radqc-hf", create_if_missing=True)

DATA = {"/root/data/train.jsonl": TRAIN_DIR / "train_chat.train.jsonl", "/root/data/val.jsonl": TRAIN_DIR / "train_chat.val.jsonl"}
MANIFEST = TRAIN_DIR / "train_chat.summary.json"  # written by radqc/to_chat.py with the sha256 of both files
TRAINABLE_BACKENDS = {"glimmer", "spark-open"}     # as radqc.generate: self-served open weights, never the Meta API


def assert_trainable(rows: list[dict]) -> None:
    """The data rule again, on the examples themselves: train split, never_train false, an open-weight backend."""
    bad = [r.get("id") for r in rows if r.get("split") != "train" or r.get("never_train") is not False
           or r.get("backend") not in TRAINABLE_BACKENDS]
    if bad:
        raise ValueError(f"{len(bad)} examples are not trainable: {bad[:5]}")


def check_manifest() -> None:
    """The files to upload are exactly the ones radqc.to_chat wrote (no hand-edited or other-origin files)."""
    if not MANIFEST.is_file():
        sys.exit(f"missing {MANIFEST}: run radqc.to_chat first")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    # a to_chat older than cc7ff0a silently dropped every doble_chequeo case (the checker did not know the type)
    types = manifest.get("checker_types")
    if not isinstance(types, list) or "doble_chequeo" not in types:
        sys.exit(f"{MANIFEST.name} was written by a radqc.to_chat without doble_chequeo (before cc7ff0a): run it again")
    if not (manifest.get("by_subtype") or {}).get("doble_chequeo"):  # v5 trains on them: the set must carry some
        sys.exit(f"{MANIFEST.name} has no doble_chequeo example: check the to_chat input")
    want = manifest.get("sha256") or {}
    for local in DATA.values():
        if not local.is_file() or want.get(local.name) != _sha(local):
            sys.exit(f"{local} does not match {MANIFEST.name}: run radqc.to_chat again")
train_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("unsloth==2026.10.8", "hf_transfer")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "TOKENIZERS_PARALLELISM": "false"})
    .add_local_python_source("glimmer_app", "proxy")  # this file imports glimmer_app in every container
)
eval_image = (ga.image.add_local_python_source("glimmer_app")
              .add_local_dir(ROOT / "core" / "oncall_core", "/root/oncall_core")
              .add_local_dir(ROOT / "radqc" / "radqc", "/root/radqc"))
if modal.is_local():  # files go up from the Mac; inside the container they are already in the image
    for remote, local in DATA.items():
        train_image = train_image.add_local_file(local, remote)
    eval_image = eval_image.add_local_file(BENCH, "/root/bench-v2.jsonl")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha_of(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def _save(name: str, data: dict, smoke: bool = False) -> None:
    d = RESULTS / "smoke" if smoke else RESULTS
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    lora_volume.commit()


def encode(tok, messages: list[dict], max_len: int = MAX_LEN) -> dict:
    """input_ids and labels: the prompt (system + user + assistant header) is -100; only the answer is learned."""
    prompt = tok.apply_chat_template(messages[:-1], tokenize=False, add_generation_prompt=True, reasoning_strength="none")
    full = tok.apply_chat_template(messages, tokenize=False, reasoning_strength="none")
    if not full.startswith(prompt):
        raise ValueError("the chat template does not keep the prompt as a prefix of the whole conversation")
    p = tok(prompt, add_special_tokens=False)["input_ids"]
    c = tok(full[len(prompt):], add_special_tokens=False)["input_ids"]
    if len(p) + len(c) > max_len:
        raise ValueError(f"example of {len(p) + len(c)} tokens (> {max_len})")
    return {"input_ids": p + c, "labels": [-100] * len(p) + c}


@app.function(image=train_image, gpu="L40S", secrets=[modal.Secret.from_name("huggingface")],
              volumes={"/hf": hf_cache, LORA_MOUNT: lora_volume}, timeout=120 * MINUTES, max_containers=1,
              single_use_containers=True)
def train(epochs: float = 2, rank: int = RANK, lr: float = 2e-4, smoke: bool = False) -> dict:
    """`smoke`: 16 steps (one evaluation and one checkpoint) to test the chain before the full run."""
    import importlib.metadata as md
    import traceback

    out: dict = {"base": BNB4, "revision": BNB4_REVISION, "epochs": epochs, "r": rank, "lora_alpha": rank, "lr": lr,
                 "data": {Path(r).name: _sha(Path(r)) for r in DATA},
                 "versions": {p: md.version(p) for p in ("unsloth", "transformers", "peft", "torch", "bitsandbytes")}}
    t0 = time.monotonic()
    stage = "load"
    try:
        # isort: off
        from unsloth import FastModel  # before transformers, so Unsloth patches it
        import torch
        from datasets import Dataset
        from transformers import Trainer, TrainingArguments
        # isort: on

        model, tok = FastModel.from_pretrained(BNB4, revision=BNB4_REVISION, max_seq_length=MAX_LEN, load_in_4bit=True,
                                               full_finetuning=False, cache_dir="/hf")
        out["load_s"] = round(time.monotonic() - t0, 1)
        model = FastModel.get_peft_model(model, finetune_vision_layers=False, finetune_language_layers=True,
                                         finetune_attention_modules=True, finetune_mlp_modules=True, r=rank,
                                         lora_alpha=rank, lora_dropout=0, bias="none", random_state=3407)
        tok = getattr(tok, "tokenizer", tok)
        stage = "data"
        rows = {k: [json.loads(x) for x in Path(f"/root/data/{k}.jsonl").read_text(encoding="utf-8").splitlines() if x]
                for k in ("train", "val")}
        assert_trainable(rows["train"] + rows["val"])
        enc = {k: [encode(tok, r["messages"]) for r in v] for k, v in rows.items()}
        lens = [len(e["input_ids"]) for e in enc["train"]]
        out["examples"] = {k: len(v) for k, v in enc.items()}
        out["tokens"] = {"max": max(lens), "mean": round(sum(lens) / len(lens)),
                         "answer_mean": round(sum(sum(t != -100 for t in e["labels"]) for e in enc["train"]) / len(lens), 1)}
        out["answer_example_0"] = tok.decode([t for t in enc["train"][0]["labels"] if t != -100])  # mask check
        pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id

        def collate(batch: list[dict]) -> dict:
            n = max(len(b["input_ids"]) for b in batch)
            ids = [b["input_ids"] + [pad] * (n - len(b["input_ids"])) for b in batch]
            lab = [b["labels"] + [-100] * (n - len(b["labels"])) for b in batch]
            att = [[1] * len(b["input_ids"]) + [0] * (n - len(b["input_ids"])) for b in batch]
            return {"input_ids": torch.tensor(ids), "labels": torch.tensor(lab), "attention_mask": torch.tensor(att)}

        stage = "train"
        t1 = time.monotonic()
        steps = EVAL_STEPS + 1 if smoke else math.ceil(len(enc["train"]) / 8) * epochs  # 8 = batch 2 x accumulation 4
        args = TrainingArguments(
            output_dir="/tmp/out", per_device_train_batch_size=2, gradient_accumulation_steps=4,
            per_device_eval_batch_size=4, num_train_epochs=epochs, learning_rate=lr, lr_scheduler_type="linear",
            warmup_steps=max(1, round(0.05 * steps)), optim="adamw_8bit", weight_decay=0.0, logging_steps=5,
            eval_strategy="steps", eval_steps=EVAL_STEPS, save_strategy="steps", save_steps=EVAL_STEPS, save_total_limit=2,
            load_best_model_at_end=True, metric_for_best_model="eval_loss", greater_is_better=False, seed=3407,
            report_to="none", remove_unused_columns=False, bf16=torch.cuda.is_bf16_supported(),
            max_steps=EVAL_STEPS + 1 if smoke else -1)
        trainer = Trainer(model=model, args=args, train_dataset=Dataset.from_list(enc["train"]),
                          eval_dataset=Dataset.from_list(enc["val"]), data_collator=collate)
        trainer.train()
        out["train_s"] = round(time.monotonic() - t1, 1)
        hist = trainer.state.log_history
        out["val_loss"] = [{"step": h["step"], "eval_loss": round(h["eval_loss"], 4)} for h in hist if "eval_loss" in h]
        out["train_loss"] = [{"step": h["step"], "loss": round(h["loss"], 4)} for h in hist if "loss" in h]
        out["best"] = {"checkpoint": Path(trainer.state.best_model_checkpoint or "").name,
                       "eval_loss": round(trainer.state.best_metric, 4) if trainer.state.best_metric else None}
        out["gpu_gb_peak"] = round(torch.cuda.max_memory_allocated() / 1e9, 1)
        stage = "save"
        model.save_pretrained(ADAPTER)  # the best checkpoint (load_best_model_at_end)
        tok.save_pretrained(ADAPTER)
        cfg = json.loads((Path(ADAPTER) / "adapter_config.json").read_text())
        out["adapter"] = {"path": ADAPTER, "r": cfg.get("r"),
                          "sha256": {f.name: _sha(f) for f in sorted(Path(ADAPTER).glob("adapter_*"))}}
        out["ok"] = True
    except Exception as e:  # noqa: BLE001 - the result is the error
        out |= {"ok": False, "stage": stage, "error": f"{type(e).__name__}: {str(e)[:600]}",
                "trace": traceback.format_exc()[-1500:]}
    out["total_s"] = round(time.monotonic() - t0, 1)
    out["gpu_usd"] = round(out["total_s"] * L40S_USD_S, 2)
    _save("train.json", out, smoke)
    return out


def _start_vllm() -> tuple[subprocess.Popen, float]:
    """The served model (as glimmer_app.serve) plus the adapter, only on 127.0.0.1 inside this container."""
    t0 = time.monotonic()
    p = subprocess.Popen([
        "vllm", "serve", ga.MODEL_ID, "--revision", ga.MODEL_REVISION, "--host", "127.0.0.1",
        "--port", str(ga.VLLM_PORT), "--served-model-name", ga.SERVED_NAME, "--max-model-len", str(ga.MAX_MODEL_LEN),
        "--gpu-memory-utilization", "0.90", "--reasoning-parser", "muse_glimmer", "--generation-config", "auto",
        "--enable-lora", "--max-lora-rank", str(RANK), "--lora-modules", f"{LORA_NAME}={ADAPTER}", *TEXT_ONLY,
    ])
    ga._wait_ready(p, ga.VLLM_PORT, 25 * MINUTES)
    return p, round(time.monotonic() - t0, 1)


@app.function(image=eval_image, gpu=ga.GPU, volumes={"/weights": ga.weights, "/vllm-cache": ga.vllm_cache,
                                                       LORA_MOUNT: lora_volume},
              timeout=60 * MINUTES, max_containers=1)
def evaluate(passes: int = 3, smoke: bool = False) -> dict:
    """bench-v2 with the checker (radqc/baseline.py) on the adapter: pass files in resultados/v5/[smoke/]."""
    sys.path.insert(0, "/root")
    lora_volume.reload()
    out: dict = {"adapter_sha256": {f.name: _sha(f) for f in sorted(Path(ADAPTER).glob("adapter_*"))}}
    # a fresh folder per measurement: passes of an earlier run (or another adapter) never mix into this one
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + (_sha_of(out["adapter_sha256"])[:8])
    d = (RESULTS / "smoke" if smoke else RESULTS) / run_id
    d.mkdir(parents=True, exist_ok=False)
    out["run_dir"] = str(d)
    t0 = time.monotonic()
    p = None
    try:
        p, out["start_s"] = _start_vllm()
        os.environ |= {"GLIMMER_BASE_URL": f"http://127.0.0.1:{ga.VLLM_PORT}/v1", "GLIMMER_API_KEY": "local",
                       "GLIMMER_MODEL": LORA_NAME}
        import asyncio

        from radqc import baseline

        bench = "/root/bench-v2.jsonl"
        if smoke:
            Path("/tmp/bench4.jsonl").write_text("".join(open(bench, encoding="utf-8").readlines()[:4]), encoding="utf-8")
            bench = "/tmp/bench4.jsonl"
        out["run"] = asyncio.run(baseline.run(bench, str(d), 1 if smoke else passes, max_usd=3.5,
                                              gpu_usd_hour=3.95, model=None))
        written = [str(d / f"pass{k}.jsonl") for k in range(1, len(out["run"].get("passes", [])) + 1)]
        out["summary"] = baseline.summary(bench, written) if written else None  # no pass: nothing to score
    finally:
        if p:
            p.kill()
        out["total_s"] = round(time.monotonic() - t0, 1)
        out["gpu_usd"] = round(out["total_s"] * H100_USD_S, 2)
        (d / "evaluate.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        lora_volume.commit()  # recorded even when the measurement fails
    return out


@app.function(image=eval_image, gpu=ga.GPU, volumes={"/weights": ga.weights, "/vllm-cache": ga.vllm_cache,
                                                       LORA_MOUNT: lora_volume},
              timeout=4 * MINUTES, max_containers=1)
def lora_check(case_id: str = "B6-0030", text_only: bool = True) -> dict:
    """Compatibility only (no quality): does the served FP8 model load the adapter, and does one bench case answer?
    4 min hard timeout on the H100 (< US$ 0.30). vLLM's own output comes back on failure. `text_only`: no image
    and video profiling, no CUDA graphs (TEXT_ONLY)."""
    import traceback
    import urllib.request as ur

    sys.path.insert(0, "/root")
    lora_volume.reload()
    out: dict = {"adapter_sha256": {f.name: _sha(f) for f in sorted(Path(ADAPTER).glob("adapter_*"))}}
    t0, log, p = time.monotonic(), open("/tmp/vllm.log", "w"), None
    try:
        p = subprocess.Popen([
            "vllm", "serve", ga.MODEL_ID, "--revision", ga.MODEL_REVISION, "--host", "127.0.0.1",
            "--port", str(ga.VLLM_PORT), "--served-model-name", ga.SERVED_NAME, "--max-model-len", str(ga.MAX_MODEL_LEN),
            "--gpu-memory-utilization", "0.90", "--reasoning-parser", "muse_glimmer", "--generation-config", "auto",
            "--enable-lora", "--max-lora-rank", str(RANK), "--lora-modules", f"{LORA_NAME}={ADAPTER}",
        ] + (TEXT_ONLY if text_only else []), stdout=log, stderr=subprocess.STDOUT)
        out["flags"] = TEXT_ONLY if text_only else []
        ga._wait_ready(p, ga.VLLM_PORT, 3 * MINUTES)
        out["start_s"] = round(time.monotonic() - t0, 1)
        with ur.urlopen(f"http://127.0.0.1:{ga.VLLM_PORT}/v1/models", timeout=10) as r:
            out["models"] = [m["id"] for m in json.load(r)["data"]]
        import asyncio

        from oncall_core import qc
        from oncall_core.llm import LLM, Provider

        case = next(json.loads(x) for x in open("/root/bench-v2.jsonl", encoding="utf-8") if json.loads(x)["id"] == case_id)
        lora = Provider("glimmer", "agent", f"http://127.0.0.1:{ga.VLLM_PORT}/v1", "local", LORA_NAME)
        t1 = time.monotonic()
        msg = asyncio.run(LLM().complete(lora, qc.qc_messages("es", case["indication"], case["findings"], case["impression"]),
                                         None, 120, max_tokens=1200))
        out["request_s"] = round(time.monotonic() - t1, 1)
        out["case"] = case_id
        out["raw"] = msg.get("content")
        out["usage"] = msg.get("_usage")
        out["parsed"] = [i.rule for i in qc.parse_model_issues(msg.get("content"), case["indication"], case["findings"],
                                                               case["impression"])]
        out["ok"] = True
    except Exception as e:  # noqa: BLE001 - the result is the error
        out |= {"ok": False, "error": f"{type(e).__name__}: {str(e)[:600]}", "trace": traceback.format_exc()[-1200:]}
    finally:
        if p:
            p.kill()
        log.close()
        lines = Path("/tmp/vllm.log").read_text(errors="replace").splitlines()
        (RESULTS / "smoke").mkdir(parents=True, exist_ok=True)
        (RESULTS / "smoke" / "lora_check_vllm.log").write_text("\n".join(lines), encoding="utf-8")  # the whole log
        out["vllm_errors"] = [x for x in lines if any(k in x for k in ("ERROR", "Error", "LoRA", "lora"))][-25:]
        out["vllm_tail"] = lines[-15:]
        out["total_s"] = round(time.monotonic() - t0, 1)
        out["gpu_usd"] = round(out["total_s"] * H100_USD_S, 2)
        _save("lora_check.json", out, smoke=True)
    return out


@app.function(image=modal.Image.debian_slim(python_version="3.12").add_local_python_source("glimmer_app", "proxy"),
              volumes={LORA_MOUNT: lora_volume},
              timeout=4 * 60 * MINUTES)
def pipeline(only_measure: bool = False, epochs: float = 2, lr: float = 2e-4, smoke: bool = False,
             measure: bool = True) -> dict:
    """Inside Modal (the Mac can be closed): train, then measure (`measure=False`: train only)."""
    s: dict = {"start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if not only_measure:
        s["train"] = train.remote(epochs, RANK, lr, smoke)
        if not s["train"].get("ok") or not measure:
            _save("summary.json", s, smoke)
            return s
    s["evaluate"] = evaluate.remote(3, smoke)
    _save("summary.json", s, smoke)
    return s


@app.local_entrypoint()
def main(only_measure: bool = False, epochs: float = 2, lr: float = 2e-4, smoke: bool = False, measure: bool = True) -> None:
    if not only_measure:
        check_manifest()
    call = pipeline.spawn(only_measure, epochs, lr, smoke, measure)
    print(f"Launched ({call.object_id}). Results: modal volume get oncall-resident-radqc-lora resultados/v5/ ./lora-v5/")
