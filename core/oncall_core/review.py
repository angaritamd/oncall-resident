"""Turn review (review_all): an agentic, verifiable loop over the shift's pending studies.

For each study (in `list_pending` order, fixed in code) the checklist is fixed in
code, RAD·QC (`Reports.run_qc`) runs in code before the model loop, findings are
only recorded with literal quotes, and the run closes with a verdict. It never
edits, signs, or sends anything.

Persistence: `review_runs` + `review_studies` (resumable; one active run at a time).
The run itself advances in a background asyncio task so no request waits on it.
"""
import asyncio
import json
import time
import uuid
from datetime import datetime, timezone

from .i18n import t
from .intents import _norm
from .llm import ProviderError, log_usage

SCHEMA = """
CREATE TABLE IF NOT EXISTS review_runs (
  id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT,
  status TEXT NOT NULL,             -- 'running' | 'paused' | 'done' | 'failed'
  lang TEXT NOT NULL, by TEXT, model TEXT
);
CREATE TABLE IF NOT EXISTS review_studies (
  run_id TEXT NOT NULL, case_id TEXT NOT NULL, position INTEGER NOT NULL,
  status TEXT NOT NULL,             -- 'pending' | 'done' | 'skipped' | 'error'
  checklist TEXT NOT NULL,          -- JSON list of items, e.g. ["C1","C3","C4"]
  findings TEXT NOT NULL,           -- JSON list of accepted findings
  verdict TEXT, note TEXT, mode TEXT, steps INTEGER NOT NULL DEFAULT 0, at TEXT NOT NULL,
  UNIQUE (run_id, case_id)
);
"""

SECTIONS = ("indication", "tech_note", "findings", "impression")
CLOSE_VERDICTS = ("ok", "revisar", "critico_sin_respuesta")
CODE_VERDICTS = ("sin_borrador", "no_evaluado")
MAX_STEPS = 4
MIN_CALL_S = 3.0

# mode -> short UI label key (i18n review.mode.*). "agent" is the primary model.
MODE_LABEL_KEY = {"agent": "review.mode.agent", "fallback": "review.mode.fallback", "rules": "review.mode.rules"}


class ReviewError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code, self.message = code, message


LOOP_TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "qc_check",
            "description": "Return the RAD·QC alerts already computed in code for this study. Read-only; never re-runs QC.",
            "parameters": {"type": "object", "properties": {"case_id": {"type": "string"}},
                           "required": ["case_id"], "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_finding",
            "description": "Record one checklist finding with a literal quote from the named section. "
                           "Rejected when the item is not in this study's checklist or the quote is not "
                           "literally in that section.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "item": {"type": "string", "description": "Checklist item, e.g. C2, C3, C5"},
                    "section": {"type": "string", "enum": ["indication", "tech_note", "findings", "impression"]},
                    "quote": {"type": "string", "description": "Exact fragment of that section"},
                    "claim": {"type": "string", "description": "One sentence: what the quote shows"},
                },
                "required": ["case_id", "item", "section", "quote", "claim"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_study",
            "description": "Close this study with a verdict. Rejected while C4 alerts are open without a C5 "
                           "finding or an explicit no-counter-evidence note.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "verdict": {"type": "string", "enum": ["ok", "revisar", "critico_sin_respuesta"]},
                    "note": {"type": "string", "description": "One line for the radiologist"},
                },
                "required": ["case_id", "verdict"],
                "additionalProperties": False,
            },
        },
    },
]
LOOP_TOOL_NAMES = {s["function"]["name"] for s in LOOP_TOOL_SPECS}

SYSTEM = {
    "es": "Eres el revisor del turno. Para este estudio el checklist y el resultado de RAD·QC ya están fijados; "
          "tú solo aportas juicio con citas literales. Usa qc_check para ver las alertas, record_finding por cada "
          "conclusión (item del checklist, sección exacta, cita copiada carácter por carácter, una frase), y "
          "close_study con el veredicto: ok (todo responde, sin alertas), revisar (hay alertas o dudas), "
          "critico_sin_respuesta (marca crítica del tecnólogo y la IMPRESIÓN no responde a su sospecha). "
          "Si hay alertas abiertas de C4, antes de cerrar deja un record_finding con item C5 por cada alerta "
          "(la cita que la contradice) o escribe en note que no hay contra-evidencia. Nunca inventes citas.",
    "en": "You are the shift reviewer. This study's checklist and RAD·QC result are already fixed; you only add "
          "judgement with literal quotes. Use qc_check to see the alerts, record_finding for each conclusion "
          "(checklist item, exact section, quote copied character for character, one sentence), and close_study "
          "with the verdict: ok (everything answered, no alerts), revisar (alerts or doubts), "
          "critico_sin_respuesta (technologist critical flag and the IMPRESSION does not answer the suspicion). "
          "With open C4 alerts, leave a record_finding with item C5 per alert (the contradicting quote) before "
          "closing, or state in note that there is no counter-evidence. Never invent quotes.",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tag(text: str) -> str:
    return f"<<<{text or ''}>>>"


def _no_counter_evidence(note: str) -> bool:
    n = _norm(note or "")
    return "contraevidencia" in n.replace("-", "").replace(" ", "") or "counter" in n


def rank_key(study: dict) -> tuple:
    """Display order: critico_sin_respuesta and critical sin_borrador first, then
    revisar, no_evaluado, ok; study position as the tiebreak."""
    v = study.get("verdict")
    critical = "C2" in (study.get("checklist") or [])
    if v == "critico_sin_respuesta" or (v == "sin_borrador" and critical):
        group = 0
    elif v == "revisar":
        group = 1
    elif v == "no_evaluado":
        group = 2
    else:
        group = 3
    return (group, study.get("position", 0))


class Review:
    """Persisted review runs plus the background loop. Wiring (service, reports,
    llm, providers, order metadata) is injected so tests can use fakes."""

    def __init__(self, store, service, reports, llm, providers, by_case: dict,
                 run_budget_s: float = 600.0, study_budget_s: float = 120.0, call_timeout_s: float = 40.0):
        self.store, self.db, self.lock = store, store._db, store._lock
        self.service, self.reports, self.llm = service, reports, llm
        self.providers = providers or []
        self.by_case = by_case
        self.run_budget_s, self.study_budget_s, self.call_timeout_s = run_budget_s, study_budget_s, call_timeout_s
        with self.lock:
            self.db.executescript(SCHEMA)
            # a restart must never leave a run stuck "running": it becomes resumable
            self.db.execute("UPDATE review_runs SET status = 'paused' WHERE status = 'running'")

    # ---- persistence ----------------------------------------------------------------------------
    def active(self) -> dict | None:
        with self.lock:
            r = self.db.execute("SELECT * FROM review_runs WHERE status IN ('running', 'paused') "
                                "ORDER BY started_at DESC LIMIT 1").fetchone()
        return dict(r) if r else None

    def _insert_studies(self, run_id: str, case_ids: list[str]) -> None:
        now = _now()
        with self.lock:
            for pos, cid in enumerate(case_ids, 1):
                self.db.execute(
                    "INSERT OR IGNORE INTO review_studies (run_id, case_id, position, status, checklist, findings, steps, at)"
                    " VALUES (?, ?, ?, 'pending', '[]', '[]', 0, ?)", (run_id, cid, pos, now))

    async def start(self, lang: str, by: str | None) -> dict:
        """Create a run over the current pending order. Raises ReviewError(409) while one is active."""
        if self.active():
            raise ReviewError(409, t(lang, "review.active"))
        try:
            items, _ = await self.service.worklist()
        except Exception:
            raise ReviewError(503, t(lang, "pacs.down"))
        run_id = "RV-" + uuid.uuid4().hex[:8]
        with self.lock:
            self.db.execute("INSERT INTO review_runs (id, started_at, status, lang, by) VALUES (?, ?, 'running', ?, ?)",
                            (run_id, _now(), lang, by))
        self._insert_studies(run_id, [i.case_id for i in items])
        if not items:
            with self.lock:
                self.db.execute("UPDATE review_runs SET status = 'done', finished_at = ? WHERE id = ?", (_now(), run_id))
        self.store.log("review", "review_start", input={"run_id": run_id}, mode="command",
                       output=t(lang, "review.started", n=len(items)))
        return self.get(run_id)

    def mark_running(self, run_id: str, lang: str) -> None:
        with self.lock:
            cur = self.db.execute("UPDATE review_runs SET status = 'running' WHERE id = ? AND status = 'paused'",
                                  (run_id,))
        if cur.rowcount != 1:
            raise ReviewError(409, t(lang, "review.not_paused", run=run_id))

    def reset(self) -> None:
        with self.lock:
            self.db.execute("DELETE FROM review_studies")
            self.db.execute("DELETE FROM review_runs")

    def _studies(self, run_id: str) -> list[dict]:
        with self.lock:
            rows = self.db.execute("SELECT * FROM review_studies WHERE run_id = ? ORDER BY position", (run_id,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["checklist"] = json.loads(d["checklist"] or "[]")
            d["findings"] = json.loads(d["findings"] or "[]")
            out.append(d)
        return out

    def get(self, run_id: str) -> dict:
        with self.lock:
            r = self.db.execute("SELECT * FROM review_runs WHERE id = ?", (run_id,)).fetchone()
        if not r:
            raise ReviewError(404, run_id)
        run = dict(r)
        studies = self._studies(run_id)
        for s in studies:
            s["mode_label"] = t(run["lang"], MODE_LABEL_KEY[s["mode"]]) if s.get("mode") in MODE_LABEL_KEY else None
            meta = self.by_case.get(s["case_id"])
            s["exam"] = meta.exam[run["lang"]] if meta and meta.exam else None
            s["critical"] = "C2" in s["checklist"]
            # per-item resolution (language-independent codes): "registrado" (accepted with a
            # literal quote), "evaluado" (C4 always runs in code), "no_evaluado" (rules fallback),
            # "sin_registro" (model closed without a finding for it), "pendiente" (still running)
            items = {}
            terminal = s["status"] != "pending"
            if s["status"] == "skipped":
                # C1 ("is there a draft?") was answered in code: there is none
                items = {"C1": "evaluado"}
                if "C2" in s["checklist"]:
                    items["C2"] = "no_evaluado"
                s["items"] = items
                continue
            for item in s["checklist"]:
                if any(f["item"] == item for f in s["findings"]):
                    items[item] = "registrado"
                elif item == "C4" and terminal:
                    items[item] = "evaluado"
                elif terminal and (s.get("mode") or "rules") == "rules":
                    items[item] = "no_evaluado"
                elif terminal:
                    items[item] = "sin_registro"
                else:
                    items[item] = "pendiente"
            s["items"] = items
        ordered = sorted([s for s in studies if s["status"] != "pending"], key=rank_key)
        ordered += [s for s in studies if s["status"] == "pending"]
        done = sum(1 for s in studies if s["status"] in ("done", "skipped", "error"))
        return {"run_id": run_id, "status": run["status"], "lang": run["lang"],
                "progress": {"done": done, "total": len(studies)},
                "finished_at": run["finished_at"], "studies": ordered}

    # ---- background loop --------------------------------------------------------------------------
    def _run_row(self, run_id: str) -> dict | None:
        with self.lock:
            r = self.db.execute("SELECT * FROM review_runs WHERE id = ?", (run_id,)).fetchone()
        return dict(r) if r else None

    def _run_over_budget(self, run: dict) -> bool:
        try:
            start = datetime.fromisoformat(run["started_at"])
        except (ValueError, TypeError):
            return False
        return (datetime.now(timezone.utc) - start).total_seconds() > self.run_budget_s

    def _save_study(self, run_id: str, case_id: str, status: str, checklist: list, findings: list,
                    verdict: str | None, note: str | None, mode: str, steps: int) -> None:
        with self.lock:
            self.db.execute(
                "UPDATE review_studies SET status = ?, checklist = ?, findings = ?, verdict = ?, note = ?, mode = ?,"
                " steps = ?, at = ? WHERE run_id = ? AND case_id = ?",
                (status, json.dumps(checklist, ensure_ascii=False), json.dumps(findings, ensure_ascii=False),
                 verdict, (note or "")[:500] or None, mode, steps, _now(), run_id, case_id))

    def _finish(self, run_id: str, status: str) -> None:
        with self.lock:
            self.db.execute("UPDATE review_runs SET status = ?, finished_at = ? WHERE id = ?",
                            (status, _now() if status in ("done", "failed") else None, run_id))

    async def advance(self, run_id: str) -> dict:
        """Review every non-terminal study; called in a background task. Never raises."""
        try:
            run = self._run_row(run_id)
            if not run or run["status"] != "running":
                return self.get(run_id)
            for s in self._studies(run_id):
                run = self._run_row(run_id)
                if not run or run["status"] != "running":
                    break
                if s["status"] != "pending":
                    continue
                if self._run_over_budget(run):
                    self._finish(run_id, "paused")
                    self.store.log("review", "review_paused", input={"run_id": run_id}, mode="command",
                                   output=t(run["lang"], "review.paused"))
                    break
                await self._review_one(run, s)
            run = self._run_row(run_id)
            if run and run["status"] == "running":
                left = [x for x in self._studies(run_id) if x["status"] == "pending"]
                self._finish(run_id, "done" if not left else "paused")
                self.store.log("review", "review_done" if not left else "review_paused", input={"run_id": run_id},
                               mode="command", output=t(run["lang"], "review.done" if not left else "review.paused"))
            return self.get(run_id)
        except Exception as e:  # a study error must never kill the run silently: mark and continue pattern
            try:
                self._finish(run_id, "failed")
                self.store.log("review", "review_failed", input={"run_id": run_id}, mode="command",
                               output=str(e)[:200], ok=False)
            except Exception:
                pass
            try:
                return self.get(run_id)
            except ReviewError:
                return {"run_id": run_id, "status": "failed"}

    # ---- one study ----------------------------------------------------------------------------------
    def _sections(self, case_id: str, lang: str) -> tuple[dict, dict | None]:
        meta = self.by_case.get(case_id)
        st = self.reports.state(case_id)
        texts = {
            "indication": (meta.reason.get(lang, "") if meta and meta.reason else ""),
            "tech_note": (meta.tech_note.get(lang, "") if meta and meta.tech_note else ""),
            "findings": (st["findings"] if st else ""),
            "impression": (st["impression"] if st else ""),
        }
        return texts, st

    async def _review_one(self, run: dict, s: dict) -> None:
        run_id, case_id, lang = run["id"], s["case_id"], run["lang"]
        texts, st = self._sections(case_id, lang)
        if not st:
            meta = self.by_case.get(case_id)
            checklist = ["C1"] + (["C2"] if meta and meta.tech_critical else [])
            self._save_study(run_id, case_id, "skipped", checklist, [], "sin_borrador",
                             t(lang, "review.no_draft", case=case_id), "rules", 0)
            self.store.log("review", "close_study", input={"run_id": run_id, "verdict": "sin_borrador"},
                           output=t(lang, "review.no_draft", case=case_id), case_id=case_id, mode="rules")
            return
        # C4 runs in code, before the model loop; qc_check inside the loop only replays it
        try:
            st = await self.reports.run_qc(case_id, lang)
        except Exception as e:
            self._save_study(run_id, case_id, "error", ["C1", "C3", "C4"], [], None, str(e)[:200], "rules", 0)
            self.store.log("review", "qc_check", input={"run_id": run_id, "case_id": case_id},
                           output=str(e)[:200], case_id=case_id, mode="rules", ok=False)
            return
        open_alerts = [i for i in st["qc"] if i["status"] == "open"]
        meta = self.by_case.get(case_id)
        checklist = ["C1"] + (["C2"] if meta and meta.tech_critical else []) + ["C3", "C4"] + (["C5"] if open_alerts else [])
        texts, _ = self._sections(case_id, lang)
        qc_cached = {"open_alerts": len(open_alerts),
                     "alerts": [{"type": i["rule"], "severity": i["severity"],
                                 "findings_or_indication": i["body_excerpt"], "impression": i["impression_excerpt"]}
                                for i in open_alerts]}
        findings: list[dict] = []
        state = {"closed": None, "steps": 0, "mode": None}
        if self.providers:
            try:
                await self._model_loop(run, case_id, lang, checklist, texts, qc_cached, findings, state)
            except Exception as e:
                self.store.log("review", "review_study_error", input={"run_id": run_id, "case_id": case_id},
                               output=str(e)[:200], case_id=case_id, mode="rules", ok=False)
        if state["closed"] is None:
            # rules fallback: no model answer or study budget spent — never an invented verdict
            verdict = "revisar" if open_alerts else "no_evaluado"
            self._save_study(run_id, case_id, "done", checklist, findings, verdict,
                             t(lang, "review.not_evaluated"), "rules", state["steps"])
            self.store.log("review", "close_study", input={"run_id": run_id, "verdict": verdict},
                           output=t(lang, "review.not_evaluated"), case_id=case_id, mode="rules")

    def _study_messages(self, lang: str, case_id: str, checklist: list, texts: dict, qc_cached: dict) -> list[dict]:
        meta = self.by_case.get(case_id)
        exam = meta.exam.get(lang, "") if meta and meta.exam else ""
        doc = (f"Caso {case_id} ({exam}). Checklist: {', '.join(checklist)}. "
               f"Alertas C4 abiertas: {qc_cached['open_alerts']}.\n"
               f"INDICACIÓN:\n{_tag(texts['indication'])}\n\nNOTA DEL TECNÓLOGO:\n{_tag(texts['tech_note'])}\n\n"
               f"HALLAZGOS:\n{_tag(texts['findings'])}\n\nIMPRESIÓN:\n{_tag(texts['impression'])}")
        return [{"role": "system", "content": SYSTEM[lang]}, {"role": "user", "content": doc}]

    async def _model_loop(self, run: dict, case_id: str, lang: str, checklist: list, texts: dict,
                          qc_cached: dict, findings: list, state: dict) -> None:
        run_id = run["id"]
        messages = self._study_messages(lang, case_id, checklist, texts, qc_cached)
        deadline = time.monotonic() + self.study_budget_s
        for _ in range(MAX_STEPS):
            if state["closed"] is not None:
                return
            left = min(self.call_timeout_s, deadline - time.monotonic())
            if left < MIN_CALL_S:
                return  # study budget spent: caller applies the rules fallback
            msg = await self._complete_any(messages, run_id, case_id, lang, left, state)
            if msg is None:
                return  # every provider down: rules fallback
            calls = msg.get("tool_calls") or []
            if not calls:
                return  # model abstained: rules fallback rather than an invented close
            messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
            for call in calls:
                name = call.get("function", {}).get("name", "")
                raw = call.get("function", {}).get("arguments") or "{}"
                try:
                    args = raw if isinstance(raw, dict) else json.loads(raw) if isinstance(raw, str) else {}
                except ValueError:
                    args = {}
                if not isinstance(args, dict):
                    args = {}
                args = {**args, "case_id": case_id}
                if name == "qc_check":
                    result = self._tool_qc(run_id, case_id, lang, state, qc_cached)
                elif name == "record_finding":
                    result = self._tool_record(run_id, case_id, lang, state, checklist, texts, findings, args)
                elif name == "close_study":
                    result = self._tool_close(run, case_id, lang, state, checklist, findings, qc_cached, args)
                else:
                    self.store.log("review", name or "unknown_tool", input={"run_id": run_id},
                                   output="unknown tool", case_id=case_id, model=state.get("model"),
                                   mode=state.get("mode"), ok=False)
                    result = {"error": f"unknown tool {name}"}
                    state["steps"] += 1
                messages.append({"role": "tool", "tool_call_id": call.get("id", name),
                                 "content": json.dumps(result, ensure_ascii=False)})
                if state["closed"] is not None:
                    return

    async def _complete_any(self, messages: list, run_id: str, case_id: str, lang: str,
                            timeout: float, state: dict) -> dict | None:
        for p in self.providers:
            try:
                msg = await self.llm.complete(p, messages, LOOP_TOOL_SPECS, timeout)
            except ProviderError as e:
                self.store.log("chat", "provider_unavailable", input={"run_id": run_id}, output=str(e),
                               case_id=case_id, model=p.label, mode=p.mode, ok=False)
                continue
            if not isinstance(msg, dict):
                continue
            log_usage(self.store, p, msg.get("_usage"), "review")
            state["mode"], state["model"] = p.mode, p.label
            with self.lock:
                self.db.execute("UPDATE review_runs SET model = ? WHERE id = ?", (p.label, run_id))
            return msg
        self.store.log("review", "providers_down", input={"run_id": run_id}, case_id=case_id,
                       output=t(lang, "review.not_evaluated"), ok=False)
        return None

    # ---- loop tools (executed in code, never by the model) --------------------------------------------------
    def _tool_qc(self, run_id: str, case_id: str, lang: str, state: dict, qc_cached: dict) -> dict:
        """Replay the C4 result computed in code; it never re-runs QC or calls the model."""
        state["steps"] += 1
        self.store.log("review", "qc_check", input={"run_id": run_id, "case_id": case_id},
                       output=t(lang, "report.qc", case=case_id, n=qc_cached["open_alerts"]),
                       case_id=case_id, model=state.get("model"), mode=state.get("mode"))
        return {"case_id": case_id, **qc_cached}

    def _tool_record(self, run_id: str, case_id: str, lang: str, state: dict, checklist: list,
                     texts: dict, findings: list, args: dict) -> dict:
        item, section = str(args.get("item") or ""), str(args.get("section") or "")
        quote, claim = str(args.get("quote") or ""), str(args.get("claim") or "")[:300]
        ok, reason = True, t(lang, "review.finding_ok")
        if item not in checklist:
            ok, reason = False, t(lang, "review.bad_item", item=item or "—")
        elif section not in SECTIONS:
            ok, reason = False, t(lang, "review.bad_section", section=section or "—")
        elif not quote or quote not in (texts.get(section) or ""):
            ok, reason = False, t(lang, "review.bad_quote", section=section)
        if ok:
            findings.append({"item": item, "section": section, "quote": quote, "claim": claim})
        state["steps"] += 1
        self.store.log("review", "record_finding",
                       input={"run_id": run_id, "case_id": case_id, "item": item, "section": section},
                       output=reason, case_id=case_id, model=state.get("model"), mode=state.get("mode"), ok=ok)
        return {"recorded": ok, "reason": reason} if ok else {"error": reason}

    def _tool_close(self, run: dict, case_id: str, lang: str, state: dict, checklist: list,
                    findings: list, qc_cached: dict, args: dict) -> dict:
        run_id = run["id"]
        verdict, note = str(args.get("verdict") or ""), str(args.get("note") or "")
        if verdict not in CLOSE_VERDICTS:
            reason = t(lang, "review.bad_verdict", verdict=verdict or "—")
            self.store.log("review", "close_study", input={"run_id": run_id, "verdict": verdict},
                           output=reason, case_id=case_id, model=state.get("model"), mode=state.get("mode"), ok=False)
            state["steps"] += 1
            return {"error": reason}
        if qc_cached["open_alerts"] and not any(f["item"] == "C5" for f in findings) \
                and not _no_counter_evidence(note):
            reason = t(lang, "review.close_needs_c5")
            self.store.log("review", "close_study", input={"run_id": run_id, "verdict": verdict},
                           output=reason, case_id=case_id, model=state.get("model"), mode=state.get("mode"), ok=False)
            state["steps"] += 1
            return {"error": reason}
        mode = state.get("mode") or "rules"
        self._save_study(run_id, case_id, "done", checklist, findings, verdict, note or None, mode, state["steps"] + 1)
        state["steps"] += 1
        state["closed"] = {"verdict": verdict, "mode": mode}
        self.store.log("review", "close_study", input={"run_id": run_id, "verdict": verdict},
                       output=verdict, case_id=case_id, model=state.get("model"), mode=mode)
        return {"closed": verdict}
