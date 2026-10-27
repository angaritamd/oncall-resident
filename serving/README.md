# serving: `oncall-resident-glimmer`

A Modal app written from scratch for this repo. It serves **Muse Glimmer** (Meta, open weights, Apache-2.0), using the FP8 build `RedHatAI/Muse-Glimmer-30B-FP8-block` pinned by revision, with **vLLM 0.28** (image pinned by digest) on one H100. The API is OpenAI-compatible, with tool calling (`--tool-call-parser muse_glimmer`).

- **Auth on every route:** `proxy.py` sits in front of vLLM and checks `Authorization: Bearer <GLIMMER_API_KEY>` with a constant-time comparison. That covers `/v1/*`, `/health`, `/invocations`, `/metrics` and `/`. vLLM itself only listens on loopback, and its `--api-key` is not relied on. The proxy port opens only once vLLM is healthy.
- **Cost:**
  - `MIN_CONTAINERS=0` by default (scale to zero) and `SCALEDOWN_SECONDS=300`.
  - Deploying with `MIN_CONTAINERS>=1` prints a warning: it keeps an H100 running 24/7.
- **Secrets:** the key lives in the Modal Secret `oncall-resident-glimmer-key` and in `demo/.env` on the demo host. It is never in the repo.
- **Volumes:** `oncall-resident-glimmer-weights` and `oncall-resident-glimmer-vllm-cache`. These are separate from any other app.

```sh
cd serving
uv run --locked pytest -q                  # proxy auth tests (no GPU)
modal run glimmer_app.py::download         # once
modal deploy glimmer_app.py
```

Measured cold start and warm latency: see `BUILD_LOG.md`.
