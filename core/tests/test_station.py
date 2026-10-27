import asyncio
import json
import os

os.environ["ONCALL_NO_APP"] = "1"

import pytest

from oncall_core import station as stmod
from oncall_core.station import StationError, Stations
from tests.test_reports import app_with

ME, OTHER = "rad@example.com", "eve@example.com"


def test_pair_link_single_use_same_login():
    s = Stations()
    st = s.pair(ME)
    assert len(st.code) == 4 and st.code.isdigit()
    with pytest.raises(StationError):          # another tailnet login cannot take my station
        s.link(OTHER, st.code)
    s.link(ME, st.code)
    assert s.linked(ME).id == st.id and st.code is None
    with pytest.raises(StationError):          # single use
        s.link(ME, "0000" if st.id else "")


def test_code_expires(monkeypatch):
    s = Stations()
    st = s.pair(ME)
    st.code_expires = 0
    with pytest.raises(StationError, match="vencido"):
        s.link(ME, st.code)


def test_wrong_codes_are_rate_limited():
    s = Stations()
    s.pair(ME)
    for _ in range(stmod.MAX_FAILS):
        with pytest.raises(StationError) as e:
            s.link(ME, "9999" if s.by_id and list(s.by_id.values())[0].code != "9999" else "9998")
        assert e.value.code == 404
    with pytest.raises(StationError) as e:
        s.link(ME, "1234")
    assert e.value.code == 429


def test_only_valid_uids_are_pushed():
    s = Stations()
    st = s.pair(ME)
    s.link(ME, st.code)
    q = asyncio.Queue()
    st.queues.append(q)
    assert not s.push_open(ME, 'x"; alert(1)')
    assert not s.push_open(OTHER, "1.2.3")
    assert s.push_open(ME, "1.3.6.1.4.1.14519.5.2.1.6279.6001.116951808801102574107980626851")
    assert q.get_nowait() == {"type": "open", "study_uid": "1.3.6.1.4.1.14519.5.2.1.6279.6001.116951808801102574107980626851"}


async def test_stream_sends_uid_only():
    s = Stations()
    st = s.pair(ME)
    s.link(ME, st.code)
    gen = s.stream(st, keepalive_s=5)
    assert (await gen.__anext__()).startswith("event: ready")
    s.push_open(ME, "1.2.840.99")
    ev = await gen.__anext__()
    assert ev.startswith("event: open") and json.loads(ev.split("data: ", 1)[1]) == {"study_uid": "1.2.840.99"}
    await gen.aclose()
    assert st.queues == []


def test_api_flow_and_opening_a_case_pushes_its_uid():
    c, store, _ = app_with({}, [])
    me = {"x-resident-login": ME}
    assert c.post("/api/station/pair").status_code == 403
    paired = c.post("/api/station/pair", headers=me).json()
    assert c.get("/api/station/state", params={"station": paired["station_id"]}, headers={"x-resident-login": OTHER}).status_code == 404
    assert c.post("/api/station/link", json={"code": "12"}, headers=me).status_code == 422
    assert c.post("/api/station/link", json={"code": paired["code"]}, headers=me).json() == {"linked": True}
    assert c.get("/api/station/config", headers=me).json()["linked"] is True
    st = c.app.state.stations.by_id[paired["station_id"]]
    q = asyncio.Queue()
    st.queues.append(q)
    c.get("/api/cases/DEMO-0001", headers=me)  # phone opens a case -> station receives the UID only
    assert q.get_nowait() == {"type": "open", "study_uid": "1.3.6.1.4.1.14519.5.2.1.6279.6001.116951808801102574107980626851"}
    assert c.post("/api/station/open", json={"case_id": "DEMO-0002"}, headers=me).json() == {"sent": True}
    assert q.get_nowait()["study_uid"].endswith("582159")
    assert c.post("/api/station/open", json={"case_id": "DEMO-0002"}, headers={"x-resident-login": OTHER}).status_code == 409
    assert c.get("/api/station/state", params={"station": paired["station_id"]}, headers=me).json()["linked"] is True
