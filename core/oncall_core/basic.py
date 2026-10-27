"""Basic mode: the day-1 rule-based answers, used when no model provider answers."""
from . import intents
from .agent import Answer
from .i18n import t
from .service import Service
from .store import Store
from .views import item_view


async def basic_answer(service: Service, store: Store, text: str, lang: str) -> Answer:
    intent, case_id = intents.match(text)

    def done(txt: str, blocks: list[dict] | None = None, name: str | None = None, cid: str | None = None) -> Answer:
        if name:
            store.log("tool", name, input={"case_id": cid} if cid else {}, output=txt[:160], case_id=cid, mode="basic")
        return Answer(txt, "basic", None, [name] if name else [], blocks or [])

    if intent == "worklist":
        items, now = await service.worklist()
        if not items:
            return done(t(lang, "wl.empty"), name="list_pending")
        views = [item_view(it, lang, now, i) for i, it in enumerate(items, 1)]
        c = sum(v["critical"] for v in views)
        crit = t(lang, "wl.crit_some", c=c) if c else t(lang, "wl.crit_none")
        key = "wl.summary_one" if len(views) == 1 else "wl.summary"
        txt = f"{t(lang, key, n=len(views), crit=crit)} {t(lang, 'wl.next', case=views[0]['case_id'])}"
        return done(txt, [{"type": "next_study", "item": views[0], "total": len(views)}, {"type": "study_list", "items": views}],
                    "list_pending", views[0]["case_id"])
    if intent == "why":
        items, now = await service.worklist()
        if not items:
            return done(t(lang, "wl.empty"))
        target = next((it for it in items if case_id and it.case_id == case_id), items[0])
        m = target.meta
        if m and m.tech_critical:
            txt = t(lang, "why.critical", case=target.case_id)
        elif m and target is items[0] and len(items) > 1 and items[1].meta and items[1].meta.priority == m.priority:
            txt = t(lang, "why.wait", case=target.case_id, m=target.wait_minutes(now))
        else:
            p = t(lang, f"priority.{m.priority}") if m else t(lang, "priority.unknown")
            txt = t(lang, "why.priority", case=target.case_id, p=p)
        pos = items.index(target) + 1
        return done(f"{txt} {t(lang, 'why.rule')}", [{"type": "evidence", "item": item_view(target, lang, now, pos)}],
                    "list_pending", target.case_id)
    if intent == "open":
        if not case_id:
            return done(t(lang, "case.which"))
        view = await service.open_case(case_id, lang)
        if not view:
            return done(t(lang, "case.missing", case=case_id))
        if view["critical"]:
            why = t(lang, "case.why_critical")
        elif view["priority"]:
            why = t(lang, "case.why_priority", p=t(lang, f"priority.{view['priority']}"))
        else:
            why = t(lang, "case.why_none")
        n = view["priors_in_pacs"]
        priors = t(lang, "case.priors_unknown") if n is None else t(lang, "case.priors_0") if n == 0 else t(lang, "case.priors_n", n=n)
        return done(t(lang, "case.open", case=view["case_id"], why=why, priors=priors), [{"type": "case", "case": view}],
                    "summarize_case", view["case_id"])
    return done(t(lang, "help"))
