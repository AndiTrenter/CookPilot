"""Shopping list routes."""
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from db import shopping_items, recipes, pantry_items
from auth import get_current_user
from models import ShoppingItem, ShoppingItemCreate, ShoppingItemUpdate, AddRecipeIngredientsRequest

router = APIRouter(prefix="/api/shopping", tags=["shopping"])


def _norm(s: str) -> str:
    """Normalize a string for case-/whitespace-insensitive comparison."""
    return (s or "").strip().lower()


@router.get("", response_model=List[ShoppingItem])
async def list_items(user: dict = Depends(get_current_user)):
    docs = await shopping_items.find({}, {"_id": 0}).sort("created_at", 1).to_list(2000)
    return [ShoppingItem(**d) for d in docs]


@router.post("", response_model=ShoppingItem)
async def add_item(body: ShoppingItemCreate, user: dict = Depends(get_current_user)):
    item = ShoppingItem(**body.model_dump(), source="manuell")
    await shopping_items.insert_one(item.model_dump())
    return item


@router.patch("/{item_id}", response_model=ShoppingItem)
async def update_item(item_id: str, body: ShoppingItemUpdate, user: dict = Depends(get_current_user)):
    patch = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if "checked" in patch and patch["checked"]:
        patch["checked_at"] = datetime.now(timezone.utc).isoformat()
    await shopping_items.update_one({"id": item_id}, {"$set": patch})
    doc = await shopping_items.find_one({"id": item_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Artikel nicht gefunden")
    return ShoppingItem(**doc)


@router.post("/{item_id}/toggle", response_model=ShoppingItem)
async def toggle_item(item_id: str, user: dict = Depends(get_current_user)):
    doc = await shopping_items.find_one({"id": item_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Artikel nicht gefunden")
    new_val = not doc.get("checked", False)
    patch = {"checked": new_val}
    if new_val:
        patch["checked_at"] = datetime.now(timezone.utc).isoformat()
    else:
        patch["checked_at"] = None
    await shopping_items.update_one({"id": item_id}, {"$set": patch})
    doc.update(patch)
    return ShoppingItem(**doc)


@router.delete("/{item_id}")
async def delete_item(item_id: str, user: dict = Depends(get_current_user)):
    await shopping_items.delete_one({"id": item_id})
    return {"ok": True}


@router.post("/clear-checked")
async def clear_checked(user: dict = Depends(get_current_user)):
    res = await shopping_items.delete_many({"checked": True})
    return {"deleted": res.deleted_count}


@router.post("/from-recipe")
async def add_from_recipe(body: AddRecipeIngredientsRequest, user: dict = Depends(get_current_user)):
    recipe = await recipes.find_one({"id": body.recipe_id}, {"_id": 0})
    if not recipe:
        raise HTTPException(status_code=404, detail="Rezept nicht gefunden")

    base_servings = max(1, recipe.get("servings", 1) or 1)
    factor = (body.servings / base_servings) if body.servings else 1

    # Load existing unchecked items once and build a lookup by (name, unit)
    existing_docs = await shopping_items.find({"checked": False}, {"_id": 0}).to_list(2000)
    existing_idx = {f"{_norm(e.get('name',''))}|{_norm(e.get('unit',''))}": e for e in existing_docs}

    added, merged = 0, 0
    for ing in recipe.get("ingredients", []) or []:
        name = (ing.get("name") or "").strip()
        if not name:
            continue
        unit = (ing.get("unit") or "").strip()
        amount = round((ing.get("amount", 0) or 0) * factor, 2)
        key = f"{_norm(name)}|{_norm(unit)}"

        if key in existing_idx:
            ex = existing_idx[key]
            new_amount = round((ex.get("amount") or 0) + amount, 2)
            await shopping_items.update_one(
                {"id": ex["id"]},
                {"$set": {"amount": new_amount, "source": f"rezept:{recipe['id']}"}},
            )
            ex["amount"] = new_amount  # keep index in sync for repeated ingredients
            merged += 1
        else:
            item = ShoppingItem(
                name=name,
                amount=amount,
                unit=unit,
                source=f"rezept:{recipe['id']}",
            )
            doc = item.model_dump()
            await shopping_items.insert_one(doc.copy())
            existing_idx[key] = doc
            added += 1
    return {"added": added, "merged": merged}


@router.post("/from-low-stock")
async def add_from_low_stock(user: dict = Depends(get_current_user)):
    low = await pantry_items.find(
        {"$expr": {"$lt": ["$amount", "$min_amount"]}},
        {"_id": 0},
    ).to_list(1000)

    existing_docs = await shopping_items.find({"checked": False}, {"_id": 0}).to_list(2000)
    existing_idx = {f"{_norm(e.get('name',''))}|{_norm(e.get('unit',''))}": e for e in existing_docs}

    added, merged = 0, 0
    for p in low:
        diff = max(0, (p.get("min_amount", 0) or 0) - (p.get("amount", 0) or 0))
        if diff <= 0:
            continue
        name = (p.get("name") or "").strip()
        unit = (p.get("unit") or "").strip()
        key = f"{_norm(name)}|{_norm(unit)}"

        if key in existing_idx:
            ex = existing_idx[key]
            new_amount = round((ex.get("amount") or 0) + diff, 2)
            await shopping_items.update_one(
                {"id": ex["id"]},
                {"$set": {"amount": new_amount, "source": f"vorrat:{p['id']}"}},
            )
            ex["amount"] = new_amount
            merged += 1
        else:
            item = ShoppingItem(
                name=name,
                amount=round(diff, 2),
                unit=unit,
                category=p.get("category", ""),
                source=f"vorrat:{p['id']}",
            )
            doc = item.model_dump()
            await shopping_items.insert_one(doc.copy())
            existing_idx[key] = doc
            added += 1
    return {"added": added, "merged": merged}
