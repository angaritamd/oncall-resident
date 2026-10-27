"""Draft reports: versions, QC after every change, and human-only signing that locks the report."""
import difflib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import qc
from .llm import LLM, Provider, ProviderError, log_usage
from .store import Store

SECTIONS = ("technique", "findings", "impression")

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
  case_id TEXT PRIMARY KEY, version INTEGER NOT NULL, technique TEXT NOT NULL, findings TEXT NOT NULL,
  impression TEXT NOT NULL, status TEXT NOT NULL, qc_mode TEXT, signed_by TEXT, signed_at TEXT, updated_at TEXT NOT NULL
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
    def __init__(self, store: Store, qc_ctx: QcContext | None = None, indication_for=None):
        self.store, self.db, self.lock = store, store._db, store._lock
        self.qc_ctx = qc_ctx
        self.indication_for = indication_for or (lambda case_id, lang: "")
        with self.lock:
            self.db.executescript(SCHEMA)

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
        return {**r, "qc": items, "open_alerts": len(open_items),
                "signable": r["status"] == "draft" and not open_items}

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

    async def draft(self, case_id: str, technique: str, findings: str, impression: str, by: str, lang: str) -> dict:
        r = self._row(case_id)
        if r and r["status"] == "signed":
            raise ReportError(409, f"El informe de {case_id} está firmado y bloqueado")
        self._save(case_id, technique.strip(), findings.strip(), impression.strip(), by, (r["version"] + 1) if r else 1)
        await self.run_qc(case_id, lang)
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
        await self.run_qc(case_id, lang)
        return self.state(case_id), {"section": section, "parts": diff_lines(text, new)}

    async def replace_text(self, case_id: str, version: int, sections: dict, by: str, lang: str) -> dict:
        """Human edit from the UI ("Editar texto"): whole sections, guarded by the version the human saw."""
        r = self._locked_check(case_id)
        if version != r["version"]:
            raise ReportError(409, "El borrador cambió; recarga antes de editar")
        vals = {s: (sections.get(s) if isinstance(sections.get(s), str) else r[s]).strip() for s in SECTIONS}
        self._save(case_id, vals["technique"], vals["findings"], vals["impression"], by, r["version"] + 1)
        await self.run_qc(case_id, lang)
        return self.state(case_id)

    async def apply_fix(self, case_id: str, item_id: int, by: str, lang: str) -> tuple[dict, dict]:
        r = self._locked_check(case_id)
        with self.lock:
            it = self.db.execute("SELECT * FROM qc_items WHERE id = ? AND case_id = ?", (item_id, case_id)).fetchone()
        if not it or it["version"] != r["version"] or it["status"] != "open":
            raise ReportError(409, "La alerta ya no está vigente")
        if not it["fix_find"] or it["fix_replace"] is None:
            raise ReportError(422, "Esta alerta no tiene corrección automática; edita el texto")
        with self.lock:
            self.db.execute("UPDATE qc_items SET status='applied' WHERE id = ?", (item_id,))
        self.store.log("qc", "apply", input={"item": item_id}, output=it["rule"], case_id=case_id)
        return await self.edit(case_id, "impression", it["fix_find"], it["fix_replace"], by, lang)

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
        self.store.log("qc", "dismiss", input={"item": item_id, "reason": reason[:300], "by": by}, output="descartada", case_id=case_id)
        return self.state(case_id)

    def sign(self, case_id: str, version: int, signer: str) -> dict:
        """Called only by the human 'Firmar' button (never exposed as a model tool)."""
        if not signer:
            raise ReportError(403, "La firma requiere un usuario identificado")
        r = self._locked_check(case_id)
        st = self.state(case_id)
        if version != r["version"]:
            raise ReportError(409, "El borrador cambió desde tu revisión; revísalo de nuevo")
        if st["open_alerts"]:
            raise ReportError(409, "Firma pendiente de tu revisión: hay alertas de QC sin resolver")
        now = _now()
        with self.lock:
            self.db.execute("UPDATE reports SET status='signed', signed_by=?, signed_at=? WHERE case_id = ? AND version = ?",
                            (signer, now, case_id, version))
        self.store.log("sign", "sign", input={"version": version}, output=f"firmado por {signer}", case_id=case_id)
        return self.state(case_id)

    # ---- QC -------------------------------------------------------------------------------------------
    async def run_qc(self, case_id: str, lang: str, indication: str = "") -> dict:
        r = self._row(case_id)
        indication = indication or self.indication_for(case_id, lang) or ""
        issues = qc.rule_issues(r["findings"], r["impression"])
        mode = "rules"
        if self.qc_ctx:
            for p in self.qc_ctx.providers:
                try:
                    msg = await self.qc_ctx.llm.complete(p, qc.qc_messages(lang, indication, r["findings"], r["impression"]),
                                                         None, self.qc_ctx.timeout, max_tokens=1200)
                    log_usage(self.store, p, msg.get("_usage") if isinstance(msg, dict) else None, "qc")
                    issues = qc.merge(issues, qc.parse_model_issues(msg.get("content") if isinstance(msg, dict) else None,
                                                                    indication, r["findings"], r["impression"]))
                    mode = p.mode  # agent (Glimmer) | fallback
                    break
                except ProviderError as e:
                    self.store.log("llm", "qc_unavailable", output=str(e), model=p.label, mode=p.mode, ok=False)
        st = self._store_issues(case_id, r["version"], issues, mode)
        self.store.log("qc", "qc_check", input={"version": r["version"]}, case_id=case_id, mode=mode,
                       output=f"{st['open_alerts']} alertas abiertas ({mode})")
        return st

    def _store_issues(self, case_id: str, version: int, issues: list, mode: str) -> dict:
        """Replaces the open alerts of a case; an issue the radiologist already dismissed stays dismissed."""
        with self.lock:
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
            self.db.execute("UPDATE reports SET qc_mode = ? WHERE case_id = ?", (mode, case_id))
        return self.state(case_id)

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
                self._store_issues(rep["case_id"], 1, qc.rule_issues(rep["findings"], rep["impression"]), "rules")
                n += 1
        return n

    def reset_demo(self, path: str | Path) -> None:
        """Demo only: wipe all reports and reload the synthetic seed (guarded by the caller)."""
        with self.lock:
            for t in ("reports", "report_versions", "qc_items"):
                self.db.execute(f"DELETE FROM {t}")
        self.seed(path)
