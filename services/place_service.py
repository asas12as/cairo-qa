"""Business logic for browsing and filtering places."""
from core import ctx


def browse_places(
    search: str = "",
    category: str = "",
    neighborhood: str = "",
    budget_level: str = "",
    min_rating: float = 0,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    all_places = ctx.db.get_all()
    s = search.lower()
    if s:
        all_places = [p for p in all_places if s in (p.get("name") or "").lower()
                      or s in (p.get("neighborhood") or "").lower()
                      or s in (p.get("notes") or "").lower()
                      or s in (p.get("genre_type") or "").lower()]
    if category:
        all_places = [p for p in all_places if (p.get("category") or "").lower() == category.lower()]
    if neighborhood:
        all_places = [p for p in all_places if neighborhood.lower() in (p.get("neighborhood") or "").lower()]
    if budget_level:
        all_places = [p for p in all_places if (p.get("budget_level") or "").lower() == budget_level.lower()]
    if min_rating:
        all_places = [p for p in all_places if (p.get("rating") or 0) >= min_rating]
    total = len(all_places)
    start = (page - 1) * per_page
    end = start + per_page
    return {"total": total, "page": page, "per_page": per_page, "places": all_places[start:end]}


def list_neighborhoods() -> list[str]:
    all_places = ctx.db.get_all()
    return sorted(set(p.get("neighborhood", "") for p in all_places if p.get("neighborhood")))


def get_place(place_id: int) -> dict | None:
    all_places = ctx.db.get_all()
    for p in all_places:
        try:
            if int(p.get("id", -1)) == place_id:
                return p
        except (ValueError, TypeError):
            if p.get("id") == place_id:
                return p
    return None
