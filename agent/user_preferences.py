import json
import os


PREFERENCE_QUESTIONS = [
    {
        "id": "traveler_type",
        "question": "What kind of traveler are you?",
        "options": [
            {"value": "foodie", "label": "Foodie — I love exploring restaurants and local cuisine", "icon": "🍽️"},
            {"value": "culture", "label": "Culture & History — museums, historical sites, and cultural spots", "icon": "🏛️"},
            {"value": "active", "label": "Adventure & Activities — active experiences and outdoor fun", "icon": "🧗"},
            {"value": "nightlife", "label": "Nightlife & Entertainment — vibrant bars, clubs, and social spots", "icon": "🌙"},
            {"value": "relaxed", "label": "Relaxed & Leisurely — quiet cafes, gardens, and peaceful places", "icon": "🧘"},
        ],
    },
    {
        "id": "budget_level",
        "question": "What's your typical travel budget per day?",
        "options": [
            {"value": "budget", "label": "Budget — under 500 EGP/day", "icon": "💰"},
            {"value": "mid-range", "label": "Mid-range — 500–1500 EGP/day", "icon": "💵"},
            {"value": "upscale", "label": "Upscale — 1500–3000 EGP/day", "icon": "💎"},
            {"value": "luxury", "label": "Luxury — 3000+ EGP/day", "icon": "👑"},
        ],
    },
    {
        "id": "vibe",
        "question": "What atmosphere do you prefer?",
        "options": [
            {"value": "bustling", "label": "Bustling city life — busy streets, markets, lively areas", "icon": "🏙️"},
            {"value": "quiet", "label": "Quiet & scenic — peaceful spots, gardens, quiet neighborhoods", "icon": "🌿"},
            {"value": "balanced", "label": "A mix of both — depends on the mood", "icon": "⚖️"},
        ],
    },
]

TRAVELER_TYPE_MAP = {
    "foodie": {"foodie": 5, "culture": 2, "activity": 2, "nightlife": 2},
    "culture": {"foodie": 2, "culture": 5, "activity": 3, "nightlife": 1},
    "active": {"foodie": 2, "culture": 2, "activity": 5, "nightlife": 3},
    "nightlife": {"foodie": 3, "culture": 1, "activity": 2, "nightlife": 5},
    "relaxed": {"foodie": 3, "culture": 3, "activity": 1, "nightlife": 1},
    "balanced": {"foodie": 3, "culture": 3, "activity": 3, "nightlife": 3},
}

BUDGET_LEVEL_DAILY = {
    "budget": 500,
    "mid-range": 1500,
    "upscale": 2500,
    "luxury": 5000,
}

VIBE_WEIGHT = {
    "bustling": {"restaurant": 1.2, "attraction": 0.8, "cafe": 0.7, "hotel": 1.0},
    "quiet": {"restaurant": 0.8, "attraction": 1.2, "cafe": 1.3, "hotel": 1.0},
    "balanced": {"restaurant": 1.0, "attraction": 1.0, "cafe": 1.0, "hotel": 1.0},
}


def _traveler_to_scores(traveler_type: str) -> dict:
    return TRAVELER_TYPE_MAP.get(traveler_type, TRAVELER_TYPE_MAP["balanced"])


class UserPreferences:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def _path(self, user_id: str) -> str:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
        return os.path.join(self.data_dir, f"{safe}.json")

    def get(self, user_id: str) -> dict | None:
        path = self._path(user_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def save(self, user_id: str, answers: dict) -> dict:
        scores = _traveler_to_scores(answers.get("traveler_type", "balanced"))
        profile = {
            "foodie_score": scores["foodie"],
            "culture_score": scores["culture"],
            "activity_score": scores["activity"],
            "nightlife_score": scores["nightlife"],
            "budget_level": answers.get("budget_level", "mid-range"),
            "vibe": answers.get("vibe", "balanced"),
            "traveler_type": answers.get("traveler_type", "balanced"),
        }
        path = self._path(user_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2)
        return profile

    def get_batch(self, user_ids: list[str]) -> dict[str, dict]:
        profiles = {}
        for uid in user_ids:
            p = self.get(uid)
            if p:
                profiles[uid] = p
        return profiles

    def category_weight(self, profile: dict | None, category: str) -> float:
        if not profile:
            return 1.0
        vibe = profile.get("vibe", "balanced")
        return VIBE_WEIGHT.get(vibe, VIBE_WEIGHT["balanced"]).get(category, 1.0)
