"""Business logic for the chat / ask endpoints."""
import json
import uuid

from agent.budget_templates import render_budget_plan
from agent.user_preferences import BUDGET_LEVEL_DAILY
from models.schemas import AskResponse, PlaceInfo
from core import ctx


_RRF_K = 60


def _rrf(ranked_lists: list[list[dict]]) -> list[dict]:
    scores = {}
    for rank_list in ranked_lists:
        for rank, item in enumerate(rank_list):
            item_id = item["id"]
            scores.setdefault(item_id, {"score": 0, "item": item})
            scores[item_id]["score"] += 1 / (_RRF_K + rank + 1)
    ranked = sorted(scores.values(), key=lambda x: -x["score"])
    return [r["item"] for r in ranked]


def _expand_query(question: str, semantic_query: str) -> list[str]:
    """Generate query variations using the LLM for better recall."""
    if not semantic_query:
        return [question]
    messages = [
        {"role": "system", "content": "Rephrase the search query 3 ways to help find matching places. Return only the rephrases, one per line, no numbering."},
        {"role": "user", "content": f"Query: {semantic_query}"},
    ]
    try:
        raw = ctx.llm.chat(messages, max_tokens=120, temperature=0.3)
        variations = [q.strip() for q in raw.strip().split("\n") if q.strip()]
        all_queries = [semantic_query] + variations[:3]
        seen = set()
        return [q for q in all_queries if q.lower() not in seen and not seen.add(q.lower())]
    except Exception:
        return [semantic_query]


def _to_place_info(row: dict) -> PlaceInfo:
    return PlaceInfo(
        name=row.get("name", "N/A"),
        category=row.get("category", ""),
        neighborhood=row.get("neighborhood", ""),
        genre_type=row.get("genre_type", ""),
        rating=row.get("rating"),
        budget_level=row.get("budget_level"),
        budget_range_min=row.get("budget_range_min"),
        budget_range_max=row.get("budget_range_max"),
        phone=row.get("phone"),
        notes=row.get("notes"),
        work_hours=row.get("work_hours"),
    )


def _context_matches_filters(context: list[dict], filters: dict) -> str | None:
    if not filters:
        return None
    neighborhood = filters.get("neighborhood")
    if neighborhood:
        hood_lower = neighborhood.lower()
        if not any(hood_lower in (r.get("neighborhood") or "").lower() for r in context):
            return f"I don't have any places in {neighborhood.title()} in my database."
    return None


def _get_plan_context():
    return ctx.retriever.structured_db.get_all()


def _derive_budget(route_info: dict, profile: dict | None) -> int:
    budget = route_info.get("_budget")
    if budget:
        return budget
    if profile:
        level = profile.get("budget_level", "mid-range")
        days = route_info.get("_days", 1)
        return BUDGET_LEVEL_DAILY.get(level, 1500) * days
    return 5000


def _build_companion_context(user_id: str, companion_ids: list[str]) -> tuple[dict, list[str], str]:
    """Load companion profiles, build context string."""
    if not companion_ids:
        return {}, [], ""
    profiles = ctx.prefs.get_batch(companion_ids)
    from services import profile_service as ps
    lines = []
    display_names = []
    for uid in companion_ids:
        p = profiles.get(uid, {})
        display_name = uid
        pp = ps.get(uid)
        if pp and pp.get("display_name"):
            display_name = pp["display_name"]
        prefs_str = ", ".join(filter(None, [
            p.get("traveler_type", ""),
            f"{BUDGET_LEVEL_DAILY.get(p.get('budget_level', 'mid-range'), 1500)} EGP/day" if p.get("budget_level") else "",
            p.get("vibe", ""),
        ]))
        lines.append(f"{display_name} ({prefs_str})" if prefs_str else display_name)
        display_names.append(display_name)
    return profiles, display_names, "Your companions: " + "; ".join(lines) + "."


def _aggregate_companion_prefs(companion_profiles: dict) -> dict:
    """Aggregate companion preferences: min budget, mode vibe, average traveler scores."""
    if not companion_profiles:
        return {}
    budgets = []
    vibes = []
    traveler_types = []
    for p in companion_profiles.values():
        bl = p.get("budget_level")
        if bl and bl in BUDGET_LEVEL_DAILY:
            budgets.append(BUDGET_LEVEL_DAILY[bl])
        if p.get("vibe"):
            vibes.append(p["vibe"])
        if p.get("traveler_type"):
            traveler_types.append(p["traveler_type"])
    from collections import Counter
    mode_vibe = Counter(vibes).most_common(1)[0][0] if vibes else "balanced"
    min_budget = min(budgets) if budgets else None
    return {"budget_level_min": min_budget, "vibe_mode": mode_vibe, "traveler_types": traveler_types}


def handle_question(user_id: str | None, question: str, companion_ids: list[str] = None) -> AskResponse:
    conv_id = str(uuid.uuid4())
    profile = ctx.prefs.get(user_id) if user_id else None
    history = ctx.memory.get_history(user_id) if user_id else []

    companion_profiles, companion_names, companion_context = _build_companion_context(user_id, companion_ids or [])

    route_info = ctx.router_agent.route(question, history)

    if user_id:
        acc_budget, acc_days = ctx.memory.get_accumulated_params(user_id, question)
        if route_info.get("_is_plan"):
            if route_info.get("_budget") is None and acc_budget is not None:
                route_info["_budget"] = acc_budget
            if route_info.get("_days") is None and acc_days is not None:
                route_info["_days"] = acc_days
        else:
            if acc_budget is not None and acc_days is not None:
                route_info["_is_plan"] = True
                route_info["_budget"] = acc_budget
                route_info["_days"] = acc_days

    if route_info.get("_is_plan"):
        context = _get_plan_context()
    else:
        queries = _expand_query(question, route_info.get("semantic_query", ""))
        all_results = []
        for q in queries:
            ri = dict(route_info)
            ri["semantic_query"] = q
            all_results.append(ctx.retriever.retrieve(ri, limit=5))
        context = _rrf(all_results)[:5]

    mismatch = _context_matches_filters(context, route_info.get("filters", {}))
    if mismatch:
        if user_id:
            ctx.memory.add_exchange(user_id, question, mismatch)
        ctx.logger.log(conv_id, question, route_info, context, mismatch)
        return AskResponse(answer=mismatch, conversation_id=conv_id, places_found=0, places=[])

    if route_info.get("_is_plan") and context:
        agg = _aggregate_companion_prefs(companion_profiles)
        budget = _derive_budget(route_info, profile)
        if agg.get("budget_level_min") and agg["budget_level_min"] < budget:
            budget = agg["budget_level_min"]
        days = route_info.get("_days") or 1
        comps_per_person = len(companion_names) + 1
        answer, recommended = render_budget_plan(context, budget * comps_per_person, days, profile=profile)
        display_places = recommended
    else:
        answer = ctx.answer_gen.generate(question, context, profile=profile, history=history,
                                          companion_context=companion_context)
        display_places = context

    if user_id:
        ctx.memory.add_exchange(user_id, question, answer)
    ctx.logger.log(conv_id, question, route_info, context, answer)

    return AskResponse(
        answer=answer,
        conversation_id=conv_id,
        places_found=len(display_places),
        places=[_to_place_info(r) for r in display_places],
    )


def handle_question_stream(user_id: str | None, question: str, companion_ids: list[str] = None):
    """Generator that yields SSE event strings for streaming."""
    conv_id = str(uuid.uuid4())
    profile = ctx.prefs.get(user_id) if user_id else None
    history = ctx.memory.get_history(user_id) if user_id else []

    companion_profiles, companion_names, companion_context = _build_companion_context(user_id, companion_ids or [])

    route_info = ctx.router_agent.route(question, history)

    if user_id:
        acc_budget, acc_days = ctx.memory.get_accumulated_params(user_id, question)
        if route_info.get("_is_plan"):
            if route_info.get("_budget") is None and acc_budget is not None:
                route_info["_budget"] = acc_budget
            if route_info.get("_days") is None and acc_days is not None:
                route_info["_days"] = acc_days
        else:
            if acc_budget is not None and acc_days is not None:
                route_info["_is_plan"] = True
                route_info["_budget"] = acc_budget
                route_info["_days"] = acc_days

    if route_info.get("_is_plan"):
        context = _get_plan_context()
    else:
        queries = _expand_query(question, route_info.get("semantic_query", ""))
        all_results = []
        for q in queries:
            ri = dict(route_info)
            ri["semantic_query"] = q
            all_results.append(ctx.retriever.retrieve(ri, limit=5))
        context = _rrf(all_results)[:5]

    mismatch = _context_matches_filters(context, route_info.get("filters", {}))
    if mismatch:
        if user_id:
            ctx.memory.add_exchange(user_id, question, mismatch)
        ctx.logger.log(conv_id, question, route_info, context, mismatch)
        yield f"data: {json.dumps({'type': 'token', 'text': mismatch})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'answer': mismatch, 'conversation_id': conv_id, 'places': []})}\n\n"
        return

    display_places = context
    if route_info.get("_is_plan") and context:
        agg = _aggregate_companion_prefs(companion_profiles)
        budget = _derive_budget(route_info, profile)
        if agg.get("budget_level_min") and agg["budget_level_min"] < budget:
            budget = agg["budget_level_min"]
        days = route_info.get("_days") or 1
        comps_per_person = len(companion_names) + 1
        full_answer, recommended = render_budget_plan(context, budget * comps_per_person, days, profile=profile)
        display_places = recommended
        yield f"data: {json.dumps({'type': 'token', 'text': full_answer})}\n\n"
    else:
        full_answer = ""
        for token in ctx.answer_gen.generate_stream(question, context, profile=profile, history=history,
                                                      companion_context=companion_context):
            full_answer += token
            yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"

    if user_id:
        ctx.memory.add_exchange(user_id, question, full_answer)
    ctx.logger.log(conv_id, question, route_info, context, full_answer)

    places_data = [_to_place_info(r).model_dump() for r in display_places]
    yield f"data: {json.dumps({'type': 'done', 'answer': full_answer, 'conversation_id': conv_id, 'places': places_data})}\n\n"
