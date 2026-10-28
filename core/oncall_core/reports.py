"""Draft reports: versions, QC after every change, and human-only signing that locks the report."""
import asyncio
import difflib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import qc
from .templates import blanks
from .llm import LLM, Provider, ProviderError, log_usage
from .store import Store

SECTIONS = ("technique", "findings", "impression")

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
  case_id TEXT PRIMARY KEY, version INTEGER NOT NULL, technique TEXT NOT NULL, findings TEXT NOT NULL,
  impression TEXT NOT NULL, status TEXT NOT NULL, qc_mode TEXT, signed_by TEXT, signed_at TEXT, updated_at TEXT NOT NULL,
  qc_version INTEGER          -- version whose QC has completed; signing requires qc_version == version
);
CREATE TABLE IF NOT EXISTS report_versions (
  case_id TEXT NOT NULL, version INTEGER NOT NULL, technique TEXT, findings TEXT, impression TEXT,
  at TEXT NOT NULL, by TEXT NOT NULL, PRIMARY KEY (case_id, version)
);
CREATE TABLE IF NOT EXISTS qc_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, version INTEGER NOT NULL, rule TEXT NOT NULL,
  severity TEXT NOT NULL, source TEXT NOT NULL, body_label TEXT NOT NULL, body_excerpt TEXT, impression_excerpt TEXT,
  explanation TEXT, fix_find TEXT, fix_replace TEXT, marks TEXT, status TEXT NOT NULL, reason TEXT, at TEXT NOT NULL
);
"""


class ReportError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code, self.message = code, message


@dataclass
class QcContext:
    llm: LLM
    providers: list[Provider]
    timeout: float = 40.0
    budget: float = 45.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def diff_lines(before: str, after: str) -> list[dict]:
    """Word-level diff for the UI: [{"op": "eq"|"del"|"ins", "text": ...}]."""
    a, b = before.split(" "), after.split(" ")
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag == "equal":
            out.append({"op": "eq", "text": " ".join(a[i1:i2])})
        else:
            if i2 > i1:
                out.append({"op": "del", "text": " ".join(a[i1:i2])})
            if j2 > j1:
                out.append({"op": "ins", "text": " ".join(b[j1:j2])})
    return out


class Reports:
    def __init__(self, store: Store, qc_ctx: QcContext | None = None, indication_for=None, background_qc: bool = False):
        # background_qc: after a change, the proven rule alerts are stored at once and the model checker runs in the
        # background; the version is not signable until that run finishes (qc_version stays unset meanwhile)
        self.background_qc = background_qc
        self._tasks: set[asyncio.Task] = set()
        # at most one background QC per case (a newer version waits for it and is checked next), and a global cap
        self._qc_running: dict[str, bool] = {}
        self._qc_again: set[str] = set()
        self._qc_slots = asyncio.Semaphore(2)
        self.store, self.db, self.lock = store, store._db, store._lock
        self.qc_ctx = qc_ctx
        self.indication_for = indication_for or (lambda case_id, lang: "")
        with self.lock:
            self.db.executescript(SCHEMA)
            cols = {r["name"] for r in self.db.execute("PRAGMA table_info(reports)")}
            # proposal: NULL (dictated by the radiologist) | 'pending' (template, not yet accepted) | 'accepted'
            for col, typ in (("qc_version", "INTEGER"), ("proposal", "TEXT"), ("template", "TEXT")):
                if col not in cols:
                    self.db.execute(f"ALTER TABLE reports ADD COLUMN {col} {typ}")

    # ---- reading --------------------------------------------------------------------------------------
    def _row(self, case_id: str) -> dict | None:
        with self.lock:
            r = self.db.execute("SELECT * FROM reports WHERE case_id = ?", (case_id,)).fetchone()
        return dict(r) if r else None

    def state(self, case_id: str) -> dict | None:
        r = self._row(case_id)
        if not r:
            return None
        with self.lock:
            items = [dict(x) for x in self.db.execute(
                "SELECT * FROM qc_items WHERE case_id = ? AND version = ? AND status != 'superseded' ORDER BY id",
                (case_id, r["version"]))]
        for it in items:
            it["marks"] = json.loads(it["marks"]) if it["marks"] else []
        open_items = [i for i in items if i["status"] == "open"]
        qc_pending = r["qc_version"] != r["version"]
        to_dictate = blanks(r["technique"], r["findings"], r["impression"])
        proposal_pending = r.get("proposal") == "pending"
        return {**r, "qc": items, "open_alerts": len(open_items), "qc_pending": qc_pending, "blanks": to_dictate,
                "proposal_pending": proposal_pending,
                "signable": r["status"] == "draft" and not open_items and not qc_pending and not to_dictate
                and not proposal_pending}

    def signed(self) -> dict[str, str]:
        """case_id -> signed_at of every signed report."""
        with self.lock:
            return {r["case_id"]: r["signed_at"] for r in
                    self.db.execute("SELECT case_id, signed_at FROM reports WHERE status = 'signed'")}

    # ---- writing --------------------------------------------------------------------------------------
    def _locked_check(self, case_id: str) -> dict:
        r = self._row(case_id)
        if not r:
            raise ReportError(404, f"No hay borrador para {case_id}")
        if r["status"] == "signed":
            raise ReportError(409, f"El informe de {case_id} está firmado y bloqueado")
        return r

    def _save(self, case_id: str, technique: str, findings: str, impression: str, by: str, version: int) -> None:
        now = _now()
        with self.lock:
            self.db.execute(
                "INSERT INTO reports (case_id, version, technique, findings, impression, status, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 'draft', ?) ON CONFLICT(case_id) DO UPDATE SET version=excluded.version, "
                "technique=excluded.technique, findings=excluded.findings, impression=excluded.impression, "
                "status='draft', updated_at=excluded.updated_at",
                (case_id, version, technique, findings, impression, now))
            self.db.execute("INSERT INTO report_versions VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (case_id, version, technique, findings, impression, now, by))

    async def draft(self, case_id: str, technique: str, findings: str, impression: str, by: str, lang: str,
                    dictated: bool = False) -> dict:
        """`dictated`: the radiologist's literal words (structured dictation), which replace a pending template
        proposal. A draft written by the model never clears a pending proposal: it still needs "de acuerdo"."""
        r = self._row(case_id)
        if r and r["status"] == "signed":
            raise ReportError(409, f"El informe de {case_id} está firmado y bloqueado")
        self._save(case_id, technique.strip(), findings.strip(), impression.strip(), by, (r["version"] + 1) if r else 1)
        if dictated:
            with self.lock:
                self.db.execute("UPDATE reports SET proposal = NULL WHERE case_id = ?", (case_id,))
        await self._qc_after_change(case_id, lang)
        return self.state(case_id)

    async def propose(self, case_id: str, proposal: dict, by: str, lang: str) -> dict:
        """Template proposal ("¿Lo leemos con IA?" → Sí). An existing draft is never overwritten: it is returned."""
        r = self._row(case_id)
        if r and r["status"] == "signed":
            raise ReportError(409, f"El informe de {case_id} está firmado y bloqueado")
        if r:
            return self.state(case_id)
        self._save(case_id, proposal["technique"], proposal["findings"], proposal["impression"], by, 1)
        with self.lock:
            self.db.execute("UPDATE reports SET proposal = 'pending', template = ? WHERE case_id = ?", (proposal["template"], case_id))
        self.store.log("qc", "propose", input={"template": proposal["template"]}, output="propuesta · verificar", case_id=case_id)
        await self._qc_after_change(case_id, lang)
        return self.state(case_id)

    def accept(self, case_id: str, by: str, version: int | None = None) -> dict:
        """The radiologist accepts the proposal ("de acuerdo") for the exact version on screen (the chat command
        passes the current one). Not a signature: signing stays a separate human tap."""
        if not by:
            raise ReportError(403, "Aceptar la propuesta requiere un usuario identificado")
        r = self._locked_check(case_id)
        if version is not None and version != r["version"]:
            raise ReportError(409, "El borrador cambió desde tu revisión; revísalo de nuevo")
        if r.get("proposal") != "pending":
            raise ReportError(409, f"{case_id} no tiene una propuesta pendiente de aceptar")
        left = blanks(r["technique"], r["findings"], r["impression"])
        if left:
            raise ReportError(409, f"Faltan {len(left)} campos por dictar antes de aceptar la propuesta")
        with self.lock:
            cur = self.db.execute("UPDATE reports SET proposal = 'accepted' WHERE case_id = ? AND version = ? AND proposal = 'pending'",
                                  (case_id, r["version"]))
        if cur.rowcount != 1:
            raise ReportError(409, "El borrador cambió; revísalo de nuevo")
        self.store.log("qc", "accept", input={"version": r["version"], "by": by}, output="propuesta aceptada", case_id=case_id)
        return self.state(case_id)

    async def edit(self, case_id: str, section: str, find: str, replace: str, by: str, lang: str) -> tuple[dict, dict]:
        """Applies exactly one replacement in one section; returns (state, diff)."""
        if section not in SECTIONS:
            raise ReportError(400, f"Sección desconocida: {section}")
        r = self._locked_check(case_id)
        text = r[section]
        n = text.count(find) if find else 0
        if n != 1:
            raise ReportError(422, f"El texto a cambiar aparece {n} veces en {section}; indica un fragmento único")
        new = text.replace(find, replace, 1)
        vals = {s: r[s] for s in SECTIONS} | {section: new}
        self._save(case_id, vals["technique"], vals["findings"], vals["impression"], by, r["version"] + 1)
        await self._qc_after_change(case_id, lang)
        return self.state(case_id), {"section": section, "parts": diff_lines(text, new)}

    async def replace_text(self, case_id: str, version: int, sections: dict, by: str, lang: str) -> dict:
        """Human edit from the UI ("Editar texto"): whole sections, guarded by the version the human saw."""
        r = self._locked_check(case_id)
        if version != r["version"]:
            raise ReportError(409, "El borrador cambió; recarga antes de editar")
        vals = {s: (sections.get(s) if isinstance(sections.get(s), str) else r[s]).strip() for s in SECTIONS}
        self._save(case_id, vals["technique"], vals["findings"], vals["impression"], by, r["version"] + 1)
        await self._qc_after_change(case_id, lang)
        return self.state(case_id)

    async def apply_fix(self, case_id: str, item_id: int, by: str, lang: str) -> tuple[dict, dict]:
        r = self._locked_check(case_id)
        with self.lock:
            it = self.db.execute("SELECT * FROM qc_items WHERE id = ? AND case_id = ?", (item_id, case_id)).fetchone()
        if not it or it["version"] != r["version"] or it["status"] != "open":
            raise ReportError(409, "La alerta ya no está vigente")
        if not it["fix_find"] or it["fix_replace"] is None:
            raise ReportError(422, "Esta alerta no tiene corrección automática; edita el texto")
        if r["impression"].count(it["fix_find"]) != 1:
            raise ReportError(422, "La corrección ya no coincide de forma única con la impresión; edita el texto")
        with self.lock:
            self.db.execute("UPDATE qc_items SET status='applied' WHERE id = ? AND status='open'", (item_id,))
        try:
            result = await self.edit(case_id, "impression", it["fix_find"], it["fix_replace"], by, lang)
        except ReportError:
            with self.lock:  # the text did not change: the alert stays open
                self.db.execute("UPDATE qc_items SET status='open' WHERE id = ? AND status='applied'", (item_id,))
            raise
        self.store.log("qc", "apply", input={"item": item_id}, output=it["rule"], case_id=case_id)
        return result

    def dismiss(self, case_id: str, item_id: int, reason: str, by: str) -> dict:
        self._locked_check(case_id)
        reason = (reason or "").strip()
        if len(reason) < 3:
            raise ReportError(422, "Indica el motivo para descartar la alerta")
        with self.lock:
            cur = self.db.execute("UPDATE qc_items SET status='dismissed', reason=? WHERE id = ? AND case_id = ? AND status='open'",
                                  (reason[:300], item_id, case_id))
        if cur.rowcount != 1:
            raise ReportError(409, "La alerta ya no está vigente")
        # the reason is recorded on the alert itself; the activity log keeps no free text
        self.store.log("qc", "dismiss", input={"item": item_id, "by": by}, output="descartada con motivo", case_id=case_id)
        return self.state(case_id)

    def sign(self, case_id: str, version: int, signer: str) -> dict:
        """Called only by the human 'Firmar' button (never exposed as a model tool)."""
        if not signer:
            raise ReportError(403, "La firma requiere un usuario identificado")
        r = self._locked_check(case_id)
        st = self.state(case_id)
        if version != r["version"]:
            raise ReportError(409, "El borrador cambió desde tu revisión; revísalo de nuevo")
        if st["qc_pending"]:
            raise ReportError(409, "Firma pendiente: RAD·QC aún revisa esta versión")
        if st["open_alerts"]:
            raise ReportError(409, "Firma pendiente de tu revisión: hay alertas de QC sin resolver")
        if st["blanks"]:
            raise ReportError(409, "Firma pendiente: faltan campos por dictar")
        if st["proposal_pending"]:
            raise ReportError(409, "Firma pendiente: la propuesta aún no está aceptada («de acuerdo»)")
        now = _now()
        with self.lock:
            # one atomic decision: right version, still a draft, QC finished for it, and no open alert
            cur = self.db.execute(
                "UPDATE reports SET status='signed', signed_by=?, signed_at=? "
                "WHERE case_id = ? AND version = ? AND qc_version = version AND status = 'draft' "
                "AND COALESCE(proposal, '') != 'pending' "
                "AND NOT EXISTS (SELECT 1 FROM qc_items q WHERE q.case_id = reports.case_id "
                "AND q.version = reports.version AND q.status = 'open')",
                (signer, now, case_id, version))
        if cur.rowcount != 1:
            raise ReportError(409, "El borrador cambió desde tu revisión; revísalo de nuevo")
        self.store.log("sign", "sign", input={"version": version}, output=f"firmado por {signer}", case_id=case_id)
        return self.state(case_id)

    # ---- QC -------------------------------------------------------------------------------------------
    async def run_qc(self, case_id: str, lang: str, indication: str = "") -> dict:
        r = self._row(case_id)
        if r["status"] != "draft":
            return self.state(case_id)
        with self.lock:  # QC running: this version is not signable until it finishes (even on a re-run)
            self.db.execute("UPDATE reports SET qc_version = NULL WHERE case_id = ? AND version = ?", (case_id, r["version"]))
        indication = indication or self.indication_for(case_id, lang) or ""
        issues = qc.rule_issues(r["findings"], r["impression"])
        mode = "rules"
        if self.qc_ctx:
            # whole QC budget across providers, below the app proxy's 60 s for report actions
            deadline = time.monotonic() + self.qc_ctx.budget
            for p in self.qc_ctx.providers:
                left = min(self.qc_ctx.timeout, deadline - time.monotonic())
                if left < 3:
                    break
                try:
                    msg = await self.qc_ctx.llm.complete(p, qc.qc_messages(lang, indication, r["findings"], r["impression"]),
                                                         None, left, max_tokens=1200)
                    log_usage(self.store, p, msg.get("_usage") if isinstance(msg, dict) else None, "qc")
                    issues = qc.merge(issues, qc.parse_model_issues(msg.get("content") if isinstance(msg, dict) else None,
                                                                    indication, r["findings"], r["impression"]))
                    mode = p.mode  # agent (Glimmer) | fallback
                    break
                except ProviderError as e:
                    self.store.log("llm", "qc_unavailable", output=str(e), model=p.label, mode=p.mode, ok=False)
        st = self._store_issues(case_id, r["version"], issues, mode)
        if st.get("stale"):
            self.store.log("qc", "qc_check", input={"version": r["version"]}, case_id=case_id, mode=mode,
                           output="resultado descartado: la versión ya cambió")
            return self.state(case_id)
        self.store.log("qc", "qc_check", input={"version": r["version"]}, case_id=case_id, mode=mode,
                       output=f"{st['open_alerts']} alertas abiertas ({mode})")
        return st

    async def _qc_after_change(self, case_id: str, lang: str) -> None:
        if not (self.background_qc and self.qc_ctx and self.qc_ctx.providers):
            await self.run_qc(case_id, lang)
            return
        r = self._row(case_id)
        # rules now (proven measure / laterality conflicts), without completing QC for this version
        self._store_issues(case_id, r["version"], qc.rule_issues(r["findings"], r["impression"]), "rules", final=False)
        if self._qc_running.get(case_id):
            self._qc_again.add(case_id)  # the running check will run once more, on the latest version
            return
        self._qc_running[case_id] = True
        task = asyncio.get_running_loop().create_task(self._background_qc(case_id, lang))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _background_qc(self, case_id: str, lang: str) -> None:
        try:
            while True:
                self._qc_again.discard(case_id)
                try:
                    async with self._qc_slots:
                        await self.run_qc(case_id, lang)
                except Exception as e:  # never lost: the version stays unsigned and "revisa" re-runs it
                    self.store.log("qc", "qc_check", output=f"QC en segundo plano falló: {type(e).__name__}", case_id=case_id, ok=False)
                if case_id not in self._qc_again:
                    break
        finally:
            self._qc_running[case_id] = False

    def _store_issues(self, case_id: str, version: int, issues: list, mode: str, final: bool = True) -> dict:
        """Replaces the open alerts of a case; an issue the radiologist already dismissed stays dismissed.
        Results for a version that is no longer current are discarded (a slow QC must not clear newer alerts)."""
        with self.lock:
            cur = self.db.execute("SELECT version, status FROM reports WHERE case_id = ?", (case_id,)).fetchone()
            if not cur or cur["version"] != version or cur["status"] != "draft":
                return self.state_unlocked(case_id)
            dismissed = {(d["rule"], (d["body_excerpt"] or "").strip(), (d["impression_excerpt"] or "").strip()): d["reason"]
                         for d in self.db.execute("SELECT * FROM qc_items WHERE case_id = ? AND status='dismissed'", (case_id,))}
            # each run replaces the whole current set; dismissals carry over (with their reason) to the new rows
            self.db.execute("UPDATE qc_items SET status='superseded' WHERE case_id = ? AND status IN ('open', 'dismissed')", (case_id,))
            now = _now()
            for i in issues:
                prior = dismissed.get(i.key())
                self.db.execute(
                    "INSERT INTO qc_items (case_id, version, rule, severity, source, body_label, body_excerpt, impression_excerpt, "
                    "explanation, fix_find, fix_replace, marks, status, reason, at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (case_id, version, i.rule, i.severity, i.source, i.body_label, i.body_excerpt, i.impression_excerpt,
                     i.explanation, i.fix_find, i.fix_replace, json.dumps(i.marks or [], ensure_ascii=False),
                     "dismissed" if prior else "open", prior, now))
            if final:
                self.db.execute("UPDATE reports SET qc_mode = ?, qc_version = ? WHERE case_id = ?", (mode, version, case_id))
            else:  # partial (rules only): QC of this version is still running
                self.db.execute("UPDATE reports SET qc_mode = ?, qc_version = NULL WHERE case_id = ?", (mode, case_id))
        return self.state(case_id)

    def state_unlocked(self, case_id: str) -> dict:
        """state() for callers that already hold the lock (re-entrancy-free copy)."""
        r = self.db.execute("SELECT * FROM reports WHERE case_id = ?", (case_id,)).fetchone()
        return {"case_id": case_id, "stale": True, "version": r["version"] if r else None}

    # ---- demo seed ------------------------------------------------------------------------------------
    def seed(self, path: str | Path) -> int:
        """Loads synthetic draft reports once (existing drafts or signed reports are never overwritten)."""
        data = json.loads(Path(path).read_text())
        if data.get("synthetic") is not True:
            raise ValueError("seed reports must be marked synthetic")
        n = 0
        for rep in data["reports"]:
            if not self._row(rep["case_id"]):
                self._save(rep["case_id"], rep["technique"], rep["findings"], rep["impression"], "seed", 1)
                # proven (rule) alerts right away; the model layer runs on the next QC
                self._store_issues(rep["case_id"], 1, qc.rule_issues(rep["findings"], rep["impression"]), "seed")
                n += 1
        return n

    def reset_demo(self, path: str | Path) -> None:
        """Demo only: wipe all reports and reload the synthetic seed (guarded by the caller)."""
        with self.lock:
            for t in ("reports", "report_versions", "qc_items"):
                self.db.execute(f"DELETE FROM {t}")
        self.seed(path)
