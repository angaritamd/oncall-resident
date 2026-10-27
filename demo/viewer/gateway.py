"""Reading-station gateway: the only way into the viewer and Orthanc's DICOMweb from the tailnet.

- every request needs a `Tailscale-User-Login` in ALLOWED_USERS (same rule as the app);
- read-only: GET/HEAD only;
- /dicom-web/* goes to Orthanc with the basic-auth credentials added here (the browser never sees them),
  never cached, and dot segments are refused so the path cannot leave /dicom-web/;
- everything else is the OHIF static build (MIT), served by this process itself: no other container
  shares a network with the gateway except Orthanc, so nothing else can reach it with a forged identity;
- only the app's own origin may frame it (CSP frame-ancestors).
"""
import base64
import mimetypes
import os
from pathlib import Path
from urllib.parse import unquote

import httpx
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.routing import Route

LOGIN_HEADER = "tailscale-user-login"
DROP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding",
        "upgrade", "host", "content-length", "authorization", "cookie", LOGIN_HEADER, "tailscale-user-name",
        "tailscale-user-profile-pic"}


def allowed_users(raw: str | None) -> set[str]:
    return {s.strip().lower() for s in (raw or "").split(",") if s.strip()}


def has_dot_segment(raw_path: str) -> bool:
    # decode repeatedly so %2e%2e / %252e%252e cannot hide a ".." segment
    p = raw_path
    for _ in range(3):
        p = unquote(p)
    return any(seg in (".", "..") for seg in p.replace("\\", "/").split("/"))


def create_gateway(*, allowed: set[str], orthanc: str, orthanc_user: str, orthanc_password: str, ohif_dir: str,
                   app_origin: str, client: httpx.AsyncClient | None = None) -> Starlette:
    if not orthanc_user or not orthanc_password:
        raise RuntimeError("Orthanc credentials missing")
    root = Path(ohif_dir).resolve()
    http = client or httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))
    basic = "Basic " + base64.b64encode(f"{orthanc_user}:{orthanc_password}".encode()).decode()
    security = {
        "content-security-policy": f"frame-ancestors {app_origin}" if app_origin else "frame-ancestors 'none'",
        "x-content-type-options": "nosniff",
        "referrer-policy": "no-referrer",
    }
    no_store = {"cache-control": "no-store, private"}

    def error(status: int, detail: str, extra: dict | None = None):
        return JSONResponse({"detail": detail}, status, headers=security | (extra or {}))

    async def dicomweb(request: Request, raw_path: str):
        target = orthanc.rstrip("/") + raw_path  # raw (still-encoded) path: %3F / %23 stay data, not delimiters
        headers = {k: v for k, v in request.headers.items() if k.lower() not in DROP} | {"authorization": basic}
        try:
            upstream = http.build_request(request.method, target, params=request.query_params, headers=headers)
            resp = await http.send(upstream, stream=True)
        except httpx.HTTPError:
            return error(502, "PACS no disponible", no_store)
        out = {k: v for k, v in resp.headers.items() if k.lower() not in DROP | {"www-authenticate", "set-cookie", "cache-control"}}
        return StreamingResponse(resp.aiter_raw(), status_code=resp.status_code, headers=out | security | no_store,
                                 background=BackgroundTask(resp.aclose))

    def serve_file(f: Path, extra: dict):
        # the OHIF image ships its assets precompressed (`gzip_static always`): the plain files are empty
        # placeholders, so the .gz is served with Content-Encoding and the original media type
        gz = f.with_name(f.name + ".gz")
        if gz.is_file():
            media = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
            return FileResponse(gz, media_type=media, headers=security | extra | {"content-encoding": "gzip", "vary": "accept-encoding"})
        return FileResponse(f, headers=security | extra)

    def static(path: str):
        rel = path.lstrip("/")
        f = (root / rel).resolve() if rel else root / "index.html"
        if (f.is_file() or f.with_name(f.name + ".gz").is_file()) and f.is_relative_to(root):
            return serve_file(f, {})
        return serve_file(root / "index.html", no_store)  # SPA routes such as /viewer

    async def handle(request: Request):
        login = (request.headers.get(LOGIN_HEADER) or "").strip().lower()
        if not login:
            return error(401, "tailnet identity required")
        if login not in allowed:
            return error(403, "not allowed")
        if request.method not in ("GET", "HEAD"):
            return error(405, "read-only")
        raw_path = request.scope.get("raw_path", b"").decode("latin-1") or request.url.path
        if has_dot_segment(raw_path):
            return error(400, "invalid path")
        path = request.url.path
        if path == "/dicom-web" or path.startswith("/dicom-web/"):
            return await dicomweb(request, raw_path)
        return static(path)

    methods = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    return Starlette(routes=[Route("/{path:path}", handle, methods=methods)])


def app() -> Starlette:  # uvicorn factory
    e = os.environ
    return create_gateway(
        allowed=allowed_users(e.get("ALLOWED_USERS")),
        orthanc=e.get("ORTHANC_URL", "http://orthanc:8042"),
        orthanc_user=e.get("ORTHANC_USER", ""),
        orthanc_password=e.get("ORTHANC_PASSWORD", ""),
        ohif_dir=e.get("OHIF_DIR", "/srv/ohif"),
        app_origin=e.get("APP_ORIGIN", ""),
    )
