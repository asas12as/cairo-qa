import json
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

router = APIRouter()
security = HTTPBearer()

from core import data_path

USERS_FILE = data_path("admin", "users.json")
SECRET = "cairo-qa-jwt-secret-key-2026-32bytes!"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


def _load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_users(users: dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def _ensure_admin():
    users = _load_users()
    if "admin" not in users:
        pw_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
        users["admin"] = {
            "password": pw_hash,
            "email": "admin@cairoqa.com",
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_users(users)


_ensure_admin()


def create_token(username: str, role: str) -> str:
    payload = {
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    return verify_token(credentials.credentials)


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.post("/register")
def register(req: RegisterRequest):
    users = _load_users()
    if req.username in users:
        raise HTTPException(status_code=400, detail="Username already exists")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password too short")
    pw_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    users[req.username] = {
        "password": pw_hash,
        "email": req.email,
        "role": "user",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_users(users)
    token = create_token(req.username, "user")
    return TokenResponse(access_token=token, username=req.username, role="user")


@router.post("/login")
def login(req: LoginRequest):
    users = _load_users()
    user = users.get(req.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not bcrypt.checkpw(req.password.encode(), user["password"].encode()):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_token(req.username, user["role"])
    return TokenResponse(access_token=token, username=req.username, role=user["role"])


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {"username": user["username"], "role": user["role"]}
