BUDGET_LEVEL_ORDER = {"$": 1, "$$": 2, "$$$": 3, "$$$$": 4, "$$-$$$": 2.5, "$$-$$": 2}
BUDGET_TEXT_MAP = {"budget": 0.5, "mid-range": 2, "upscale": 3, "luxury": 4}

PREF_CATEGORY_LABELS = {
    "foodie": "restaurant",
    "culture": "attraction",
    "active": "attraction",
    "nightlife": "nightlife",
    "relaxed": "cafe",
}

PREF_CATEGORY_COUNT = {
    "foodie": 6,
    "culture": 5,
    "active": 4,
    "nightlife": 4,
    "relaxed": 3,
}


def _budget_score(budget_level: str) -> float:
    if not budget_level:
        return 99
    bl = budget_level.strip().lower()
    if bl.startswith("free"):
        return 0
    text_score = BUDGET_TEXT_MAP.get(bl, None)
    if text_score is not None:
        return text_score
    for key in sorted(BUDGET_LEVEL_ORDER, key=len, reverse=True):
        if bl.startswith(key):
            return BUDGET_LEVEL_ORDER[key]
    return 99


def _target_budget_score(profile: dict | None) -> float:
    if not profile:
        return 2.0
    return BUDGET_TEXT_MAP.get(profile.get("budget_level", "mid-range"), 2.0)


def _hotel_fit_score(row: dict, daily_budget: int, target_score: float) -> float:
    max_p = row.get("budget_range_max") or 0
    min_p = row.get("budget_range_min") or 0
    if max_p <= 0:
        return 999
    avg = (min_p + max_p) / 2
    price_diff = abs(avg - daily_budget)
    rating = row.get("rating") or 0
    return price_diff - rating * 100


def _pick(places: list[dict], count: int, target_score: float) -> list[dict]:
    pool = [p for p in places if _budget_score(p.get("budget_level", "")) <= target_score + 1]
    if not pool:
        pool = places
    sorted_pool = sorted(pool, key=lambda p: -(p.get("rating") or 0))
    return sorted_pool[:count]


def render_budget_plan(context: list[dict], total_budget: int, days: int,
                       profile: dict | None = None) -> tuple[str, list[dict]]:
    daily_budget = total_budget // days
    target_score = _target_budget_score(profile)

    hotels = [r for r in context if r.get("category") and r["category"].lower() == "hotel"]
    restaurants = [r for r in context if r.get("category") and r["category"].lower() == "restaurant"]
    attractions = [r for r in context if r.get("category") and r["category"].lower() == "attraction"]
    cafes = [r for r in context if r.get("category") and r["category"].lower() == "cafe"]
    nightlife = [r for r in context if r.get("category") and r["category"].lower() == "nightlife"]

    traveler_type = (profile or {}).get("traveler_type", "balanced")
    vibe = (profile or {}).get("vibe", "balanced")

    recommended = []
    lines = []
    lines.append(f"📊 **{total_budget:,} EGP · {days} days** (~{daily_budget:,} EGP/day)\n")

    # ---- Select hotel ----
    affordable_hotels = sorted(
        [h for h in hotels if h.get("budget_range_max") and h["budget_range_max"] <= daily_budget * 2],
        key=lambda h: _hotel_fit_score(h, daily_budget, target_score)
    )
    chosen_hotel = affordable_hotels[0] if affordable_hotels else (
        min(hotels, key=lambda h: (h.get("budget_range_max") or 99999)) if hotels else None
    )
    if chosen_hotel:
        lines.append(f"**🏨 Accommodation:** {chosen_hotel['name']}  {_stars(chosen_hotel.get('rating'))}  {chosen_hotel.get('neighborhood','')}  {_price_str(chosen_hotel)}/night")
        recommended.append(chosen_hotel)
        if affordable_hotels and len(affordable_hotels) > 1:
            alt = ", ".join(f"{h['name']} ({_price_str(h)})" for h in affordable_hotels[1:3])
            lines.append(f"   *Alternatives: {alt}*")
        lines.append("")

    # ---- Select places across categories ----
    rest_selected = _pick(restaurants, 5, target_score)
    attr_selected = _pick(attractions, 5, target_score)
    cafe_selected = _pick(cafes, 1, target_score)
    night_selected = _pick(nightlife, 3, target_score)

    if not rest_selected:
        rest_selected = sorted(restaurants, key=lambda r: -(r.get("rating") or 0))[:5]
    if not attr_selected:
        attr_selected = sorted(attractions, key=lambda a: -(a.get("rating") or 0))[:5]

    recommended.extend(rest_selected)
    recommended.extend(attr_selected)
    if cafe_selected:
        recommended.extend(cafe_selected)
    if night_selected:
        recommended.extend(night_selected)

    # ---- Distribute into day-by-day itinerary ----
    used_rest = list(rest_selected)
    used_attr = list(attr_selected)

    hotel_name = chosen_hotel["name"] if chosen_hotel else "your hotel"

    def _day_header(day_num: int, title: str) -> str:
        return f"\n**━━━ Day {day_num}: {title} ━━━**\n"

    def _pop_rest() -> dict | None:
        return used_rest.pop(0) if used_rest else None

    def _pop_attr() -> dict | None:
        return used_attr.pop(0) if used_attr else None

    def _fmt_place(p: dict) -> str:
        hood = p.get("neighborhood", "")
        stars = _stars(p.get("rating"))
        price = _price_str(p)
        return f"   • **{p['name']}** {stars} {hood} {price}".rstrip()

    def _fmt_meal(meal: str, p: dict | None) -> str:
        if not p:
            return f"   *{meal}: grab something local / street food*"
        return f"   *{meal}:* {_fmt_place(p)}"

    budget_per_day = total_budget // days

    lines.append(_day_header(1, "Arrival & Local Exploration"))
    lines.append(f"   Check into {hotel_name}. Settle in and take a walk around the neighborhood.")
    if cafe_selected:
        lines.append(f"   *Afternoon coffee:* {_fmt_place(cafe_selected[0])}")
    r1 = _pop_rest()
    lines.append(_fmt_meal("Dinner", r1))
    if traveler_type == "nightlife" and night_selected:
        lines.append(f"   *Evening:* {_fmt_place(night_selected[0])}")
    lines.append(f"   *Daily spend: ~{budget_per_day} EGP*")

    lines.append(_day_header(2, "Iconic Cairo — History & Pyramids"))
    lines.append(f"   Start early from {hotel_name}.")
    a1, a2 = _pop_attr(), _pop_attr()
    lines.append(f"   *Morning:* {_fmt_place(a1) if a1 else 'Explore Giza Pyramids area'}")
    lines.append(f"   *Afternoon:* {_fmt_place(a2) if a2 else 'Visit the Grand Egyptian Museum'}")
    r2 = _pop_rest()
    lines.append(_fmt_meal("Lunch", r2))
    r3 = _pop_rest()
    lines.append(_fmt_meal("Dinner", r3))
    lines.append(f"   *Daily spend: ~{budget_per_day} EGP*")

    lines.append(_day_header(3, "Cultural Immersion — Museums & Old Cairo"))
    lines.append(f"   Head to central Cairo from {hotel_name}.")
    a3, a4 = _pop_attr(), _pop_attr()
    lines.append(f"   *Morning:* {_fmt_place(a3) if a3 else 'National Museum of Egyptian Civilization'}")
    lines.append(f"   *Afternoon:* {_fmt_place(a4) if a4 else 'Explore Islamic Cairo / Khan el-Khalili'}")
    r4 = _pop_rest()
    lines.append(_fmt_meal("Lunch", r4))
    r5 = _pop_rest()
    lines.append(_fmt_meal("Dinner", r5))
    if traveler_type == "nightlife" and len(night_selected) > 1:
        lines.append(f"   *Evening:* {_fmt_place(night_selected[1])}")
    lines.append(f"   *Daily spend: ~{budget_per_day} EGP*")

    lines.append(_day_header(4, "Food Tour & Local Neighborhoods"))
    lines.append(f"   Today is about eating your way through Cairo! Start from {hotel_name}.")
    lines.append(f"   *Morning walk:* Explore Zamalek or Downtown Cairo")
    r6, r7, r8 = _pop_rest(), _pop_rest(), _pop_rest()
    lines.append(_fmt_meal("Brunch", r6))
    lines.append(_fmt_meal("Lunch", r7))
    if cafe_selected:
        lines.append(f"   *Afternoon break:* {_fmt_place(cafe_selected[0])}")
    a5 = _pop_attr()
    if a5:
        lines.append(f"   *Late afternoon:* {_fmt_place(a5)}")
    lines.append(_fmt_meal("Dinner", r8))
    if traveler_type == "nightlife" and len(night_selected) > 2:
        lines.append(f"   *Evening:* {_fmt_place(night_selected[2])}")
    lines.append(f"   *Daily spend: ~{budget_per_day} EGP*")

    lines.append(_day_header(5, "Relaxed Farewell & Departure"))
    lines.append(f"   Last day! Enjoy a slow morning around {hotel_name}.")
    r9 = _pop_rest()
    lines.append(_fmt_meal("Breakfast / Brunch", r9))
    a6 = _pop_attr()
    if a6:
        lines.append(f"   *Morning:* {_fmt_place(a6)}")
    else:
        lines.append(f"   *Morning:* Last-minute souvenir shopping at Khan el-Khalili")
    lines.append(f"   *Afternoon:* Check out and head to airport.")
    lines.append(f"   *Daily spend: ~{budget_per_day} EGP*")

    # ---- Budget breakdown ----
    hotel_pct = 0.35 if traveler_type == "foodie" else 0.45
    food_pct = 0.35 if traveler_type == "foodie" else 0.25
    hotel_budget = int(total_budget * hotel_pct)
    food_budget = int(total_budget * food_pct)
    activity_budget = total_budget - hotel_budget - food_budget

    lines.append(f"\n---")
    lines.append(f"✅ **Budget Summary:** Hotel ~{hotel_budget} + Food ~{food_budget} + Activities ~{activity_budget} = {hotel_budget + food_budget + activity_budget} EGP")
    leftover = total_budget - (hotel_budget + food_budget + activity_budget)
    if leftover > 0:
        lines.append(f"   *{leftover} EGP remaining for transport/souvenirs*")
    elif leftover < 0:
        lines.append(f"   *{abs(leftover)} EGP over — adjust hotel or activity choices*")

    return "\n".join(lines), recommended


def _stars(rating) -> str:
    if rating is None:
        return ""
    r = round(rating)
    return "★" * r + "☆" * (5 - r)


def _price_str(row: dict) -> str:
    bl = row.get("budget_level", "")
    rmin = row.get("budget_range_min")
    rmax = row.get("budget_range_max")
    if rmin and rmax:
        return f"{rmin}-{rmax} EGP"
    if rmin:
        return f"from {rmin} EGP"
    return bl
