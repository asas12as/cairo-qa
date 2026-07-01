import json
import os
import shutil

from core import data_path

PROFILES_DIR = data_path("profiles")
AVATARS_DIR = data_path("profiles", "avatars")
os.makedirs(PROFILES_DIR, exist_ok=True)
os.makedirs(AVATARS_DIR, exist_ok=True)

DEFAULT_PROFILE = {
    "display_name": "",
    "bio": "",
    "avatar_type": "emoji",
    "avatar": "👤",
    "avatar_url": None,
    "interests": [],
    "joined_at": "",
}


def _path(username: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in username)
    return os.path.join(PROFILES_DIR, f"{safe}.json")


def get(username: str) -> dict:
    path = _path(username)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def upsert(username: str, data: dict, joined_at: str = "") -> dict:
    existing = get(username) or {}
    existing.update({k: v for k, v in data.items() if v is not None})
    if joined_at and not existing.get("joined_at"):
        existing["joined_at"] = joined_at
    for k in ("display_name", "bio", "avatar_type", "avatar", "avatar_url", "interests"):
        existing.setdefault(k, DEFAULT_PROFILE[k])
    path = _path(username)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    return existing


def get_public(username: str) -> dict:
    p = get(username)
    if not p:
        return None
    return {
        "display_name": p.get("display_name", username),
        "avatar_type": p.get("avatar_type", "emoji"),
        "avatar": p.get("avatar", "👤"),
        "avatar_url": p.get("avatar_url"),
        "bio": p.get("bio", ""),
    }


def save_avatar(username: str, contents: bytes) -> str:
    ext = "png"
    fname = f"{username}.{ext}"
    dest = os.path.join(AVATARS_DIR, fname)
    with open(dest, "wb") as f:
        f.write(contents)
    return f"/avatars/{fname}"
