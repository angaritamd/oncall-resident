"""Reading-station gateway: the only way into OHIF and Orthanc's DICOMweb from the tailnet.

- every request needs a `Tailscale-User-Login` in ALLOWED_USERS (same rule as the app);
- read-only: GET/HEAD only;
- /dicom-web/* goes to Orthanc with the basic-auth credentials added here (the browser never sees them);
- everything else is the OHIF static app;
- only the app's own origin may frame it (CSP frame-ancestors).
"""
import base64
import os

import httpx
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

LOGIN_HEADER = "tailscale-user-login"
DROP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding",
        "upgrade", "host", "content-length", "authorization", "cookie", LOGIN_HEADER, "tailscale-user-name",
        "tailscale-user-profile-pic"}


def allowed_users(raw: str | None) -> set[str]:
    return {s.strip().lower() for s in (raw or "").split(",") if s.strip()}


def create_gateway(*, allowed: set[str], orthanc: str, orthanc_user: str, orthanc_password: str, ohif: str,
                   app_origin: str, client: httpx.AsyncClient | None = None) -> Starlette:
    if not orthanc_user or not orthanc_password:
        raise RuntimeError("Orthanc credentials missing")
    http = client or httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))
    basic = "Basic " + base64.b64encode(f"{orthanc_user}:{orthanc_password}".encode()).decode()
    security = {
        "content-security-policy": f"frame-ancestors {app_origin}" if app_origin else "frame-ancestors 'none'",
        "x-content-type-options": "nosniff",
        "referrer-policy": "no-referrer",
    }

    async def handle(request: Request):
        login = (request.headers.get(LOGIN_HEADER) or "").strip().lower()
        if not login:
            return JSONResponse({"detail": "tailnet identity required"}, 401, headers=security)
        if login not in allowed:
            return JSONResponse({"detail": "not allowed"}, 403, headers=security)
        if request.method not in ("GET", "HEAD"):
            return JSONResponse({"detail": "read-only"}, 405, headers=security)
        path = request.url.path
        if path == "/dicom-web" or path.startswith("/dicom-web/"):
            target, extra = orthanc.rstrip("/") + path, {"authorization": basic}
        else:
            target, extra = ohif.rstrip("/") + path, {}
        headers = {k: v for k, v in request.headers.items() if k.lower() not in DROP} | extra
        upstream = http.build_request(request.method, target, params=request.query_params, headers=headers)
        resp = await http.send(upstream, stream=True)
        out = {k: v for k, v in resp.headers.items() if k.lower() not in DROP | {"www-authenticate", "set-cookie"}}
        out |= security
        return StreamingResponse(resp.aiter_raw(), status_code=resp.status_code, headers=out,
                                 background=BackgroundTask(resp.aclose))

    methods = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    return Starlette(routes=[Route("/{path:path}", handle, methods=methods)])


def app() -> Starlette:  # uvicorn factory
    e = os.environ
    return create_gateway(
        allowed=allowed_users(e.get("ALLOWED_USERS")),
        orthanc=e.get("ORTHANC_URL", "http://orthanc:8042"),
        orthanc_user=e.get("ORTHANC_USER", ""),
        orthanc_password=e.get("ORTHANC_PASSWORD", ""),
        ohif=e.get("OHIF_URL", "http://ohif:8080"),
        app_origin=e.get("APP_ORIGIN", ""),
    )
