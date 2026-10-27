import sys
from pathlib import Path
from urllib.parse import unquote

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gateway import create_gateway, has_dot_segment  # noqa: E402

seen = []
ME = {"tailscale-user-login": "rad@example.com"}


def upstream(req: httpx.Request) -> httpx.Response:
    seen.append(req)
    if "boom" in req.url.path:
        raise httpx.ConnectError("down")
    return httpx.Response(200, headers={"content-type": "application/json", "www-authenticate": "Basic", "cache-control": "max-age=3600"},
                          stream=httpx.ByteStream(b'{"ok": true}'))


@pytest.fixture
def gw(tmp_path):
    seen.clear()
    (tmp_path / "index.html").write_text("<html>ohif</html>")
    (tmp_path / "app-config.js").write_text("window.config={}")
    import gzip
    (tmp_path / "app.bundle.js").write_text("")  # OHIF ships empty placeholders next to the real .gz
    (tmp_path / "app.bundle.js.gz").write_bytes(gzip.compress(b"console.log('ohif')"))
    app = create_gateway(allowed={"rad@example.com"}, orthanc="http://orthanc:8042", orthanc_user="u", orthanc_password="p",
                         ohif_dir=str(tmp_path), app_origin="https://app.example.ts.net",
                         client=httpx.AsyncClient(transport=httpx.MockTransport(upstream)))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://gw")


async def test_identity_is_required_and_allowlisted(gw):
    assert (await gw.get("/dicom-web/studies")).status_code == 401
    assert (await gw.get("/dicom-web/studies", headers={"tailscale-user-login": "eve@example.com"})).status_code == 403
    assert (await gw.get("/app-config.js")).status_code == 401
    assert seen == []


async def test_read_only(gw):
    for m in ("POST", "PUT", "DELETE", "PATCH"):
        assert (await gw.request(m, "/dicom-web/studies", headers=ME)).status_code == 405
    assert seen == []


async def test_dicomweb_gets_orthanc_credentials_hides_them_and_is_never_cached(gw):
    r = await gw.get("/dicom-web/studies", params={"PatientID": "x"},
                     headers=ME | {"authorization": "Bearer client", "cookie": "a=b"})
    assert r.status_code == 200
    up = seen[-1]
    assert str(up.url).startswith("http://orthanc:8042/dicom-web/studies") and up.url.params["PatientID"] == "x"
    assert up.headers["authorization"].startswith("Basic ") and "cookie" not in up.headers and "tailscale-user-login" not in up.headers
    assert "www-authenticate" not in r.headers and r.headers["cache-control"] == "no-store, private"
    assert r.headers["content-security-policy"] == "frame-ancestors https://app.example.ts.net"


@pytest.mark.parametrize("path", ["/dicom-web/../instances", "/dicom-web/%2e%2e/instances", "/dicom-web/%252e%252e/tools",
                                  "/dicom-web/./studies", "/../etc/passwd"])
async def test_dot_segments_are_refused(gw, path):
    # call the ASGI app with the raw path, as `curl --path-as-is` sends it (httpx would normalise "..")
    app = gw._transport.app
    sent = []
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "GET", "scheme": "http",
             "path": unquote(path), "raw_path": path.encode(), "query_string": b"", "root_path": "",
             "headers": [(b"host", b"gw"), (b"tailscale-user-login", b"rad@example.com")], "server": ("gw", 80), "client": ("c", 1)}

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(msg):
        sent.append(msg)

    await app(scope, receive, send)
    assert sent[0]["status"] == 400 and seen == []


async def test_upstream_failure_is_a_controlled_502(gw):
    r = await gw.get("/dicom-web/boom", headers=ME)
    assert r.status_code == 502 and r.json()["detail"] == "PACS no disponible" and "content-security-policy" in r.headers


async def test_static_ohif_and_spa_fallback(gw):
    cfg = await gw.get("/app-config.js", headers=ME)
    assert cfg.status_code == 200 and cfg.text == "window.config={}"
    spa = await gw.get("/viewer", params={"StudyInstanceUIDs": "1.2.3"}, headers=ME)
    assert spa.status_code == 200 and "ohif" in spa.text and seen == []


def test_dot_segment_detection():
    assert has_dot_segment("/a/%2E%2E/b") and has_dot_segment("/a\\..\\b") and not has_dot_segment("/dicom-web/studies/1.2.3")


def test_refuses_to_start_without_orthanc_credentials(tmp_path):
    with pytest.raises(RuntimeError):
        create_gateway(allowed=set(), orthanc="x", orthanc_user="", orthanc_password="", ohif_dir=str(tmp_path), app_origin="")


async def test_precompressed_assets_are_served_with_content_encoding(gw):
    r = await gw.get("/app.bundle.js", headers=ME)
    assert r.status_code == 200 and r.headers["content-encoding"] == "gzip"
    assert r.headers["content-type"].startswith("text/javascript") and r.text == "console.log('ohif')"
