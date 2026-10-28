"""Typed, read-only tools the resident model may call. Outputs only contain data from the PACS and the
order; every missing value is the literal "Sin dato"/"Unknown" so the model has nothing to fill in."""
import re
from dataclasses import dataclass, field

from .i18n import t
from .reports import ReportError, Reports
from .service import Service
from .views import item_view

TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "list_pending",
            "description": "List the pending studies in reading order. The order is fixed in code (technologist "
                           "critical flag, then order priority STAT > urgent > routine, then longest wait, then study ID); "
                           "you may comment on it but never change it. Signed studies are not listed. Read-only.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_case",
            "description": "Return the facts recorded for one study: exam, sex, age, indication, technologist note, "
                           "critical flag, priority and its source, wait, and priors (declared in the order vs found "
                           "in the PACS). Read-only. Never contains image findings.",
            "parameters": {
                "type": "object",
                "properties": {"case_id": {"type": "string", "description": "Study ID, e.g. DEMO-0001, or a Study Instance UID"}},
                "required": ["case_id"],
                "additionalProperties": False,
            },
        },
    },
]
REPORT_TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "draft_report",
            "description": "Create (or replace) the structured draft report of a study from findings the radiologist "
                           "dictated or confirmed in this conversation. Never invent findings: if the radiologist has "
                           "not given any, do NOT call this tool, ask instead. QC runs automatically afterwards.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "findings": {"type": "string", "description": "FINDINGS, only what the radiologist dictated/confirmed"},
                    "impression": {"type": "string", "description": "IMPRESSION, derived only from those findings"},
                    "technique": {"type": "string", "description": "Optional; defaults to the exam name"},
                },
                "required": ["case_id", "findings", "impression"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_report",
            "description": "Apply exactly ONE change the radiologist asked for: replace one exact fragment in one section. "
                           "Do not propagate the change to other sections (QC will flag inconsistencies). If the radiologist "
                           "does not name a section, use 'findings'. Returns the diff; QC runs automatically afterwards.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "section": {"type": "string", "enum": ["technique", "findings", "impression"]},
                    "find": {"type": "string", "description": "Exact fragment currently in that section (must appear once)"},
                    "replace": {"type": "string"},
                },
                "required": ["case_id", "section", "find", "replace"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "qc_check",
            "description": "Run RAD·QC (mechanical errors) on the current draft and return the alerts. Never edits the report.",
            "parameters": {"type": "object", "properties": {"case_id": {"type": "string"}}, "required": ["case_id"],
                           "additionalProperties": False},
        },
    },
]
PENDING_TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "add_pending_item",
            "description": "Add a pending item to a study when the radiologist asks for it (e.g. 'pídele previos'). "
                           "Kinds: repeat_series, late_phase (delayed images / new injection), missing_priors, "
                           "second_review (tomorrow). Nothing is sent to anyone; it is the radiologist's list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "kind": {"type": "string", "enum": ["repeat_series", "late_phase", "missing_priors", "second_review"]},
                    "note": {"type": "string", "description": "Optional short note in the radiologist's words"},
                },
                "required": ["case_id", "kind"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_pending_items",
            "description": "List the open pending items of every study (what is left for tomorrow). Read-only.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
]
TOOL_SPECS = TOOL_SPECS + REPORT_TOOL_SPECS + PENDING_TOOL_SPECS
TOOL_NAMES = {s["function"]["name"] for s in TOOL_SPECS}
# sign_report is deliberately not a tool: only the human "Firmar" button can sign (POST /api/reports/{id}/sign).


@dataclass
class ToolResult:
    data: dict                      # what the model sees (JSON)
    summary: str                    # one line for the activity log
    case_id: str | None = None
    blocks: list[dict] = field(default_factory=list)  # cards for the UI, built from the same data
    ok: bool = True


FREE_TEXT_MAX = 400


REPORT_TEXT_MAX = 8000
TRUNCATED = " [truncado]"


def untrusted(text, limit: int = FREE_TEXT_MAX):
    """Free text written by people (order, technologist, dictation) is data for the model, never instructions.
    A cut is marked, never silent."""
    if not isinstance(text, str):
        return text
    clean = "".join(ch for ch in text if ch.isprintable() or ch == " ")
    clean = re.sub(r"<{3,}|>{3,}", "", clean)  # the text cannot open or close the delimiter
    if len(clean) > limit:
        clean = clean[:limit] + TRUNCATED
    return f"<<<{clean}>>>"


# Arguments kept in the activity log: report free text (findings, impression, find/replace) stays in the
# report itself, never in the log.
LOGGED_ARGS = {"list_pending": (), "summarize_case": ("case_id",), "draft_report": ("case_id",),
               "edit_report": ("case_id", "section"), "qc_check": ("case_id",), "add_pending_item": ("case_id", "kind"),
               "list_pending_items": ()}
SAFE_VALUE = re.compile(r"[A-Za-z0-9._:-]{1,64}")
DECLARED_ARGS = {spec["function"]["name"]: set(spec["function"]["parameters"].get("properties", {}))
                 for spec in TOOL_SPECS}


def loggable_args(name: str, args: dict) -> dict:
    """Deny by default: only listed, short, plain identifiers are kept; anything else (free text, unknown or
    invented tools) is reduced to its argument names and lengths."""
    keep = LOGGED_ARGS.get(name, ("case_id",))
    declared = DECLARED_ARGS.get(name, set())
    out = {k: str(args[k]) for k in keep if k in args and SAFE_VALUE.fullmatch(str(args[k]))}
    # lengths only for the tool's own declared argument names; any other key (model-chosen text) is just counted
    out |= {f"{k}_chars": len(str(v)) for k, v in args.items() if k not in out and k in declared}
    extra = sum(1 for k in args if k not in out and k not in declared)
    if extra:
        out["extra_args"] = extra
    return out


def report_for_model(st: dict) -> dict:
    u = lambda x: untrusted(x, REPORT_TEXT_MAX) if x else x
    return {
        "case_id": st["case_id"], "version": st["version"], "status": st["status"],
        "technique": u(st["technique"]), "findings": u(st["findings"]), "impression": u(st["impression"]),
        "qc_open_alerts": [
            {"type": i["rule"], "severity": i["severity"], "findings_or_indication": u(i["body_excerpt"]),
             "impression": u(i["impression_excerpt"])}
            for i in st["qc"] if i["status"] == "open"
        ],
        "qc_pending": st.get("qc_pending", False),
        "signing": "Only the radiologist can sign, by tapping 'Firmar'. You cannot sign.",
    }


class Toolbox:
    def __init__(self, service: Service, lang: str, reports: Reports | None = None, by: str = "residente",
                 pending=None, pending_list=None):
        self.service, self.lang, self.reports, self.by = service, lang, reports, by
        # pending items: the store and an async lister (derives metadata items, labels in `lang`)
        self.pending, self.pending_list = pending, pending_list
        self.none = t(lang, "none")

    def _v(self, value):
        return self.none if value is None or value == "" else value

    async def call(self, name: str, args: dict) -> ToolResult:
        if name == "list_pending":
            return await self.list_pending()
        if name == "summarize_case":
            return await self.summarize_case(str(args.get("case_id", "")))
        if name == "add_pending_item" and self.pending is not None:
            return await self.add_pending_item(args)
        if name == "list_pending_items" and self.pending_list is not None:
            items = await self.pending_list()
            data = {"items": [{"case_id": i["case_id"], "kind": i["label"], "source": i["source_label"],
                               "note": untrusted(i["note"]) if i["note"] else self.none} for i in items],
                    "sent_to_anyone": False}
            return ToolResult(data, t(self.lang, "tool.pending_summary", n=len(items)), None,
                              [{"type": "pending_list", "items": items}])
        if name in ("draft_report", "edit_report", "qc_check") and self.reports is not None:
            try:
                return await getattr(self, name)(args)
            except ReportError as e:
                return ToolResult({"error": e.message}, e.message, str(args.get("case_id") or "") or None, ok=False)
        return ToolResult({"error": f"unknown tool {name}"}, f"unknown tool {name}", ok=False)

    async def list_pending(self) -> ToolResult:
        items, now = await self.service.worklist()
        views = [item_view(it, self.lang, now, i) for i, it in enumerate(items, 1)]
        data = {
            "total": len(views),
            "ordering_rule": t(self.lang, "why.rule"),
            "studies": [
                {
                    "position": v["position"],
                    "case_id": v["case_id"],
                    "exam": self._v(v["exam"]),
                    "priority": [f'{r["label"]} ({r["source"]})' for r in v["reasons"]],
                    "wait_minutes": self._v(v["wait_minutes"]),
                }
                for v in views
            ],
        }
        blocks = [{"type": "next_study", "item": views[0], "total": len(views)}, {"type": "study_list", "items": views}] if views else []
        first = views[0]["case_id"] if views else None
        summary = t(self.lang, "tool.list_summary", n=len(views), first=first or "—")
        return ToolResult(data, summary, first, blocks)

    async def summarize_case(self, case_id: str) -> ToolResult:
        view = await self.service.open_case(case_id, self.lang) if case_id.strip() else None
        if not view:
            msg = t(self.lang, "case.missing", case=case_id or "—")
            return ToolResult({"error": msg}, msg, case_id or None, ok=False)
        declared = view["priors_declared"]
        data = {
            "case_id": view["case_id"],
            "exam": self._v(view["exam"]),
            "modalities": view["modalities"] or self.none,
            "sex": t(self.lang, f"sex.{view['sex']}") if view["sex"] in ("M", "F") else self._v(view["sex"]),
            "age": self._v(view["age"]),
            "indication": untrusted(self._v(view["reason"])) if view["reason"] else self.none,
            "technologist_note": untrusted(view["tech_note"]) if view["tech_note"] else self.none,
            "_free_text": t(self.lang, "tool.untrusted"),
            "technologist_critical_flag": view["critical"],
            "priority": [f'{r["label"]} ({r["source"]})' for r in view["reasons"]],
            "wait_minutes": self._v(view["wait_minutes"]),
            "priors_declared_in_order": self.none if declared is None else declared,
            "prior_studies_in_pacs": self._v(view["priors_in_pacs"]),
            "series": self._v(view["series_count"]),
            "images": self._v(view["instance_count"]),
            "image_findings": t(self.lang, "tool.no_findings"),
        }
        summary = f'{view["case_id"]}: {data["exam"]}' + (f' · {t(self.lang, "critical")}' if view["critical"] else "")
        return ToolResult(data, summary, view["case_id"], [{"type": "case", "case": view}])

    async def add_pending_item(self, args: dict) -> ToolResult:
        from .pending import KINDS
        kind = str(args.get("kind") or "")
        found = await self.service.find(str(args.get("case_id") or ""))
        if not found or kind not in KINDS:
            msg = t(self.lang, "case.missing", case=args.get("case_id") or "—") if not found else f"unknown kind {kind}"
            return ToolResult({"error": msg}, msg, None, ok=False)
        cid = found[0].case_id
        # provenance is the model, not the human: it is shown as "Residente (IA)" and never upgrades an item
        self.pending.add(cid, kind, "resident", str(args.get("note") or "") or None, by="residente-ia")
        msg = t(self.lang, "pending.noted", case=cid, kind=t(self.lang, f"pending.{kind}"))
        items = [i for i in await self.pending_list() if i["case_id"] == cid] if self.pending_list else []
        return ToolResult({"added": kind, "case_id": cid, "sent_to_anyone": False}, msg, cid,
                          [{"type": "pending_list", "items": items}])

    async def _resolve(self, case_id: str):
        found = await self.service.find(str(case_id or ""))
        if not found:
            raise ReportError(404, t(self.lang, "case.missing", case=case_id or "—"))
        return found[0]

    async def draft_report(self, args: dict) -> ToolResult:
        it = await self._resolve(args.get("case_id"))
        findings, impression = str(args.get("findings") or "").strip(), str(args.get("impression") or "").strip()
        if not findings:
            msg = t(self.lang, "report.need_findings", case=it.case_id)
            return ToolResult({"need_findings": msg}, msg, it.case_id, ok=False)
        technique = str(args.get("technique") or "").strip() or (it.meta.exam[self.lang] + "." if it.meta else self.none)
        st = await self.reports.draft(it.case_id, technique, findings, impression, self.by, self.lang)
        summary = t(self.lang, "report.drafted", case=it.case_id, v=st["version"], n=st["open_alerts"])
        return ToolResult(report_for_model(st), summary, it.case_id, [{"type": "report", "report": st}])

    async def edit_report(self, args: dict) -> ToolResult:
        it = await self._resolve(args.get("case_id"))
        st, diff = await self.reports.edit(it.case_id, str(args.get("section") or "findings"), str(args.get("find") or ""),
                                           str(args.get("replace") or ""), self.by, self.lang)
        summary = t(self.lang, "report.edited", case=it.case_id, v=st["version"], n=st["open_alerts"])
        return ToolResult(report_for_model(st) | {"diff": diff}, summary, it.case_id,
                          [{"type": "report", "report": st, "diff": diff}])

    async def qc_check(self, args: dict) -> ToolResult:
        it = await self._resolve(args.get("case_id"))
        if not self.reports.state(it.case_id):
            raise ReportError(404, t(self.lang, "report.none", case=it.case_id))
        st = await self.reports.run_qc(it.case_id, self.lang)
        return ToolResult(report_for_model(st), t(self.lang, "report.qc", case=it.case_id, n=st["open_alerts"]),
                          it.case_id, [{"type": "report", "report": st}])
