import re

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
RATING_PATTERN = re.compile(r"(?:rating|rated|stars?)\s*(?:of\s*)?(\d+(?:\.\d+)?)", re.IGNORECASE)
DAYS_PATTERN = re.compile(r"(\d+)\s*-?\s*(?:days?|nights?)", re.IGNORECASE)

# Fallback patterns for budget without suffix: "only 6000", "6000 for 5 days"
BARE_BUDGET = re.compile(r"(?:only|have|budget|around|about|limited|total|معايا|عندي|فقط|ميزانية)\s*(\d+)", re.IGNORECASE)
FOR_X_DAYS = re.compile(r"(\d+)\s*(?:for|in|over|لمدة|فى|في)\s*(\d+)\s*-?\s*(?:days?|nights?|ايام|يوم|ليلة|ليالي)", re.IGNORECASE)

# Bare Arabic budget: numbers without currency suffix appearing before budget-related words
ARABIC_BARE_BUDGET = re.compile(r"(\d+)\s*(?:جنيه|جنية|جم|EGP)", re.IGNORECASE)

# Arabic patterns
ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
ARABIC_DAYS = re.compile(r"(?:يوم|ايام|ليلة|ليالي)", re.IGNORECASE)
ARABIC_BUDGET = re.compile(r"(\d+)\s*(?:جنيه|جنية|جم)", re.IGNORECASE)
ARABIC_PLAN = re.compile(r"(?:رحلة|خطة| itinerary|برنامج)", re.IGNORECASE)

PLAN_KEYWORDS = {"plan", "itinerary", "trip", "schedule", "tour"}


class QueryRouter:
    def __init__(self):
        pass

    def route(self, question: str) -> dict:
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

        # Budget detection (multiple strategies)
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

        # Bare standalone number (3-6 digits) as budget
        if budget_val is None:
            m = re.search(r"(?:^|\s)(\d{3,6})(?:\s|$)", q_norm)
            if m:
                budget_val = int(m.group(1))

        if for_x:
            if budget_val is None:
                budget_val = int(for_x.group(1))

        if budget_val is not None:
            filters["max_budget"] = budget_val

        # Rating
        rating_match = RATING_PATTERN.search(q_lower)
        if rating_match:
            filters["min_rating"] = float(rating_match.group(1))

        has_filters = len([k for k in filters if filters[k] is not None]) > 0

        # Semantic query
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

        # Day detection
        m = DAYS_PATTERN.search(q_norm)
        if m:
            days_val = int(m.group(1))
        elif for_x:
            days_val = int(for_x.group(2))
        elif ARABIC_DAYS.search(q_norm):
            day_match = ARABIC_DAYS.search(q_norm)
            before = q_norm[:day_match.start()]
            digits = re.findall(r"(\d+)", before)
            if digits:
                days_val = int(digits[-1])

        # Plan detection
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
