"""Bearer-auth reverse proxy in front of vLLM.

vLLM's own --api-key only guards part of its routes, so every request (including /health,
/invocations and /metrics) is checked here first, with a constant-time comparison, and only then
streamed to the vLLM server listening on loopback.
"""
import hmac
import os

import httpx
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

HOP_BY_HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers",
              "transfer-encoding", "upgrade", "host", "content-length", "authorization"}


def authorized(header: str | None, key: str) -> bool:
    if not key or not header or not header.startswith("Bearer "):
        return False
    return hmac.compare_digest(header[len("Bearer "):].encode(), key.encode())


def create_proxy(upstream: str, api_key: str, client: httpx.AsyncClient | None = None) -> Starlette:
    if not api_key:
        raise RuntimeError("GLIMMER_API_KEY is empty; refusing to start an unauthenticated proxy")
    http = client or httpx.AsyncClient(base_url=upstream, timeout=httpx.Timeout(600.0, connect=10.0))

    async def forward(request: Request):
        if not authorized(request.headers.get("authorization"), api_key):
            return JSONResponse({"error": "unauthorized"}, status_code=401, headers={"www-authenticate": "Bearer"})
        headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP}
        upstream_req = http.build_request(request.method, request.url.path, params=request.query_params,
                                          headers=headers, content=await request.body())
        resp = await http.send(upstream_req, stream=True)
        out_headers = {k: v for k, v in resp.headers.items() if k.lower() not in HOP_BY_HOP}
        return StreamingResponse(resp.aiter_raw(), status_code=resp.status_code, headers=out_headers,
                                 background=BackgroundTask(resp.aclose))

    methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
    return Starlette(routes=[Route("/{path:path}", forward, methods=methods)])


def app() -> Starlette:  # uvicorn factory
    return create_proxy(os.environ.get("VLLM_UPSTREAM", "http://127.0.0.1:8001"), os.environ.get("GLIMMER_API_KEY", ""))
