"""Recipe routes."""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from db import recipes
from auth import get_current_user
from models import Recipe, RecipeCreate, RecipeUpdate

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


@router.get("", response_model=List[Recipe])
async def list_recipes(
    user: dict = Depends(get_current_user),
    search: Optional[str] = None,
    category: Optional[str] = None,
    favorite: Optional[bool] = None,
):
    query = {}
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"tags": {"$regex": search, "$options": "i"}},
        ]
    if category:
        query["category"] = category
    if favorite is not None:
        query["favorite"] = favorite
    docs = await recipes.find(query, {"_id": 0}).sort("updated_at", -1).to_list(500)
    return [Recipe(**d) for d in docs]


@router.post("", response_model=Recipe)
async def create_recipe(body: RecipeCreate, user: dict = Depends(get_current_user)):
    r = Recipe(**body.model_dump(), owner_id=user["id"])
    await recipes.insert_one(r.model_dump())
    return r


@router.get("/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: str, user: dict = Depends(get_current_user)):
    doc = await recipes.find_one({"id": recipe_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Rezept nicht gefunden")
    return Recipe(**doc)


@router.patch("/{recipe_id}", response_model=Recipe)
async def update_recipe(recipe_id: str, body: RecipeUpdate, user: dict = Depends(get_current_user)):
    patch = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    # allow explicit null for cook_time_min etc. - simplified
    if not patch:
        raise HTTPException(status_code=400, detail="Keine Änderungen")
    patch["updated_at"] = datetime.now(timezone.utc).isoformat()
    # ingredients need dump
    if "ingredients" in patch:
        patch["ingredients"] = [i.model_dump() if hasattr(i, "model_dump") else i for i in patch["ingredients"]]
    await recipes.update_one({"id": recipe_id}, {"$set": patch})
    doc = await recipes.find_one({"id": recipe_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Rezept nicht gefunden")
    return Recipe(**doc)


@router.delete("/{recipe_id}")
async def delete_recipe(recipe_id: str, user: dict = Depends(get_current_user)):
    res = await recipes.delete_one({"id": recipe_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rezept nicht gefunden")
    return {"ok": True}


@router.post("/{recipe_id}/favorite", response_model=Recipe)
async def toggle_favorite(recipe_id: str, user: dict = Depends(get_current_user)):
    doc = await recipes.find_one({"id": recipe_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Rezept nicht gefunden")
    new_val = not doc.get("favorite", False)
    await recipes.update_one({"id": recipe_id}, {"$set": {"favorite": new_val, "updated_at": datetime.now(timezone.utc).isoformat()}})
    doc["favorite"] = new_val
    return Recipe(**doc)
