"""Recipe routes."""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from db import recipes, db
from auth import get_current_user, require_admin
from models import Recipe, RecipeCreate, RecipeUpdate
from recipe_import_service import import_from_url, fetch_lidl_category_index, search_lidl_kochen, RecipeImportError

router = APIRouter(prefix="/api/recipes", tags=["recipes"])

external_recipes = db.external_recipes


class ImportUrlRequest(BaseModel):
    url: str


class ImportUrlPreview(BaseModel):
    title: str
    description: str = ""
    category: str = ""
    tags: List[str] = []
    servings: int = 4
    cook_time_min: Optional[int] = None
    difficulty: Optional[str] = None
    ingredients: list
    steps: List[str]
    image_url: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None


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



# ---------------------------------------------------------------------------
# Import from external URL
# ---------------------------------------------------------------------------
@router.post("/preview-url", response_model=ImportUrlPreview)
async def preview_from_url(body: ImportUrlRequest, user: dict = Depends(get_current_user)):
    try:
        parsed = await import_from_url(body.url)
    except RecipeImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Fehler beim Laden: {exc}")
    return ImportUrlPreview(**parsed)


@router.post("/import-url", response_model=Recipe)
async def import_from_url_endpoint(body: ImportUrlRequest, user: dict = Depends(get_current_user)):
    try:
        parsed = await import_from_url(body.url)
    except RecipeImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Fehler beim Laden: {exc}")

    # Deduplicate by source (e.g. "lidl:<slug>") for the user
    existing = await recipes.find_one(
        {"source": parsed.get("source"), "owner_id": user["id"]},
        {"_id": 0},
    )
    if existing:
        return Recipe(**existing)

    payload = {
        "title": parsed["title"],
        "description": parsed.get("description") or "",
        "category": parsed.get("category") or "",
        "tags": parsed.get("tags") or [],
        "servings": parsed.get("servings") or 4,
        "cook_time_min": parsed.get("cook_time_min"),
        "difficulty": parsed.get("difficulty"),
        "ingredients": parsed.get("ingredients") or [],
        "steps": parsed.get("steps") or [],
        "image_url": parsed.get("image_url"),
        "source": parsed.get("source") or "import",
    }
    r = Recipe(**payload, owner_id=user["id"])
    await recipes.insert_one(r.model_dump())
    return r


# ---------------------------------------------------------------------------
# External catalog (rezepte.lidl.ch search)
# ---------------------------------------------------------------------------
@router.get("/external/search")
async def external_search(
    q: str = Query("", description="Suchbegriff"),
    limit: int = 20,
    user: dict = Depends(get_current_user),
):
    """Combined search: cached Lidl-CH Monsieur Cuisine + live Lidl-DE (lidl-kochen.de)."""
    mongo_query: dict = {"source_name": "lidl_monsieur_cuisine"}
    if q.strip():
        mongo_query["title"] = {"$regex": q.strip(), "$options": "i"}
    cached = await external_recipes.find(mongo_query, {"_id": 0}).limit(limit).to_list(limit)
    for c in cached:
        c.setdefault("source_name", "lidl_monsieur_cuisine")

    live: list = []
    if q.strip():
        try:
            live = await search_lidl_kochen(q, per_page=limit)
        except Exception:
            live = []

    combined = cached + live
    return {"count": len(combined), "results": combined}


@router.get("/external/live-search")
async def external_live_search(
    q: str = Query(..., min_length=1),
    source: str = Query("lidl_kochen"),
    limit: int = 20,
    user: dict = Depends(get_current_user),
):
    if source != "lidl_kochen":
        raise HTTPException(status_code=400, detail="Unbekannte Quelle")
    try:
        results = await search_lidl_kochen(q, per_page=limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Suche fehlgeschlagen: {exc}")
    return {"count": len(results), "results": results}


@router.post("/external/refresh")
async def external_refresh(user: dict = Depends(require_admin)):
    try:
        items = await fetch_lidl_category_index()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Index-Aktualisierung fehlgeschlagen: {exc}")

    now = datetime.now(timezone.utc).isoformat()
    written = 0
    for it in items:
        doc = {
            **it,
            "source_name": "lidl_monsieur_cuisine",
            "indexed_at": now,
        }
        await external_recipes.update_one(
            {"source_name": doc["source_name"], "slug": doc["slug"]},
            {"$set": doc},
            upsert=True,
        )
        written += 1
    return {"ok": True, "indexed": written, "indexed_at": now}


@router.get("/external/status")
async def external_status(user: dict = Depends(get_current_user)):
    cnt = await external_recipes.count_documents({"source_name": "lidl_monsieur_cuisine"})
    latest = await external_recipes.find_one(
        {"source_name": "lidl_monsieur_cuisine"},
        {"_id": 0, "indexed_at": 1},
        sort=[("indexed_at", -1)],
    )
    return {
        "source": "rezepte.lidl.ch · Monsieur Cuisine Smart",
        "count": cnt,
        "last_indexed_at": latest.get("indexed_at") if latest else None,
    }
