"""oncall-resident-glimmer: Muse Glimmer (Meta, open weights, Apache-2.0) served with vLLM on Modal.

Written from scratch for this repo. OpenAI-compatible API behind serving/proxy.py, which requires
`Authorization: Bearer <GLIMMER_API_KEY>` on every route.

  modal run serving/glimmer_app.py::download      # once: weights into the volume
  modal deploy serving/glimmer_app.py             # scale-to-zero by default
  GLIMMER_LORA=1 modal deploy serving/glimmer_app.py   # also serves the RAD·QC v5 adapter as model "radqc-v5"

Cost: MIN_CONTAINERS defaults to 0 (pay only while a container is up; it scales down after
SCALEDOWN_SECONDS of idleness). MIN_CONTAINERS>=1 keeps an H100 running 24/7.
"""
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

import modal

APP_NAME = "oncall-resident-glimmer"
MODEL_ID = "RedHatAI/Muse-Glimmer-30B-FP8-block"  # FP8 build of meta-models/Muse-Glimmer-30B
MODEL_REVISION = "1deb4641ff84f9a728dd11b27cac1f6a02a9ed14"
SERVED_NAME = "muse-glimmer"
GPU = "H100"
MAX_MODEL_LEN = 32768
MIN_CONTAINERS = int(os.environ.get("MIN_CONTAINERS", "0"))
SCALEDOWN_SECONDS = int(os.environ.get("SCALEDOWN_SECONDS", "300"))
PROXY_PORT, VLLM_PORT = 8000, 8001
# RAD·QC v5 LoRA (ANG-174), off unless GLIMMER_LORA=1 at deploy time (Miguel: only once v5 beats the baseline on
# bench-v2). The adapter is served as its own model next to the base one, from the volume serving/train_v5.py writes.
LORA = os.environ.get("GLIMMER_LORA", "").strip() == "1"
LORA_NAME, LORA_MOUNT, LORA_RANK = "radqc-v5", "/lora", 16
# vLLM 0.28 wraps the vision tower's linears for LoRA too and its startup profiling runs a dummy video through them
# (lora_shrink assertion, 30 Oct): with an adapter, text only (no image or video) and eager
TEXT_ONLY = ["--limit-mm-per-prompt", '{"image": 0, "video": 0}', "--enforce-eager"]

if MIN_CONTAINERS >= 1:
    print(f"WARNING: MIN_CONTAINERS={MIN_CONTAINERS} keeps {MIN_CONTAINERS}x {GPU} running all the time "
          "(billed 24/7). Use 0 unless you need zero cold starts.", file=sys.stderr)

image = (
    modal.Image.from_registry(
        "vllm/vllm-openai:v0.28.0@sha256:61fc8a896b0a4fbbbdc063bc4b0dbc25ce98e02b5050c24aeb7830ac02039b14",
        # the image ships python3 only; Modal needs `python` (vLLM, huggingface_hub, starlette and uvicorn
        # are already installed in that interpreter)
        setup_dockerfile_commands=["RUN ln -sf /usr/bin/python3 /usr/bin/python"],
    )
    .entrypoint([])
    .env({"HF_HOME": "/weights", "VLLM_CACHE_ROOT": "/vllm-cache", "HF_HUB_DISABLE_TELEMETRY": "1"})
    .add_local_python_source("proxy")
)

weights = modal.Volume.from_name("oncall-resident-glimmer-weights", create_if_missing=True)
vllm_cache = modal.Volume.from_name("oncall-resident-glimmer-vllm-cache", create_if_missing=True)
key = modal.Secret.from_name("oncall-resident-glimmer-key")  # GLIMMER_API_KEY
lora_volume = modal.Volume.from_name("oncall-resident-radqc-lora", create_if_missing=True)  # written by train_v5.py

app = modal.App(APP_NAME)


@app.function(image=image, volumes={"/weights": weights}, timeout=60 * 60)
def download():
    from huggingface_hub import snapshot_download

    snapshot_download(MODEL_ID, revision=MODEL_REVISION)
    weights.commit()


def _wait_ready(proc: subprocess.Popen, port: int, deadline_s: int) -> None:
    """Fails as soon as vLLM exits (OOM, bad revision, corrupt weights) instead of billing GPU time until
    the deadline."""
    end = time.time() + deadline_s
    while time.time() < end:
        if proc.poll() is not None:
            raise RuntimeError(f"vLLM exited during startup with code {proc.returncode}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as r:
                if r.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            pass  # not listening yet
        time.sleep(1)
    proc.kill()
    raise RuntimeError("vLLM did not become healthy in time")


def vllm_cmd(lora: bool = LORA) -> list[str]:
    cmd = [
        "vllm", "serve", MODEL_ID,
        "--revision", MODEL_REVISION,
        "--host", "127.0.0.1", "--port", str(VLLM_PORT),
        "--served-model-name", SERVED_NAME,
        "--max-model-len", str(MAX_MODEL_LEN),
        "--gpu-memory-utilization", "0.90",
        "--enable-auto-tool-choice",
        "--tool-call-parser", "muse_glimmer",
        "--reasoning-parser", "muse_glimmer",
        "--generation-config", "auto",
    ]
    if lora:
        cmd += ["--enable-lora", "--max-lora-rank", str(LORA_RANK),
                "--lora-modules", f"{LORA_NAME}={LORA_MOUNT}/{LORA_NAME}", *TEXT_ONLY]
    return cmd


@app.function(
    image=image,
    gpu=GPU,
    volumes={"/weights": weights, "/vllm-cache": vllm_cache} | ({LORA_MOUNT: lora_volume} if LORA else {}),
    secrets=[key],
    min_containers=MIN_CONTAINERS,
    scaledown_window=SCALEDOWN_SECONDS,
    timeout=60 * 30,
)
@modal.concurrent(max_inputs=32)
@modal.web_server(port=PROXY_PORT, startup_timeout=60 * 15)
def serve():
    t0 = time.time()
    vllm = subprocess.Popen(vllm_cmd())
    _wait_ready(vllm, VLLM_PORT, 60 * 14)
    print(f"vLLM ready after {time.time() - t0:.1f}s", flush=True)
    # the public port only opens once vLLM is healthy, so Modal holds requests until then
    subprocess.Popen([
        "uvicorn", "proxy:app", "--factory", "--host", "0.0.0.0", "--port", str(PROXY_PORT),
        "--no-access-log",
    ], env={**os.environ, "VLLM_UPSTREAM": f"http://127.0.0.1:{VLLM_PORT}"})
