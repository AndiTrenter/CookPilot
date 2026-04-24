"""Invite routes."""
import os
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from db import invites, users, get_settings
from auth import require_admin
from models import Invite, InviteCreate
from email_service import send_email, build_invite_email

router = APIRouter(prefix="/api/invites", tags=["invites"])


@router.post("", response_model=dict)
async def create_invite(body: InviteCreate, admin: dict = Depends(require_admin)):
    existing = await users.find_one({"email": body.email.lower()}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=409, detail="E-Mail ist bereits registriert")

    # Invalidate any outstanding invites for that email
    await invites.update_many(
        {"email": body.email.lower(), "accepted": False},
        {"$set": {"accepted": True}},
    )

    token = secrets.token_urlsafe(32)
    inv = Invite(
        email=body.email.lower(),
        role=body.role,
        token=token,
        invited_by=admin["id"],
        expires_at=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
    )
    await invites.insert_one(inv.model_dump())

    settings = await get_settings()
    public_url = os.environ.get("COOKPILOT_PUBLIC_URL", "")
    invite_url = f"{public_url.rstrip('/')}/invite/{token}"
    html, text = build_invite_email(settings.get("app_name", "CookPilot"), invite_url, admin["name"])
    mailed = await send_email(body.email, "Einladung zu CookPilot", html, text)

    return {
        "ok": True,
        "invite_url": invite_url,
        "email_sent": mailed,
        "token": token,
        "expires_at": inv.expires_at,
    }


@router.get("")
async def list_invites(admin: dict = Depends(require_admin)):
    docs = await invites.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return docs


@router.delete("/{invite_id}")
async def delete_invite(invite_id: str, admin: dict = Depends(require_admin)):
    await invites.delete_one({"id": invite_id})
    return {"ok": True}
