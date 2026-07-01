import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from api.auth import get_current_user
from services import messaging_service, friendship_service

router = APIRouter()


class CreateConversationRequest(BaseModel):
    participant: str


class SendMessageRequest(BaseModel):
    text: str


@router.get("/chat/conversations")
def list_conversations(user: dict = Depends(get_current_user)):
    convs = messaging_service.get_user_conversations(user["username"])
    return {"conversations": convs}


@router.post("/chat/conversations")
def create_conversation(req: CreateConversationRequest, user: dict = Depends(get_current_user)):
    if req.participant == user["username"]:
        raise HTTPException(status_code=400, detail="Cannot chat with yourself")
    if not friendship_service.are_friends(user["username"], req.participant):
        raise HTTPException(status_code=403, detail="Must be friends to chat")
    conv = messaging_service.create_conversation([user["username"], req.participant])
    return {"status": "ok", "conversation": conv}


@router.get("/chat/conversations/{conv_id}/messages")
def get_messages(conv_id: str, before: str = Query(""), user: dict = Depends(get_current_user)):
    convs = messaging_service.get_user_conversations(user["username"])
    conv = next((c for c in convs if c["id"] == conv_id), None)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msgs = messaging_service.get_messages(conv_id, before_id=before or None)
    return {"messages": msgs}


@router.post("/chat/conversations/{conv_id}/messages")
def send_message(conv_id: str, req: SendMessageRequest, user: dict = Depends(get_current_user)):
    msg = messaging_service.add_message(conv_id, user["username"], req.text)
    if not msg:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "ok", "message": msg}


@router.post("/chat/conversations/{conv_id}/read")
def mark_read(conv_id: str, user: dict = Depends(get_current_user)):
    messaging_service.mark_read(conv_id, user["username"])
    return {"status": "ok"}


@router.get("/chat/conversations/{conv_id}/subscribe")
async def subscribe(conv_id: str, user: str = Query(...), user_auth: dict = Depends(get_current_user)):
    """SSE endpoint — polls for new messages and pushes them."""
    async def event_stream():
        last_id = None
        # Get current last message id to start from
        msgs = messaging_service.get_messages(conv_id, limit=1)
        if msgs:
            last_id = msgs[-1]["id"]
        while True:
            try:
                new_msgs = messaging_service.subscribe_poll(conv_id, user, since_msg_id=last_id)
                for m in new_msgs:
                    last_id = m["id"]
                    yield f"data: {json.dumps({'type': 'message', 'from': m['from'], 'text': m['text'], 'id': m['id'], 'created_at': m['created_at']})}\n\n"
                await asyncio.sleep(1.5)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(3)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
