from research_assistant.data_api import lookups

_ANALYTICAL_TOOLS = ("run_analysis",)


async def apply(run: dict, context: dict) -> dict:
    researcher = context.get("researcher")
    if not researcher:
        return run
    access = await lookups.get_researcher_access(researcher)
    if access["is_admin"]:
        return run
    allowed = {d.upper() for d in access["dataset_ids"]}
    restricted = {
        d["id"].upper() for d in await lookups.list_datasets() if d["restricted"]
    }
    off_limits = (restricted & {s.upper() for s in run["sources"]}) - allowed
    analysed = sorted(
        ds
        for ds in off_limits
        if any(
            ds in (t.get("args") or "").upper()
            for t in run["tools"]
            if t.get("tool") in _ANALYTICAL_TOOLS
        )
    )
    if not analysed:
        return run
    decision = {
        "policy": "researcher_access",
        "action": "deny",
        "reason": (
            f"Researcher '{researcher}' is not authorised to analyse restricted "
            f"dataset(s) {', '.join(analysed)}; the result was withheld."
        ),
        "datasets": analysed,
    }
    return {
        **run,
        "answer": decision["reason"],
        "sources": [],
        "governance": [*run["governance"], decision],
    }
