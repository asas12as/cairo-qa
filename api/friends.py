from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth import get_current_user
from services import friendship_service, profile_service

router = APIRouter()


class FriendRequest(BaseModel):
    username: str


class RequestAction(BaseModel):
    request_id: str


@router.post("/friends/request")
def send_request(req: FriendRequest, user: dict = Depends(get_current_user)):
    if req.username == user["username"]:
        raise HTTPException(status_code=400, detail="Cannot friend yourself")
    result = friendship_service.send_request(user["username"], req.username)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/friends/accept")
def accept_request(req: RequestAction, user: dict = Depends(get_current_user)):
    result = friendship_service.accept_request(req.request_id, user["username"])
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/friends/reject")
def reject_request(req: RequestAction, user: dict = Depends(get_current_user)):
    result = friendship_service.reject_request(req.request_id, user["username"])
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/friends/unfriend")
def unfriend(req: FriendRequest, user: dict = Depends(get_current_user)):
    result = friendship_service.unfriend(user["username"], req.username)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/friends")
def list_friends(user: dict = Depends(get_current_user)):
    usernames = friendship_service.get_friends(user["username"])
    enriched = []
    for un in usernames:
        p = profile_service.get_public(un)
        enriched.append({
            "username": un,
            "display_name": p.get("display_name", un) if p else un,
            "avatar": p.get("avatar", "👤") if p else "👤",
            "avatar_url": p.get("avatar_url") if p else None,
            "bio": p.get("bio", "") if p else "",
        })
    return {"friends": enriched}


@router.get("/friends/requests")
def list_requests(user: dict = Depends(get_current_user)):
    return friendship_service.get_pending_requests(user["username"])


@router.get("/friends/search")
def search_users(q: str = Query(""), user: dict = Depends(get_current_user)):
    results = friendship_service.search_users(q)
    # Filter out existing friends and self
    friends = friendship_service.get_friends(user["username"])
    results = [r for r in results if r["username"] not in friends and r["username"] != user["username"]]
    return {"results": results}
