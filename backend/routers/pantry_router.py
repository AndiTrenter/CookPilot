"""Pantry routes."""
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from db import pantry_items
from auth import get_current_user
from models import PantryItem, PantryItemCreate, PantryItemUpdate, PantryAdjust

router = APIRouter(prefix="/api/pantry", tags=["pantry"])


@router.get("", response_model=List[PantryItem])
async def list_items(user: dict = Depends(get_current_user)):
    docs = await pantry_items.find({}, {"_id": 0}).sort("name", 1).to_list(2000)
    return [PantryItem(**d) for d in docs]


@router.get("/low-stock", response_model=List[PantryItem])
async def low_stock(user: dict = Depends(get_current_user)):
    docs = await pantry_items.find(
        {"$expr": {"$lt": ["$amount", "$min_amount"]}},
        {"_id": 0},
    ).to_list(500)
    return [PantryItem(**d) for d in docs]


@router.post("", response_model=PantryItem)
async def add_item(body: PantryItemCreate, user: dict = Depends(get_current_user)):
    item = PantryItem(**body.model_dump())
    await pantry_items.insert_one(item.model_dump())
    return item


@router.patch("/{item_id}", response_model=PantryItem)
async def update_item(item_id: str, body: PantryItemUpdate, user: dict = Depends(get_current_user)):
    patch = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    patch["updated_at"] = datetime.now(timezone.utc).isoformat()
    await pantry_items.update_one({"id": item_id}, {"$set": patch})
    doc = await pantry_items.find_one({"id": item_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Artikel nicht gefunden")
    return PantryItem(**doc)


@router.post("/{item_id}/adjust", response_model=PantryItem)
async def adjust(item_id: str, body: PantryAdjust, user: dict = Depends(get_current_user)):
    doc = await pantry_items.find_one({"id": item_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Artikel nicht gefunden")
    new_amount = max(0, (doc.get("amount", 0) or 0) + body.delta)
    await pantry_items.update_one(
        {"id": item_id},
        {"$set": {"amount": new_amount, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    doc["amount"] = new_amount
    return PantryItem(**doc)


@router.delete("/{item_id}")
async def delete_item(item_id: str, user: dict = Depends(get_current_user)):
    await pantry_items.delete_one({"id": item_id})
    return {"ok": True}
