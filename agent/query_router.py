import re
import json

CATEGORY_KEYWORDS = {
    "restaurant": ["restaurant", "eat", "dining", "dinner", "lunch", "breakfast", "food", "cuisine"],
    "hotel": ["hotel", "stay", "accommodation", "lodging", "hostel"],
    "attraction": ["attraction", "museum", "sight", "tourist", "monument", "mosque", "church", "park", "historical", "culture"],
    "cafe": ["cafe", "coffee", "tea", "shisha"],
}

NEIGHBORHOODS = ["zamalek", "maadi", "downtown", "garden city", "helwan", "nasr city",
                 "new cairo", "tagamoa", "shorouk", "rehab", "sheraton", "korba",
                 "el marg", "haram", "giza", "heliopolis", "dokki", "mohandiseen",
                 "agouza", "islamic cairo", "coptic cairo", "fustat", "manial",
                 "roda", "boulaq", "katameya", "mirage city", "new capital",
                 "6th october", "mokattam"]

GENRE_KEYWORDS = {
    "italian": ["italian", "pizza", "pasta"],
    "seafood": ["seafood", "fish", "shrimp"],
    "grill": ["grill", "steak", "bbq", "barbecue"],
    "museum": ["museum", "exhibition", "artifact"],
    "park": ["park", "garden"],
    "rooftop": ["rooftop", "roof", "skyline", "view"],
    "romantic": ["romantic", "couple", "date"],
    "family": ["family", "kids", "children", "child-friendly"],
    "late night": ["late night", "open late", "24 hours", "24h", "overnight"],
}

BUDGET_PATTERN = re.compile(r"(\d+)\s*-?\s*(?:egp|le|pounds?|usd)", re.IGNORECASE)
DAILY_BUDGET_PATTERN = re.compile(r"(?:daily|per\s*day|/day|a\s*day|per\s*person\s*per\s*day|فاليوم|في\s*اليوم|في\s*اليوم\s*الواحد)\s*(?:budget\s*)?(?:of\s*)?(\d+)|(\d+)\s*(?:per\s*day|/day|a\s*day|فاليوم|في\s*اليوم)", re.IGNORECASE)
RATING_PATTERN = re.compile(r"(?:rating|rated|stars?)\s*(?:of\s*)?(\d+(?:\.\d+)?)", re.IGNORECASE)
DAYS_PATTERN = re.compile(r"(\d+)\s*-?\s*(?:days?|nights?)", re.IGNORECASE)
BARE_BUDGET = re.compile(r"(?:only|have|budget|around|about|limited|total|معايا|عندي|فقط|ميزانية)\s*(\d+)", re.IGNORECASE)
FOR_X_DAYS = re.compile(r"(\d+)\s*(?:for|in|over|لمدة|فى|في)\s*(\d+)\s*-?\s*(?:days?|nights?|ايام|يوم|ليلة|ليالي)", re.IGNORECASE)
ARABIC_BARE_BUDGET = re.compile(r"(\d+)\s*(?:جنيه|جنية|جم|EGP)", re.IGNORECASE)
ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
ARABIC_DAYS = re.compile(r"(?:^|\s|و)(?:يوم|ايام|ليلة|ليالي)(?:\s|$|,|\.)", re.IGNORECASE)
ARABIC_BUDGET = re.compile(r"(\d+)\s*(?:جنيه|جنية|جم|فاليوم|في\s*اليوم)", re.IGNORECASE)
ARABIC_PLAN = re.compile(r"(?:رحلة|خطة| itinerary|برنامج)", re.IGNORECASE)
ARABIC_DAILY_BUDGET = re.compile(r"(\d+)\s*(?:فاليوم|في\s*اليوم|في\s*اليوم\s*الواحد)", re.IGNORECASE)
PLAN_KEYWORDS = {"plan", "itinerary", "trip", "schedule", "tour"}

LLM_PARSE_SYSTEM = """You are a query parser for a Cairo travel assistant. Extract structured fields from the user's question about visiting Cairo, Egypt.

Return ONLY valid JSON with these fields (no markdown, no explanation):
- "budget": integer or null — the budget amount in EGP. If the user says "daily budget of X" or "X per day", put X here and set is_daily_budget=true.
- "is_daily_budget": true if the budget is per day, false if total or absent
- "days": integer or null — number of days for the trip
- "category": one of "restaurant", "hotel", "attraction", "cafe", or null
- "neighborhood": neighborhood/district name or null (e.g. zamalek, downtown, maadi, heliopolis, giza)
- "genre": cuisine/type like "italian", "seafood", "grill", or null
- "min_rating": number 1-5 or null
- "is_plan": true if asking for an itinerary/trip plan/schedule
- "semantic_query": extract key search terms (2-6 words) from the question for database matching, or null
- "error": null, or a brief description if the query can't be understood

Examples:
Q: "Plan a 5-day trip to Cairo for a family with a daily budget of 1500 EGP per person"
A: {"budget": 1500, "is_daily_budget": true, "days": 5, "category": null, "neighborhood": null, "genre": null, "min_rating": null, "is_plan": true, "semantic_query": "family trip Cairo", "error": null}

Q: "what are the best restaurants in Zamalek?"
A: {"budget": null, "is_daily_budget": false, "days": null, "category": "restaurant", "neighborhood": "zamalek", "genre": null, "min_rating": null, "is_plan": false, "semantic_query": "best restaurants", "error": null}

Q: "I need a cheap hotel under 1000 EGP near downtown"
A: {"budget": 1000, "is_daily_budget": false, "days": null, "category": "hotel", "neighborhood": "downtown", "genre": null, "min_rating": null, "is_plan": false, "semantic_query": "cheap hotel downtown", "error": null}

Q: "tell me about the pyramids"
A: {"budget": null, "is_daily_budget": false, "days": null, "category": "attraction", "neighborhood": null, "genre": null, "min_rating": null, "is_plan": false, "semantic_query": "pyramids Giza", "error": null}

Q: "what's the weather like?"
A: {"budget": null, "is_daily_budget": false, "days": null, "category": null, "neighborhood": null, "genre": null, "min_rating": null, "is_plan": false, "semantic_query": null, "error": "not a travel query"}

Q: "2000 EGP for 3 days in Cairo"
A: {"budget": 2000, "is_daily_budget": false, "days": 3, "category": null, "neighborhood": null, "genre": null, "min_rating": null, "is_plan": true, "semantic_query": "Cairo trip", "error": null}
"""


class QueryRouter:
    def __init__(self, llm=None):
        self.llm = llm

    def route(self, question: str, history: list[dict] = None) -> dict:
        if self.llm:
            try:
                parsed = self._parse_llm(question, history or [])
                if parsed and parsed.get("error") is None:
                    return self._build_route(parsed, question)
            except Exception:
                pass
        return self._route_fallback(question)

    def _parse_llm(self, question: str, history: list[dict]) -> dict | None:
        messages = [
            {"role": "system", "content": LLM_PARSE_SYSTEM},
        ]
        for h in history[-4:]:
            messages.append({"role": "user", "content": h["question"]})
            messages.append({"role": "assistant", "content": h["answer"][:300]})
        messages.append({"role": "user", "content": f"Q: {question}"})
        raw = self.llm.chat(messages, max_tokens=200, temperature=0.0)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
        return json.loads(raw)

    def _build_route(self, parsed: dict, original_question: str) -> dict:
        budget_val = parsed.get("budget")
        days_val = parsed.get("days")
        is_daily = parsed.get("is_daily_budget", False)

        if budget_val is not None and is_daily and days_val:
            budget_val = budget_val * days_val

        filters = {}
        if parsed.get("category"):
            filters["category"] = parsed["category"]
        if parsed.get("neighborhood"):
            filters["neighborhood"] = parsed["neighborhood"]
        if parsed.get("genre"):
            filters["genre"] = parsed["genre"]
        if budget_val is not None:
            filters["max_budget"] = budget_val
        if parsed.get("min_rating"):
            filters["min_rating"] = parsed["min_rating"]

        semantic_query = parsed.get("semantic_query") or original_question
        is_plan = parsed.get("is_plan", False) or (budget_val is not None and days_val is not None)
        query_type = "plan" if is_plan else ("hybrid" if len(filters) > 0 else "semantic")

        return {
            "filters": filters,
            "semantic_query": semantic_query,
            "type": query_type,
            "_is_plan": is_plan,
            "_budget": budget_val,
            "_days": days_val,
        }

    def _route_fallback(self, question: str) -> dict:
        q_lower = question.lower()
        q_norm = q_lower.translate(ARABIC_DIGITS)
        filters = {}
        semantic_terms = []

        for cat, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in q_lower for kw in keywords):
                filters["category"] = cat
                break

        for hood in NEIGHBORHOODS:
            if hood in q_lower:
                filters["neighborhood"] = hood
                break

        for genre, keywords in GENRE_KEYWORDS.items():
            if any(kw in q_lower for kw in keywords):
                filters["genre"] = genre
                semantic_terms.append(genre)
                break

        budget_val = None
        days_val = None
        for_x = FOR_X_DAYS.search(q_norm)

        m = BUDGET_PATTERN.search(q_norm)
        if m:
            budget_val = int(m.group(1))

        if budget_val is None:
            m = ARABIC_BUDGET.search(q_norm)
            if m:
                budget_val = int(m.group(1))

        if budget_val is None:
            m = BARE_BUDGET.search(q_lower)
            if m:
                budget_val = int(m.group(1))

        if budget_val is None:
            m = ARABIC_BARE_BUDGET.search(q_norm)
            if m:
                budget_val = int(m.group(1))

        if budget_val is None:
            m = re.search(r"(?:^|\s)(\d{3,6})(?:\s|$)", q_norm)
            if m:
                budget_val = int(m.group(1))

        if for_x:
            if budget_val is None:
                budget_val = int(for_x.group(1))

        if budget_val is not None:
            filters["max_budget"] = budget_val

        rating_match = RATING_PATTERN.search(q_lower)
        if rating_match:
            filters["min_rating"] = float(rating_match.group(1))

        has_filters = len([k for k in filters if filters[k] is not None]) > 0

        stopwords = {"a", "an", "the", "in", "at", "for", "to", "with", "and", "or",
                     "of", "i", "have", "my", "is", "are", "do", "does", "what",
                     "where", "which", "how", "much", "many", "can", "you", "recommend"}
        tokens = [w for w in re.sub(r"[^\w\s]", " ", q_lower).split()
                  if w not in stopwords and len(w) > 2]
        for cat_kws in CATEGORY_KEYWORDS.values():
            tokens = [t for t in tokens if t not in cat_kws]
        tokens = [t for t in tokens if t not in NEIGHBORHOODS]
        tokens = [t for t in tokens if not BUDGET_PATTERN.search(t)]
        extra = [t for t in tokens if t not in semantic_terms]
        semantic_query = " ".join(semantic_terms + extra)
        query_type = "hybrid" if has_filters and semantic_query else \
                     "structured" if has_filters else \
                     "semantic" if semantic_query else "semantic"
        if not semantic_query:
            semantic_query = q_lower

        m = DAYS_PATTERN.search(q_norm)
        if m:
            days_val = int(m.group(1))
        elif for_x:
            days_val = int(for_x.group(2))
        elif ARABIC_DAYS.search(q_norm):
            day_match = ARABIC_DAYS.search(q_norm)
            before = q_norm[:day_match.start()]
            digit_matches = re.findall(r"(\d+)", before)
            if digit_matches:
                candidate_days = int(digit_matches[-1])
                if ARABIC_DAILY_BUDGET.search(q_norm):
                    daily_m = ARABIC_DAILY_BUDGET.search(q_norm)
                    daily_val = int(daily_m.group(1))
                    if daily_val == candidate_days:
                        candidate_days = None
                if candidate_days and candidate_days <= 365:
                    days_val = candidate_days

        if budget_val is not None and days_val is not None:
            daily_m = DAILY_BUDGET_PATTERN.search(q_norm) or ARABIC_DAILY_BUDGET.search(q_norm)
            daily_match_val = None
            if daily_m:
                daily_match_val = int(daily_m.group(1) or daily_m.group(2) or 0)
            if daily_match_val == budget_val:
                budget_val = budget_val * days_val

        has_plan_kw = any(kw in q_lower for kw in PLAN_KEYWORDS) or bool(ARABIC_PLAN.search(q_norm))
        has_budget_and_days = budget_val is not None and days_val is not None
        is_plan = has_budget_and_days or (days_val is not None and has_plan_kw)

        return {
            "filters": filters,
            "semantic_query": semantic_query,
            "type": query_type,
            "_is_plan": is_plan,
            "_budget": budget_val,
            "_days": days_val,
        }
