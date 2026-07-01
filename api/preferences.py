"""User preference endpoints."""
from fastapi import APIRouter, Query

from agent.user_preferences import PREFERENCE_QUESTIONS
from models.schemas import PreferencesCheckResponse, PreferencesSaveRequest
from core import ctx

router = APIRouter()


@router.get("/preferences/check", response_model=PreferencesCheckResponse)
async def check(user_id: str = Query(...)):
    profile = ctx.prefs.get(user_id)
    if profile:
        return PreferencesCheckResponse(has_preferences=True, questions=None)
    return PreferencesCheckResponse(has_preferences=False, questions=PREFERENCE_QUESTIONS)


@router.post("/preferences/save")
async def save(req: PreferencesSaveRequest):
    profile = ctx.prefs.save(req.user_id, req.answers)
    return {"status": "ok", "profile": profile}
