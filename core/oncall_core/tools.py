"""Typed, read-only tools the resident model may call. Outputs only contain data from the PACS and the
order; every missing value is the literal "Sin dato"/"Unknown" so the model has nothing to fill in."""
from dataclasses import dataclass, field

from .i18n import t
from .service import Service
from .views import item_view

TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "list_pending",
            "description": "List the pending studies in the order they should be read: technologist critical flag, "
                           "then order priority, then longest wait. Read-only.",
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
TOOL_NAMES = {s["function"]["name"] for s in TOOL_SPECS}


@dataclass
class ToolResult:
    data: dict                      # what the model sees (JSON)
    summary: str                    # one line for the activity log
    case_id: str | None = None
    blocks: list[dict] = field(default_factory=list)  # cards for the UI, built from the same data
    ok: bool = True


class Toolbox:
    def __init__(self, service: Service, lang: str):
        self.service, self.lang = service, lang
        self.none = t(lang, "none")

    def _v(self, value):
        return self.none if value is None or value == "" else value

    async def call(self, name: str, args: dict) -> ToolResult:
        if name == "list_pending":
            return await self.list_pending()
        if name == "summarize_case":
            return await self.summarize_case(str(args.get("case_id", "")))
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
            "indication": self._v(view["reason"]),
            "technologist_note": self._v(view["tech_note"]),
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
