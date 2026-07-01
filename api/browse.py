"""Public browse & review endpoints."""
from fastapi import APIRouter, HTTPException, Query

from models.schemas import PlaceInfo
from services.place_service import browse_places, get_place, list_neighborhoods
from services.review_service import create_review, get_reviews, my_reviews

router = APIRouter()


@router.get("/places")
async def browse(
    search: str = "",
    category: str = "",
    neighborhood: str = "",
    budget_level: str = "",
    min_rating: float = Query(0, ge=0),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    return browse_places(search, category, neighborhood, budget_level, min_rating, page, per_page)


@router.get("/places/neighborhoods")
async def neighborhoods():
    return {"neighborhoods": list_neighborhoods()}


@router.get("/places/{place_id}")
async def place_detail(place_id: int):
    p = get_place(place_id)
    if not p:
        raise HTTPException(status_code=404, detail="Place not found")
    return p


@router.post("/places/{place_id}/reviews")
async def create(place_id: int, data: dict):
    return create_review(place_id, data["user_id"], data["rating"], data.get("comment", ""))


@router.get("/places/{place_id}/reviews")
async def reviews(place_id: int):
    return get_reviews(place_id)


@router.get("/reviews/my")
async def my(user_id: str = Query(...)):
    return {"reviews": my_reviews(user_id)}
