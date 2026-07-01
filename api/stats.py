"""Stats & feedback endpoints."""
import json
import os
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from models.schemas import FeedbackRequest, StatsResponse
from core import ctx, data_path

router = APIRouter()


@router.post("/feedback")
async def feedback(req: FeedbackRequest):
    ctx.logger.log_feedback(req.conversation_id, req.rating, req.corrected_answer)
    return {"status": "ok"}


class ProjectFeedbackRequest(BaseModel):
    user_id: str = ""
    rating: int
    comment: str = ""


@router.post("/feedback/project")
async def project_feedback(req: ProjectFeedbackRequest):
    path = data_path("project_feedback.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    entries = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            try:
                entries = json.load(f)
            except json.JSONDecodeError:
                entries = []
    entries.append({
        "user_id": req.user_id,
        "rating": req.rating,
        "comment": req.comment,
        "created_at": datetime.now().isoformat(),
    })
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    return {"status": "ok"}


@router.get("/feedback/project")
async def get_project_feedback(user_id: str = ""):
    path = data_path("project_feedback.json")
    if not os.path.exists(path):
        return {"feedback": []}
    with open(path, encoding="utf-8") as f:
        try:
            entries = json.load(f)
        except json.JSONDecodeError:
            return {"feedback": []}
    if user_id:
        entries = [e for e in entries if e.get("user_id") == user_id]
    ratings = [e["rating"] for e in entries if e.get("rating")]
    avg = round(sum(ratings) / len(ratings), 2) if ratings else 0
    return {
        "feedback": entries,
        "total": len(entries),
        "average_rating": avg,
        "distribution": {str(i): sum(1 for e in entries if e.get("rating") == i) for i in range(1, 6)},
    }


@router.get("/stats", response_model=StatsResponse)
async def stats():
    llm = ctx.llm
    model_path = getattr(getattr(llm, 'config', None), 'path', getattr(llm, 'model', 'unknown')) if llm else "none"
    return StatsResponse(
        total_places=ctx.retriever.structured_db.count(),
        total_conversations=ctx.logger.count(),
        model_path=model_path,
    )
