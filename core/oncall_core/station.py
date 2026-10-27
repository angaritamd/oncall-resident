"""Reading-station sync, level 1: a desktop station shows OHIF; a phone paired with a 4-digit code makes the
station open the study the phone opened. Only Study Instance UIDs travel; never PHI, never pixels.

Pairing rules: the code is single-use, expires in 10 minutes, and only links a phone signed in with the SAME
tailnet login as the station; a login gets 5 wrong attempts per 10 minutes. State is in memory (a restart
asks to pair again)."""
import asyncio
import re
import secrets
import time
from dataclasses import dataclass, field

UID_RE = re.compile(r"[0-2](?:\.\d+){1,63}")  # a DICOM UID: the only thing that travels to the station
CODE_TTL_S = 600
MAX_FAILS = 5
FAIL_WINDOW_S = 600


class StationError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code, self.message = code, message


@dataclass
class Station:
    id: str
    owner: str
    code: str | None
    code_expires: float
    queues: list = field(default_factory=list)  # one asyncio.Queue per open SSE stream
    last_uid: str | None = None


class Stations:
    def __init__(self):
        self.by_id: dict[str, Station] = {}
        self.links: dict[str, str] = {}          # phone login -> station id
        self.fails: dict[str, list[float]] = {}  # login -> failed attempt times

    def pair(self, owner: str) -> Station:
        if not owner:
            raise StationError(403, "identity required")
        # one live station per login: a new pairing replaces the previous one
        for sid, st in list(self.by_id.items()):
            if st.owner == owner:
                self.by_id.pop(sid)
        used = {s.code for s in self.by_id.values()}
        code = next(c for c in (f"{secrets.randbelow(10_000):04d}" for _ in range(100)) if c not in used)
        st = Station(secrets.token_urlsafe(24), owner, code, time.monotonic() + CODE_TTL_S)
        self.by_id[st.id] = st
        self.links = {k: v for k, v in self.links.items() if v in self.by_id}
        return st

    def link(self, login: str, code: str) -> Station:
        if not login:
            raise StationError(403, "identity required")
        now = time.monotonic()
        recent = [t for t in self.fails.get(login, []) if now - t < FAIL_WINDOW_S]
        if len(recent) >= MAX_FAILS:
            raise StationError(429, "Demasiados intentos; espera unos minutos")
        st = next((s for s in self.by_id.values() if s.code and s.code == code.strip() and s.code_expires > now), None)
        if not st or st.owner != login:
            self.fails[login] = recent + [now]
            raise StationError(404, "Código no válido o vencido")
        st.code = None  # single use
        self.links[login] = st.id
        return st

    def unlink(self, login: str) -> None:
        sid = self.links.pop(login, None)
        st = self.by_id.get(sid) if sid else None
        if st and not self.is_linked(st):
            st.last_uid = None  # an unlinked station forgets the study (nothing to replay)

    def is_linked(self, st: Station) -> bool:
        return any(sid == st.id for sid in self.links.values())

    def linked(self, login: str) -> Station | None:
        sid = self.links.get(login)
        return self.by_id.get(sid) if sid else None

    def owned(self, station_id: str, login: str) -> Station:
        st = self.by_id.get(station_id)
        if not st or st.owner != login:
            raise StationError(404, "station not found")
        return st

    def push_open(self, login: str, study_uid: str) -> bool:
        """Sends {"study_uid"} to the phone's linked station. Returns True only if a connected station stream
        received it; the UID is remembered either way and replayed when the station (re)connects."""
        st = self.linked(login)
        if not st or not study_uid or not UID_RE.fullmatch(study_uid):
            return False
        st.last_uid = study_uid
        for q in st.queues:
            q.put_nowait({"type": "open", "study_uid": study_uid})
        return len(st.queues) > 0

    async def stream(self, st: Station, keepalive_s: float = 15.0):
        q: asyncio.Queue = asyncio.Queue()
        st.queues.append(q)
        try:
            yield "event: ready\ndata: {}\n\n"
            if st.last_uid and self.is_linked(st):  # a study opened while the station was disconnected is not lost
                yield f"event: open\ndata: {{\"study_uid\": \"{st.last_uid}\"}}\n\n"
            while True:
                try:
                    ev = await asyncio.wait_for(q.get(), keepalive_s)
                    yield f"event: open\ndata: {{\"study_uid\": \"{ev['study_uid']}\"}}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            st.queues.remove(q)
