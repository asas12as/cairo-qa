"""Review / rating business logic."""
import json
import os
from datetime import datetime, timezone

from core import data_path

REVIEWS_FILE = data_path("reviews.json")


def _load():
    if not os.path.exists(REVIEWS_FILE):
        return []
    try:
        with open(REVIEWS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save(reviews):
    os.makedirs(os.path.dirname(REVIEWS_FILE) or ".", exist_ok=True)
    with open(REVIEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(reviews, f, indent=2, ensure_ascii=False)


def create_review(place_id: int, user_id: str, rating: float, comment: str = "") -> dict:
    reviews = _load()
    new_id = max((r["id"] for r in reviews), default=0) + 1
    review = {
        "id": new_id,
        "user_id": user_id,
        "place_id": place_id,
        "rating": rating,
        "comment": comment,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    reviews.append(review)
    _save(reviews)
    return review


def get_reviews(place_id: int) -> dict:
    reviews = _load()
    place_reviews = [r for r in reviews if r["place_id"] == place_id]
    avg = round(sum(r["rating"] for r in place_reviews) / len(place_reviews), 1) if place_reviews else None
    return {
        "place_id": place_id,
        "average_rating": avg,
        "count": len(place_reviews),
        "reviews": place_reviews[-20:],
    }


def my_reviews(user_id: str) -> list[dict]:
    reviews = _load()
    return [r for r in reviews if r["user_id"] == user_id][-50:]
