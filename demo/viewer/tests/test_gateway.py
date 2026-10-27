import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gateway import create_gateway  # noqa: E402

seen = []


def upstream(req: httpx.Request) -> httpx.Response:
    seen.append(req)
    return httpx.Response(200, headers={"content-type": "application/json", "www-authenticate": "Basic"},
                          stream=httpx.ByteStream(b'{"ok": true}'))


@pytest.fixture
def gw():
    seen.clear()
    app = create_gateway(allowed={"rad@example.com"}, orthanc="http://orthanc:8042", orthanc_user="u", orthanc_password="p",
                         ohif="http://ohif:8080", app_origin="https://app.example.ts.net",
                         client=httpx.AsyncClient(transport=httpx.MockTransport(upstream)))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://gw")


async def test_identity_is_required_and_allowlisted(gw):
    assert (await gw.get("/dicom-web/studies")).status_code == 401
    assert (await gw.get("/dicom-web/studies", headers={"tailscale-user-login": "eve@example.com"})).status_code == 403
    assert seen == []


async def test_read_only(gw):
    for m in ("POST", "PUT", "DELETE", "PATCH"):
        r = await gw.request(m, "/dicom-web/studies", headers={"tailscale-user-login": "rad@example.com"})
        assert r.status_code == 405
    assert seen == []


async def test_dicomweb_gets_orthanc_credentials_and_hides_them(gw):
    r = await gw.get("/dicom-web/studies", params={"PatientID": "x"},
                     headers={"tailscale-user-login": "RAD@example.com", "authorization": "Bearer client", "cookie": "a=b"})
    assert r.status_code == 200
    up = seen[-1]
    assert str(up.url).startswith("http://orthanc:8042/dicom-web/studies") and up.url.params["PatientID"] == "x"
    assert up.headers["authorization"].startswith("Basic ") and "cookie" not in up.headers
    assert "tailscale-user-login" not in up.headers
    assert "www-authenticate" not in r.headers
    assert r.headers["content-security-policy"] == "frame-ancestors https://app.example.ts.net"


async def test_everything_else_is_ohif_without_credentials(gw):
    r = await gw.get("/viewer", params={"StudyInstanceUIDs": "1.2.3"}, headers={"tailscale-user-login": "rad@example.com"})
    up = seen[-1]
    assert r.status_code == 200 and str(up.url).startswith("http://ohif:8080/viewer") and "authorization" not in up.headers


def test_refuses_to_start_without_orthanc_credentials():
    with pytest.raises(RuntimeError):
        create_gateway(allowed=set(), orthanc="x", orthanc_user="", orthanc_password="", ohif="y", app_origin="")
