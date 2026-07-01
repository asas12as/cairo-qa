"""Admin CRUD routes — uses AppContext instead of module globals."""
import glob
import json
import os
from collections import Counter

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth import require_admin
from core import ctx, data_path

router = APIRouter()

USERS_FILE = data_path("admin", "users.json")
CONVERSATIONS_DIR = data_path("conversations")
PROFILES_DIR = data_path("user_profiles")


def _load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_users(users):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


# ---- Places CRUD ----

class PlaceCreate(BaseModel):
    category: str
    name: str
    neighborhood: str = ""
    address: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    rating: float = 0.0
    rating_count: int = 0
    genre_type: str = ""
    budget_level: str = ""
    budget_range_min: int = 0
    budget_range_max: int = 0
    work_hours: str = ""
    phone: str = ""
    notes: str = ""


class PlaceUpdate(BaseModel):
    category: str | None = None
    name: str | None = None
    neighborhood: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    rating: float | None = None
    rating_count: int | None = None
    genre_type: str | None = None
    budget_level: str | None = None
    budget_range_min: int | None = None
    budget_range_max: int | None = None
    work_hours: str | None = None
    phone: str | None = None
    notes: str | None = None


@router.get("/places")
def list_places(search: str = "", category: str = "", page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=500)):
    all_places = ctx.db.get_all()
    if search:
        s = search.lower()
        all_places = [p for p in all_places if s in (p.get("name") or "").lower()
                      or s in (p.get("neighborhood") or "").lower()
                      or s in (p.get("notes") or "").lower()]
    if category:
        c = category.lower()
        all_places = [p for p in all_places if (p.get("category") or "").lower() == c]
    total = len(all_places)
    start = (page - 1) * per_page
    end = start + per_page
    return {"total": total, "page": page, "per_page": per_page, "places": all_places[start:end]}


@router.get("/places/{place_id}")
def get_place(place_id: int):
    all_places = ctx.db.get_all()
    for p in all_places:
        if p.get("id") == place_id:
            return p
    raise HTTPException(status_code=404, detail="Place not found")


@router.post("/places")
def create_place(data: PlaceCreate, _=Depends(require_admin)):
    place_id = ctx.db.insert_place(data.model_dump())
    return {"status": "ok", "id": place_id}


@router.put("/places/{place_id}")
def update_place(place_id: int, data: PlaceUpdate, _=Depends(require_admin)):
    ctx.db.update_place(place_id, data.model_dump(exclude_none=True))
    return {"status": "ok"}


@router.delete("/places/{place_id}")
def delete_place(place_id: int, _=Depends(require_admin)):
    ctx.db.delete_place(place_id)
    return {"status": "ok", "deleted": place_id}


# ---- Users CRUD ----

@router.get("/users")
def list_users(_=Depends(require_admin)):
    users = _load_users()
    result = []
    for username, data in users.items():
        result.append({
            "username": username,
            "email": data.get("email", ""),
            "role": data.get("role", "user"),
            "created_at": data.get("created_at", ""),
        })
    return {"users": result}


class UserUpdate(BaseModel):
    email: str | None = None
    role: str | None = None
    new_password: str | None = None


@router.put("/users/{username}")
def update_user(username: str, data: UserUpdate, _=Depends(require_admin)):
    users = _load_users()
    if username not in users:
        raise HTTPException(status_code=404, detail="User not found")
    changed = []
    if data.email is not None:
        users[username]["email"] = data.email
        changed.append("email")
    if data.role is not None:
        if data.role not in ("user", "admin"):
            raise HTTPException(status_code=400, detail="Invalid role")
        users[username]["role"] = data.role
        changed.append("role")
    if data.new_password is not None and data.new_password.strip():
        if len(data.new_password) < 4:
            raise HTTPException(status_code=400, detail="Password too short")
        users[username]["password"] = bcrypt.hashpw(data.new_password.encode(), bcrypt.gensalt()).decode()
        changed.append("password")
    if changed:
        _save_users(users)
    return {"status": "ok", "changed": changed}


@router.delete("/users/{username}")
def delete_user(username: str, _=Depends(require_admin)):
    users = _load_users()
    if username not in users:
        raise HTTPException(status_code=404, detail="User not found")
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete admin")
    del users[username]
    _save_users(users)
    return {"status": "ok", "deleted": username}


# ---- Conversations ----

@router.get("/conversations")
def list_conversations(_=Depends(require_admin)):
    if not os.path.isdir(CONVERSATIONS_DIR):
        return {"conversations": []}
    entries = []
    for fname in sorted(os.listdir(CONVERSATIONS_DIR), reverse=True):
        if not fname.endswith(".jsonl"):
            continue
        fpath = os.path.join(CONVERSATIONS_DIR, fname)
        with open(fpath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        if len(entries) > 1000:
            break
    return {"conversations": entries[:500]}


@router.delete("/conversations/{conv_id}")
def delete_conversation(conv_id: str, _=Depends(require_admin)):
    deleted = 0
    if os.path.isdir(CONVERSATIONS_DIR):
        for fname in os.listdir(CONVERSATIONS_DIR):
            if not fname.endswith(".jsonl"):
                continue
            fpath = os.path.join(CONVERSATIONS_DIR, fname)
            lines = []
            with open(fpath, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            if entry.get("conversation_id") == conv_id:
                                deleted += 1
                                continue
                        except json.JSONDecodeError:
                            pass
                    lines.append(line)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "ok", "deleted_entries": deleted}


# ---- User Profiles ----

@router.get("/profiles")
def list_profiles(_=Depends(require_admin)):
    if not os.path.isdir(PROFILES_DIR):
        return {"profiles": []}
    result = []
    for fname in os.listdir(PROFILES_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(PROFILES_DIR, fname)
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            result.append({
                "username": fname[:-5],
                "traveler_type": data.get("traveler_type", ""),
                "budget_level": data.get("budget_level", ""),
                "vibe": data.get("vibe", ""),
                "updated_at": data.get("updated_at", ""),
            })
        except (json.JSONDecodeError, OSError):
            pass
    return {"profiles": result}


@router.delete("/profiles/{username}")
def delete_profile(username: str, _=Depends(require_admin)):
    fpath = os.path.join(PROFILES_DIR, f"{username}.json")
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Profile not found")
    os.remove(fpath)
    return {"status": "ok", "deleted": username}


# ---- Feedback ----

@router.get("/feedback")
def list_feedback(_=Depends(require_admin)):
    feedback = []
    if os.path.isdir(CONVERSATIONS_DIR):
        for fname in sorted(os.listdir(CONVERSATIONS_DIR), reverse=True):
            if not fname.endswith(".jsonl"):
                continue
            fpath = os.path.join(CONVERSATIONS_DIR, fname)
            with open(fpath, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            if entry.get("feedback_rating") or entry.get("corrected_answer"):
                                feedback.append(entry)
                        except json.JSONDecodeError:
                            pass
            if len(feedback) > 500:
                break
    return {"feedback": feedback[:200]}


# ---- Project Feedback ----

PROJECT_FEEDBACK_FILE = data_path("project_feedback.json")


@router.get("/project-feedback")
def list_project_feedback(_=Depends(require_admin)):
    if not os.path.exists(PROJECT_FEEDBACK_FILE):
        return {"feedback": [], "total": 0, "average_rating": 0, "distribution": {}}
    with open(PROJECT_FEEDBACK_FILE, encoding="utf-8") as f:
        try:
            entries = json.load(f)
        except json.JSONDecodeError:
            return {"feedback": [], "total": 0, "average_rating": 0, "distribution": {}}
    ratings = [e["rating"] for e in entries if e.get("rating")]
    avg = round(sum(ratings) / len(ratings), 2) if ratings else 0
    dist = {str(i): sum(1 for e in entries if e.get("rating") == i) for i in range(1, 6)}
    return {
        "feedback": entries,
        "total": len(entries),
        "average_rating": avg,
        "distribution": dist,
    }


@router.delete("/project-feedback/{index}")
def delete_project_feedback(index: int, _=Depends(require_admin)):
    if not os.path.exists(PROJECT_FEEDBACK_FILE):
        raise HTTPException(status_code=404, detail="No feedback found")
    with open(PROJECT_FEEDBACK_FILE, encoding="utf-8") as f:
        try:
            entries = json.load(f)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Corrupt feedback file")
    if index < 0 or index >= len(entries):
        raise HTTPException(status_code=404, detail="Feedback entry not found")
    entries.pop(index)
    with open(PROJECT_FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    return {"status": "ok", "deleted": True}


@router.get("/conversations/user/{username}")
def get_user_conversations(username: str, _=Depends(require_admin)):
    pattern = os.path.join(CONVERSATIONS_DIR, "*.jsonl")
    entries = []
    for fpath in sorted(glob.glob(pattern), reverse=True):
        with open(fpath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("user_id") == username or entry.get("username") == username:
                        entries.append(entry)
                except json.JSONDecodeError:
                    pass
    return {"conversations": entries[:200]}


@router.get("/activity")
def activity_stats(_=Depends(require_admin)):
    pattern = os.path.join(CONVERSATIONS_DIR, "*.jsonl")
    user_counts = Counter()
    total = 0
    for fpath in glob.glob(pattern):
        with open(fpath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    uid = entry.get("user_id") or entry.get("username") or "unknown"
                    user_counts[uid] += 1
                    total += 1
                except json.JSONDecodeError:
                    pass
    top = [{"username": u, "count": c} for u, c in user_counts.most_common(20)]
    return {"total_conversations": total, "unique_users": len(user_counts), "top_users": top}


# ---- Stats ----

@router.get("/stats")
def admin_stats(_=Depends(require_admin)):
    places = ctx.db.get_all()
    cats = Counter(p.get("category", "Unknown") for p in places)
    budgets = Counter(p.get("budget_level", "Unknown") for p in places)
    ratings = [p.get("rating") for p in places if p.get("rating")]
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0
    total_convos = sum(
        1 for fname in os.listdir(CONVERSATIONS_DIR) if fname.endswith(".jsonl")
        for _ in open(os.path.join(CONVERSATIONS_DIR, fname), encoding="utf-8")
    ) if os.path.isdir(CONVERSATIONS_DIR) else 0
    users = _load_users()
    profile_count = len([f for f in os.listdir(PROFILES_DIR) if f.endswith(".json")]) if os.path.isdir(PROFILES_DIR) else 0
    pf_count = 0
    if os.path.exists(PROJECT_FEEDBACK_FILE):
        with open(PROJECT_FEEDBACK_FILE, encoding="utf-8") as f:
            try:
                pf_count = len(json.load(f))
            except json.JSONDecodeError:
                pass
    return {
        "total_places": len(places),
        "total_conversations": total_convos,
        "total_users": len(users),
        "total_profiles": profile_count,
        "project_feedback_count": pf_count,
        "categories": dict(cats),
        "budget_distribution": dict(budgets),
        "avg_rating": avg_rating,
    }
