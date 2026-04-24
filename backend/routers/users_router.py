"""User management routes (admin only for list/edit)."""
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from db import users
from auth import require_admin, get_current_user
from models import UserPublic

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=List[UserPublic])
async def list_users(_: dict = Depends(require_admin)):
    docs = await users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return [UserPublic(**d) for d in docs]


@router.patch("/{user_id}", response_model=UserPublic)
async def update_user(user_id: str, patch: dict, admin: dict = Depends(require_admin)):
    allowed = {"name", "role", "active", "allergies", "diet"}
    update = {k: v for k, v in patch.items() if k in allowed}
    if not update:
        raise HTTPException(status_code=400, detail="Keine gültigen Felder")
    await users.update_one({"id": user_id}, {"$set": update})
    doc = await users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    return UserPublic(**doc)


@router.delete("/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Eigenen Account kann man nicht löschen")
    await users.delete_one({"id": user_id})
    return {"ok": True}


@router.patch("/me/profile", response_model=UserPublic)
async def update_my_profile(patch: dict, user: dict = Depends(get_current_user)):
    allowed = {"name", "allergies", "diet"}
    update = {k: v for k, v in patch.items() if k in allowed}
    if update:
        await users.update_one({"id": user["id"]}, {"$set": update})
    doc = await users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return UserPublic(**doc)
