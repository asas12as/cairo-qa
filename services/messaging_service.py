import json
import os
import uuid
from datetime import datetime, timezone

from core import data_path

CONVERSATIONS_FILE = data_path("messages", "conversations.json")
MESSAGES_DIR = data_path("messages")
os.makedirs(MESSAGES_DIR, exist_ok=True)


def _load_conversations() -> list[dict]:
    if not os.path.exists(CONVERSATIONS_FILE):
        return []
    try:
        with open(CONVERSATIONS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_conversations(convs: list[dict]):
    with open(CONVERSATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(convs, f, indent=2, ensure_ascii=False)


def _messages_path(conv_id: str) -> str:
    return os.path.join(MESSAGES_DIR, f"{conv_id}.json")


def _load_messages(conv_id: str) -> list[dict]:
    path = _messages_path(conv_id)
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_messages(conv_id: str, msgs: list[dict]):
    with open(_messages_path(conv_id), "w", encoding="utf-8") as f:
        json.dump(msgs, f, indent=2, ensure_ascii=False)


def get_user_conversations(username: str) -> list[dict]:
    convs = _load_conversations()
    result = []
    for c in convs:
        if username in c.get("participants", []):
            result.append(c)
    result.sort(key=lambda x: x.get("last_message_at", ""), reverse=True)
    return result


def create_conversation(participants: list[str]) -> dict:
    convs = _load_conversations()
    # Check existing
    for c in convs:
        if sorted(c["participants"]) == sorted(participants):
            return c
    conv = {
        "id": str(uuid.uuid4()),
        "participants": participants,
        "last_message": None,
        "last_message_at": datetime.now(timezone.utc).isoformat(),
        "unread": {p: 0 for p in participants},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    convs.append(conv)
    _save_conversations(convs)
    _save_messages(conv["id"], [])
    return conv


def add_message(conv_id: str, from_user: str, text: str) -> dict:
    convs = _load_conversations()
    conv = None
    for c in convs:
        if c["id"] == conv_id:
            conv = c
            break
    if not conv:
        return None
    msg = {
        "id": str(uuid.uuid4()),
        "from": from_user,
        "text": text,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    msgs = _load_messages(conv_id)
    msgs.append(msg)
    _save_messages(conv_id, msgs)

    conv["last_message"] = {"from": from_user, "text": text, "created_at": msg["created_at"]}
    conv["last_message_at"] = msg["created_at"]
    for p in conv["participants"]:
        if p != from_user:
            conv["unread"][p] = conv["unread"].get(p, 0) + 1
        else:
            conv["unread"].setdefault(p, 0)
    _save_conversations(convs)
    return msg


def get_messages(conv_id: str, before_id: str = None, limit: int = 100) -> list[dict]:
    msgs = _load_messages(conv_id)
    if before_id:
        idx = next((i for i, m in enumerate(msgs) if m["id"] == before_id), len(msgs))
        msgs = msgs[:idx]
    return msgs[-limit:]


def mark_read(conv_id: str, username: str):
    convs = _load_conversations()
    for c in convs:
        if c["id"] == conv_id and username in c.get("participants", []):
            c["unread"][username] = 0
            _save_conversations(convs)
            return True
    return False


def subscribe_poll(conv_id: str, username: str, since_msg_id: str = None) -> list[dict]:
    """Return messages newer than since_msg_id (used by SSE endpoint)."""
    msgs = _load_messages(conv_id)
    if since_msg_id:
        idx = next((i for i, m in enumerate(msgs) if m["id"] == since_msg_id), -1)
        if idx >= 0:
            return msgs[idx + 1:]
    return msgs
