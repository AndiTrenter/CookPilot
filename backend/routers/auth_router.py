"""Auth routes for CookPilot."""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from db import users, invites, get_settings
from models import LoginRequest, LoginResponse, UserPublic, AcceptInviteRequest, User
from auth import verify_password, create_token, hash_password, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _to_public(user: dict) -> UserPublic:
    return UserPublic(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        role=user["role"],
        active=user.get("active", True),
        allergies=user.get("allergies", []),
        diet=user.get("diet"),
    )


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    user = await users.find_one({"email": body.email.lower()}, {"_id": 0})
    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Ungültige Anmeldedaten")
    if not user.get("active", True):
        raise HTTPException(status_code=403, detail="Konto deaktiviert")
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Ungültige Anmeldedaten")
    token = create_token(user["id"], user["role"])
    return LoginResponse(token=token, user=_to_public(user))


@router.get("/me", response_model=UserPublic)
async def me(user: dict = Depends(get_current_user)):
    return _to_public(user)


@router.get("/invite/{token}")
async def preview_invite(token: str):
    inv = await invites.find_one({"token": token, "accepted": False}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Einladung nicht gefunden oder bereits benutzt")
    if inv["expires_at"] < datetime.now(timezone.utc).isoformat():
        raise HTTPException(status_code=410, detail="Einladung abgelaufen")
    return {"email": inv["email"], "role": inv["role"]}


@router.post("/accept-invite", response_model=LoginResponse)
async def accept_invite(body: AcceptInviteRequest):
    inv = await invites.find_one({"token": body.token, "accepted": False}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Einladung nicht gefunden oder bereits benutzt")
    if inv["expires_at"] < datetime.now(timezone.utc).isoformat():
        raise HTTPException(status_code=410, detail="Einladung abgelaufen")
    if await users.find_one({"email": inv["email"].lower()}, {"_id": 0}):
        raise HTTPException(status_code=409, detail="E-Mail ist bereits registriert")

    user = User(
        email=inv["email"].lower(),
        name=body.name,
        role=inv["role"],
        password_hash=hash_password(body.password),
    )
    doc = user.model_dump()
    await users.insert_one(doc.copy())
    await invites.update_one({"token": body.token}, {"$set": {"accepted": True}})
    token = create_token(user.id, user.role)
    return LoginResponse(token=token, user=_to_public(doc))
