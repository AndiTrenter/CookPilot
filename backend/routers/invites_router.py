"""Invite routes."""
import os
import re
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from db import invites, users, get_settings
from auth import require_admin
from models import Invite, InviteCreate
from email_service import send_email, build_invite_email

router = APIRouter(prefix="/api/invites", tags=["invites"])


def _resolve_public_base(request: Request) -> str:
    """Return the URL host where the app is reachable for invite links.

    Priority:
      1. ``COOKPILOT_PUBLIC_URL`` env, **if** it looks usable (not empty,
         not the template placeholder, not pointing at localhost/127.0.0.1).
      2. The host of the inbound request - works automatically when the
         admin opens CookPilot via its real URL (LAN-IP, mDNS, reverse proxy).
    """
    env = (os.environ.get("COOKPILOT_PUBLIC_URL") or "").strip().rstrip("/")
    bogus = (
        not env
        or "localhost" in env.lower()
        or "127.0.0.1" in env
        or re.search(r"://ip[:/]", env, re.IGNORECASE)  # template default "http://IP:8001"
    )
    if not bogus:
        return env

    # Derive from request: e.g. https://cookpilot.example.com or http://192.168.1.10:8010
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    return f"{scheme}://{host}".rstrip("/")


@router.post("", response_model=dict)
async def create_invite(body: InviteCreate, request: Request, admin: dict = Depends(require_admin)):
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
    public_url = _resolve_public_base(request)
    invite_url = f"{public_url}/invite/{token}"
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
