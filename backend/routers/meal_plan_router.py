"""Meal plan / Wochenplan routes."""
from datetime import datetime, timezone
from typing import List, Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import uuid
from db import db, recipes, pantry_items, shopping_items
from auth import get_current_user
from routers.shopping_router import round_up_to_pack

router = APIRouter(prefix="/api/meal-plan", tags=["meal-plan"])

meal_plans = db.meal_plans

MealType = Literal["fruehstueck", "mittag", "abend", "snack"]


class MealPlanEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    date: str  # ISO YYYY-MM-DD
    meal_type: MealType
    recipe_id: Optional[str] = None
    custom_title: Optional[str] = None
    servings: int = 2
    note: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MealPlanCreate(BaseModel):
    date: str
    meal_type: MealType
    recipe_id: Optional[str] = None
    custom_title: Optional[str] = None
    servings: int = 2
    note: Optional[str] = None


class MealPlanUpdate(BaseModel):
    date: Optional[str] = None
    meal_type: Optional[MealType] = None
    recipe_id: Optional[str] = None
    custom_title: Optional[str] = None
    servings: Optional[int] = None
    note: Optional[str] = None


@router.get("")
async def list_plan(
    start_date: str = Query(..., description="ISO YYYY-MM-DD"),
    end_date: str = Query(..., description="ISO YYYY-MM-DD"),
    user: dict = Depends(get_current_user),
):
    docs = await meal_plans.find(
        {"user_id": user["id"], "date": {"$gte": start_date, "$lte": end_date}},
        {"_id": 0},
    ).sort("date", 1).to_list(500)

    # Hydrate with recipe snapshots
    rid_set = {d["recipe_id"] for d in docs if d.get("recipe_id")}
    recipe_map = {}
    if rid_set:
        async for r in recipes.find({"id": {"$in": list(rid_set)}}, {"_id": 0, "id": 1, "title": 1, "image_url": 1, "cook_time_min": 1, "category": 1, "servings": 1}):
            recipe_map[r["id"]] = r
    for d in docs:
        d["recipe"] = recipe_map.get(d.get("recipe_id")) if d.get("recipe_id") else None
    return docs


@router.post("", response_model=MealPlanEntry)
async def create_entry(body: MealPlanCreate, user: dict = Depends(get_current_user)):
    if body.recipe_id:
        if not await recipes.find_one({"id": body.recipe_id}, {"_id": 0, "id": 1}):
            raise HTTPException(status_code=404, detail="Rezept nicht gefunden")
    entry = MealPlanEntry(user_id=user["id"], **body.model_dump())
    await meal_plans.insert_one(entry.model_dump())
    return entry


@router.patch("/{entry_id}", response_model=MealPlanEntry)
async def update_entry(entry_id: str, body: MealPlanUpdate, user: dict = Depends(get_current_user)):
    patch = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not patch:
        raise HTTPException(status_code=400, detail="Keine Änderungen")
    res = await meal_plans.update_one({"id": entry_id, "user_id": user["id"]}, {"$set": patch})
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
    doc = await meal_plans.find_one({"id": entry_id}, {"_id": 0})
    return MealPlanEntry(**doc)


@router.delete("/{entry_id}")
async def delete_entry(entry_id: str, user: dict = Depends(get_current_user)):
    res = await meal_plans.delete_one({"id": entry_id, "user_id": user["id"]})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Generate shopping list from meal plan range
# ---------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    start_date: str
    end_date: str
    deduct_pantry: bool = True


def _norm(s: str) -> str:
    return (s or "").strip().lower()


@router.post("/generate-shopping-list")
async def generate_shopping_list(body: GenerateRequest, user: dict = Depends(get_current_user)):
    plan_docs = await meal_plans.find(
        {"user_id": user["id"], "date": {"$gte": body.start_date, "$lte": body.end_date}, "recipe_id": {"$ne": None}},
        {"_id": 0},
    ).to_list(500)

    if not plan_docs:
        return {"added": 0, "merged": 0, "skipped_pantry": 0, "items": []}

    # Aggregate ingredients across all planned recipes (factor by servings)
    needed: dict[str, dict] = {}
    for entry in plan_docs:
        r = await recipes.find_one({"id": entry["recipe_id"]}, {"_id": 0})
        if not r:
            continue
        base_serv = max(1, r.get("servings", 2) or 2)
        factor = (entry.get("servings", 2) or 2) / base_serv
        for ing in r.get("ingredients", []) or []:
            name = (ing.get("name") or "").strip()
            if not name:
                continue
            unit = (ing.get("unit") or "").strip()
            key = f"{_norm(name)}|{_norm(unit)}"
            amount = (ing.get("amount") or 0) * factor
            if key in needed:
                needed[key]["amount"] += amount
            else:
                needed[key] = {"name": name, "unit": unit, "amount": round(amount, 2)}

    # Optionally deduct pantry stock
    skipped = 0
    if body.deduct_pantry:
        pantry = await pantry_items.find({}, {"_id": 0}).to_list(2000)
        for p in pantry:
            pname = _norm(p.get("name", ""))
            punit = _norm(p.get("unit", ""))
            avail = p.get("amount", 0) or 0
            for key, n in list(needed.items()):
                if _norm(n["name"]) == pname and _norm(n["unit"]) == punit:
                    if avail >= n["amount"]:
                        del needed[key]
                        skipped += 1
                    else:
                        n["amount"] = round(n["amount"] - avail, 2)
                    break

    # Add to shopping list (merge with existing not-checked items by name+unit)
    existing = await shopping_items.find({"checked": False}, {"_id": 0}).to_list(2000)
    existing_idx = {f"{_norm(e['name'])}|{_norm(e.get('unit',''))}": e for e in existing}

    added, merged = 0, 0
    new_items = []
    for key, n in needed.items():
        if n["amount"] <= 0:
            continue
        # Round up to next typical pack size if the catalog has the product.
        n["amount"], _rounded = await round_up_to_pack(n["name"], n["unit"], n["amount"])
        if key in existing_idx:
            ex = existing_idx[key]
            new_amount = round((ex.get("amount") or 0) + n["amount"], 2)
            await shopping_items.update_one({"id": ex["id"]}, {"$set": {"amount": new_amount, "source": "wochenplan"}})
            merged += 1
        else:
            doc = {
                "id": str(uuid.uuid4()),
                "name": n["name"],
                "amount": n["amount"],
                "unit": n["unit"],
                "category": "",
                "checked": False,
                "source": "wochenplan",
                "note": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "checked_at": None,
            }
            await shopping_items.insert_one(doc.copy())
            new_items.append(doc)
            added += 1

    return {"added": added, "merged": merged, "skipped_pantry": skipped, "items": new_items}
