import json
import os
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from api.auth import get_current_user
from services import profile_service
from core import ctx, data_path

router = APIRouter()


class ProfileUpdate(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    avatar_type: str | None = None
    avatar: str | None = None
    interests: list[str] | None = None


@router.get("/profile")
def get_own_profile(user: dict = Depends(get_current_user)):
    username = user["username"]
    p = profile_service.get(username)
    if not p:
        users_file = data_path("admin", "users.json")
        joined_at = ""
        if os.path.exists(users_file):
            try:
                with open(users_file, encoding="utf-8") as f:
                    all_users = json.load(f)
                    joined_at = all_users.get(username, {}).get("created_at", "")
            except (json.JSONDecodeError, OSError):
                pass
        p = profile_service.upsert(username, {}, joined_at=joined_at)
    pref = ctx.prefs.get(username)
    return {
        "profile": p,
        "preferences": pref or {},
        "username": username,
        "role": user.get("role", "user"),
    }


@router.put("/profile")
def update_profile(req: ProfileUpdate, user: dict = Depends(get_current_user)):
    data = req.model_dump(exclude_none=True)
    p = profile_service.upsert(user["username"], data)
    return {"status": "ok", "profile": p}


@router.post("/profile/avatar")
def upload_avatar(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    contents = file.file.read()
    url = profile_service.save_avatar(user["username"], contents)
    profile_service.upsert(user["username"], {"avatar_url": url, "avatar_type": "image"})
    return {"status": "ok", "avatar_url": url}


@router.get("/profile/{username}")
def view_profile(username: str, user: dict = Depends(get_current_user)):
    if username == user["username"]:
        return get_own_profile(user)

    # Check friendship
    from services.friendship_service import are_friends
    is_friend = are_friends(user["username"], username)

    p = profile_service.get(username)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")

    pref = ctx.prefs.get(username) if is_friend else None

    if is_friend:
        return {
            "profile": p,
            "preferences": pref or {},
            "username": username,
            "relationship": "friend",
        }
    else:
        return {
            "profile": profile_service.get_public(username),
            "preferences": None,
            "username": username,
            "relationship": "stranger",
        }
