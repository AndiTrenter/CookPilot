"""Chat routes (AI Küchenassistent)."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from db import chat_sessions, chat_messages, pantry_items, recipes
from auth import get_current_user
from models import ChatSession, ChatMessage, ChatSendRequest
from llm_service import chat_completion, build_system_prompt, LLMNotConfigured

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/sessions", response_model=List[ChatSession])
async def list_sessions(user: dict = Depends(get_current_user)):
    docs = await chat_sessions.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [ChatSession(**d) for d in docs]


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessage])
async def session_messages(session_id: str, user: dict = Depends(get_current_user)):
    docs = await chat_messages.find({"session_id": session_id, "user_id": user["id"]}, {"_id": 0}).sort("created_at", 1).to_list(500)
    return [ChatMessage(**d) for d in docs]


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user: dict = Depends(get_current_user)):
    await chat_sessions.delete_one({"id": session_id, "user_id": user["id"]})
    await chat_messages.delete_many({"session_id": session_id, "user_id": user["id"]})
    return {"ok": True}


@router.post("/send")
async def send(body: ChatSendRequest, user: dict = Depends(get_current_user)):
    session_id = body.session_id
    if not session_id:
        session = ChatSession(user_id=user["id"], title=body.message[:40])
        await chat_sessions.insert_one(session.model_dump())
        session_id = session.id

    # Build context
    pantry = await pantry_items.find({}, {"_id": 0}).to_list(200)
    recipes_count = await recipes.count_documents({})
    system_prompt = build_system_prompt(user, pantry, recipes_count)

    # Persist user message
    user_msg = ChatMessage(session_id=session_id, user_id=user["id"], role="user", content=body.message)
    await chat_messages.insert_one(user_msg.model_dump())

    # Last messages as history
    history_docs = await chat_messages.find(
        {"session_id": session_id, "user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", 1).to_list(30)
    history = [{"role": m["role"], "content": m["content"]} for m in history_docs[-20:-1]]  # exclude just-inserted

    try:
        reply = await chat_completion(system_prompt, history, body.message)
    except LLMNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"KI-Fehler: {exc}")

    assistant_msg = ChatMessage(session_id=session_id, user_id=user["id"], role="assistant", content=reply)
    await chat_messages.insert_one(assistant_msg.model_dump())

    return {"session_id": session_id, "reply": reply, "message_id": assistant_msg.id}
