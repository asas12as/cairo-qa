"""Chat & streaming endpoints."""
import json

from fastapi import APIRouter, Query
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from models.schemas import AskRequest, AskResponse
from services.chat_service import handle_question, handle_question_stream

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    return handle_question(req.user_id, req.question)


@router.get("/ask/stream")
async def ask_stream(
    question: str = Query(..., description="Your question about Cairo places"),
    user_id: str | None = Query(None),
    companion_ids: str = Query("", description="Comma-separated companion usernames"),
):
    cids = [c.strip() for c in companion_ids.split(",") if c.strip()] if companion_ids else None
    return StreamingResponse(
        handle_question_stream(user_id, question, companion_ids=cids),
        media_type="text/event-stream",
    )
