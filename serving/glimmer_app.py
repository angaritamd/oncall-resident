"""oncall-resident-glimmer: Muse Glimmer (Meta, open weights, Apache-2.0) served with vLLM on Modal.

Written from scratch for this repo. OpenAI-compatible API behind serving/proxy.py, which requires
`Authorization: Bearer <GLIMMER_API_KEY>` on every route.

  modal run serving/glimmer_app.py::download      # once: weights into the volume
  modal deploy serving/glimmer_app.py             # scale-to-zero by default

Cost: MIN_CONTAINERS defaults to 0 (pay only while a container is up; it scales down after
SCALEDOWN_SECONDS of idleness). MIN_CONTAINERS>=1 keeps an H100 running 24/7.
"""
import os
import subprocess
import sys
import time
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

app = modal.App(APP_NAME)


@app.function(image=image, volumes={"/weights": weights}, timeout=60 * 60)
def download():
    from huggingface_hub import snapshot_download

    snapshot_download(MODEL_ID, revision=MODEL_REVISION)
    weights.commit()


def _wait_ready(port: int, deadline_s: int) -> None:
    end = time.time() + deadline_s
    while time.time() < end:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as r:
                if r.status == 200:
                    return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("vLLM did not become healthy in time")


@app.function(
    image=image,
    gpu=GPU,
    volumes={"/weights": weights, "/vllm-cache": vllm_cache},
    secrets=[key],
    min_containers=MIN_CONTAINERS,
    scaledown_window=SCALEDOWN_SECONDS,
    timeout=60 * 30,
)
@modal.concurrent(max_inputs=32)
@modal.web_server(port=PROXY_PORT, startup_timeout=60 * 15)
def serve():
    t0 = time.time()
    subprocess.Popen([
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
    ])
    _wait_ready(VLLM_PORT, 60 * 14)
    print(f"vLLM ready after {time.time() - t0:.1f}s", flush=True)
    # the public port only opens once vLLM is healthy, so Modal holds requests until then
    subprocess.Popen([
        "uvicorn", "proxy:app", "--factory", "--host", "0.0.0.0", "--port", str(PROXY_PORT),
        "--no-access-log",
    ], env={**os.environ, "VLLM_UPSTREAM": f"http://127.0.0.1:{VLLM_PORT}"})
