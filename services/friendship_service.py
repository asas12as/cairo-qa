import json
import os
import uuid
from datetime import datetime, timezone

from core import data_path

REQUESTS_FILE = data_path("friendships", "requests.json")
FRIENDS_FILE = data_path("friendships", "friends.json")
os.makedirs(os.path.dirname(REQUESTS_FILE), exist_ok=True)


def _load_requests() -> list[dict]:
    if not os.path.exists(REQUESTS_FILE):
        return []
    try:
        with open(REQUESTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_requests(requests: list[dict]):
    with open(REQUESTS_FILE, "w", encoding="utf-8") as f:
        json.dump(requests, f, indent=2, ensure_ascii=False)


def _load_friends() -> dict[str, list[str]]:
    if not os.path.exists(FRIENDS_FILE):
        return {}
    try:
        with open(FRIENDS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_friends(friends: dict[str, list[str]]):
    with open(FRIENDS_FILE, "w", encoding="utf-8") as f:
        json.dump(friends, f, indent=2, ensure_ascii=False)


def _add_friend_edge(a: str, b: str):
    friends = _load_friends()
    friends.setdefault(a, [])
    friends.setdefault(b, [])
    if b not in friends[a]:
        friends[a].append(b)
    if a not in friends[b]:
        friends[b].append(a)
    _save_friends(friends)


def _remove_friend_edge(a: str, b: str):
    friends = _load_friends()
    if a in friends and b in friends[a]:
        friends[a].remove(b)
    if b in friends and a in friends[b]:
        friends[b].remove(a)
    _save_friends(friends)


def are_friends(a: str, b: str) -> bool:
    friends = _load_friends()
    return b in friends.get(a, [])


def send_request(from_user: str, to_user: str) -> dict:
    requests = _load_requests()
    if are_friends(from_user, to_user):
        return {"error": "Already friends"}
    for r in requests:
        if r["status"] == "pending":
            if r["from_user"] == from_user and r["to_user"] == to_user:
                return {"error": "Request already sent"}
            if r["from_user"] == to_user and r["to_user"] == from_user:
                return {"error": "They already sent you a request"}
    req = {
        "id": str(uuid.uuid4()),
        "from_user": from_user,
        "to_user": to_user,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    requests.append(req)
    _save_requests(requests)
    return {"status": "sent", "request": req}


def accept_request(request_id: str, user: str) -> dict:
    requests = _load_requests()
    for r in requests:
        if r["id"] == request_id and r["to_user"] == user and r["status"] == "pending":
            r["status"] = "accepted"
            _add_friend_edge(r["from_user"], r["to_user"])
            _save_requests(requests)
            return {"status": "accepted", "friend": r["from_user"]}
    return {"error": "Request not found"}


def reject_request(request_id: str, user: str) -> dict:
    requests = _load_requests()
    for r in requests:
        if r["id"] == request_id and r["to_user"] == user and r["status"] == "pending":
            r["status"] = "rejected"
            _save_requests(requests)
            return {"status": "rejected"}
    return {"error": "Request not found"}


def unfriend(a: str, b: str) -> dict:
    if not are_friends(a, b):
        return {"error": "Not friends"}
    _remove_friend_edge(a, b)
    return {"status": "unfriended"}


def get_friends(username: str) -> list[str]:
    friends = _load_friends()
    return friends.get(username, [])


def get_pending_requests(username: str) -> dict:
    requests = _load_requests()
    incoming = [r for r in requests if r["to_user"] == username and r["status"] == "pending"]
    outgoing = [r for r in requests if r["from_user"] == username and r["status"] == "pending"]
    return {"incoming": incoming, "outgoing": outgoing}


def search_users(query: str) -> list[dict]:
    import json
    users_file = data_path("admin", "users.json")
    if not os.path.exists(users_file):
        return []
    with open(users_file, encoding="utf-8") as f:
        users = json.load(f)
    q = query.lower()
    results = []
    for username, data in users.items():
        if username == "admin":
            continue
        if q in username.lower():
            results.append({
                "username": username,
                "role": data.get("role", "user"),
                "created_at": data.get("created_at", ""),
            })
    return results[:20]
