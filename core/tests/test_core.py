import os
from pathlib import Path

os.environ["ONCALL_NO_APP"] = "1"

import pytest
from fastapi.testclient import TestClient

from adapters.base import SourceUnavailable, Study
from adapters.orthanc.qido import parse_study
from oncall_core import intents
from oncall_core.main import create_app

CASES = Path(__file__).resolve().parents[2] / "demo/seed/cases.json"
UIDS = {
    "DEMO-0001": "1.3.6.1.4.1.14519.5.2.1.6279.6001.116951808801102574107980626851",
    "DEMO-0002": "1.3.6.1.4.1.14519.5.2.1.6279.6001.210460865401632134346677582159",
    "DEMO-0003": "1.3.6.1.4.1.14519.5.2.1.6279.6001.270617793094907821983261388534",
    "DEMO-0004": "1.3.6.1.4.1.14519.5.2.1.6279.6001.339170810277323131167631068432",
    "DEMO-0005": "1.3.6.1.4.1.14519.5.2.1.6279.6001.182110250999021699484937823450",
}


class FakeSource:
    def __init__(self, uids, down=False):
        self.studies = [Study(u, f"P{i}", ("CT",), "20000101", None, 1, 10) for i, u in enumerate(uids)]
        self.down = down

    async def list_studies(self):
        if self.down:
            raise SourceUnavailable("down")
        return self.studies

    async def studies_for_patient(self, pid):
        return [s for s in self.studies if s.patient_id == pid]

    async def ping(self):
        return not self.down


def client(uids=UIDS.values(), down=False):
    return TestClient(create_app(FakeSource(list(uids), down), str(CASES)))


def test_order_critical_then_priority_then_wait():
    r = client().get("/api/worklist").json()
    assert [i["case_id"] for i in r["items"]] == ["DEMO-0001", "DEMO-0002", "DEMO-0005", "DEMO-0004", "DEMO-0003"]
    first = r["items"][0]
    assert first["reasons"][0] == {"kind": "critical", "label": "Crítico", "source": "Tecnólogo"}


def test_unknown_study_listed_last_without_invented_metadata():
    r = client(list(UIDS.values()) + ["9.9.9"]).get("/api/worklist?lang=en").json()
    last = r["items"][-1]
    assert last["study_uid"] == "9.9.9" and last["has_metadata"] is False and last["exam"] is None
    assert last["reasons"][0]["source"] == "No metadata"


def test_chat_worklist_and_open_and_why():
    c = client()
    r = c.post("/api/chat", json={"text": "¿Qué tengo pendiente?"}).json()
    assert r["intent"] == "worklist" and r["blocks"][0]["item"]["case_id"] == "DEMO-0001"
    assert "5 estudios" in r["text"]
    r = c.post("/api/chat", json={"text": "Abrir caso DEMO-0004", "lang": "en"}).json()
    case = r["blocks"][0]["case"]
    assert case["case_id"] == "DEMO-0004" and case["priors_declared"] is True and case["priors_in_pacs"] == 0
    r = c.post("/api/chat", json={"text": "¿Por qué va primero?"}).json()
    assert r["intent"] == "why" and "tecnólogo" in r["text"]


def test_empty_and_down():
    assert client([]).post("/api/chat", json={"text": "pendientes"}).json()["blocks"] == []
    c = client(down=True)
    assert c.post("/api/chat", json={"text": "pendientes"}).status_code == 503
    assert c.get("/api/health").json()["pacs"] == "down"


def test_case_not_found():
    assert client().get("/api/cases/DEMO-9999").status_code == 404


@pytest.mark.parametrize("text,intent", [
    ("What's pending?", "worklist"), ("qué tengo pendiente", "worklist"),
    ("open DEMO-0002", "open"), ("demo-0003", "open"), ("why is it first?", "why"), ("hola", "help"),
])
def test_intents(text, intent):
    assert intents.match(text)[0] == intent


def test_parse_qido():
    s = parse_study({"0020000D": {"vr": "UI", "Value": ["1.2"]}, "00080061": {"vr": "CS", "Value": ["CT", "SR"]}, "00201208": {"vr": "IS", "Value": [3]}})
    assert s.study_uid == "1.2" and s.modalities == ("CT", "SR") and s.instance_count == 3 and s.patient_id == ""
