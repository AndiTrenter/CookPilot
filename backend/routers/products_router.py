"""Product catalog routes.

Provides a searchable list of common kitchen products with a sensible default
unit. Used by Pantry / Shopping / Recipe forms as autocomplete source so users
no longer have to type the unit manually for known items.
"""
from typing import List, Optional
from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from db import products
from auth import get_current_user, require_admin

router = APIRouter(prefix="/api/products", tags=["products"])


# ---------------------------------------------------------------------------
# Allowed units (frontend uses the same enum)
# ---------------------------------------------------------------------------
UNITS = [
    "g", "kg", "ml", "l", "Stk", "EL", "TL", "Prise", "Bund", "Zehe",
    "Pck", "Dose", "Glas", "Scheibe", "Becher",
]


class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    default_unit: str = ""
    category: str = ""
    aliases: List[str] = []
    pack_size: float = 0  # 0 = no rounding; otherwise round-up unit for shopping list
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProductCreate(BaseModel):
    name: str
    default_unit: str = ""
    category: str = ""
    aliases: List[str] = []
    pack_size: float = 0


@router.get("/units")
async def list_units(user: dict = Depends(get_current_user)):
    return {"units": UNITS}


@router.get("", response_model=List[Product])
async def list_products(
    search: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    query: dict = {}
    if search and search.strip():
        s = search.strip()
        query["$or"] = [
            {"name": {"$regex": s, "$options": "i"}},
            {"aliases": {"$elemMatch": {"$regex": s, "$options": "i"}}},
        ]
    docs = await products.find(query, {"_id": 0}).sort("name", 1).to_list(max(1, min(limit, 200)))
    return [Product(**d) for d in docs]


@router.post("", response_model=Product)
async def create_product(body: ProductCreate, admin: dict = Depends(require_admin)):
    if body.default_unit and body.default_unit not in UNITS:
        raise HTTPException(status_code=400, detail=f"Einheit '{body.default_unit}' ist nicht erlaubt")
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Name darf nicht leer sein")
    existing = await products.find_one(
        {"name": {"$regex": f"^{body.name.strip()}$", "$options": "i"}},
        {"_id": 0, "id": 1},
    )
    if existing:
        raise HTTPException(status_code=409, detail="Produkt existiert bereits")
    p = Product(**body.model_dump())
    await products.insert_one(p.model_dump())
    return p


@router.delete("/{product_id}")
async def delete_product(product_id: str, admin: dict = Depends(require_admin)):
    res = await products.delete_one({"id": product_id})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Nicht gefunden")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Seed catalog (idempotent - upserts by name, keeps user-modified entries)
# ---------------------------------------------------------------------------
SEED: list[dict] = [
    # Milchprodukte
    {"name": "Milch", "default_unit": "l", "category": "Milchprodukte", "pack_size": 1.0},
    {"name": "Butter", "default_unit": "g", "category": "Milchprodukte", "pack_size": 250},
    {"name": "Sahne", "default_unit": "ml", "category": "Milchprodukte", "aliases": ["Schlagsahne", "Rahm"], "pack_size": 200},
    {"name": "Quark", "default_unit": "g", "category": "Milchprodukte", "pack_size": 250},
    {"name": "Joghurt", "default_unit": "g", "category": "Milchprodukte", "pack_size": 500},
    {"name": "Frischkäse", "default_unit": "g", "category": "Milchprodukte", "pack_size": 200},
    {"name": "Mozzarella", "default_unit": "g", "category": "Milchprodukte", "pack_size": 125},
    {"name": "Parmesan", "default_unit": "g", "category": "Milchprodukte", "pack_size": 100},
    {"name": "Gouda", "default_unit": "g", "category": "Milchprodukte", "pack_size": 200},
    {"name": "Feta", "default_unit": "g", "category": "Milchprodukte", "pack_size": 200},
    {"name": "Schmand", "default_unit": "g", "category": "Milchprodukte", "pack_size": 200},
    {"name": "Crème fraîche", "default_unit": "g", "category": "Milchprodukte", "pack_size": 200},
    # Eier
    {"name": "Ei", "default_unit": "Stk", "category": "Milchprodukte", "aliases": ["Eier", "Hühnerei"], "pack_size": 10},
    # Backwaren / Mehl & Co.
    {"name": "Mehl", "default_unit": "g", "category": "Backen", "aliases": ["Weizenmehl"], "pack_size": 1000},
    {"name": "Zucker", "default_unit": "g", "category": "Backen", "pack_size": 1000},
    {"name": "Brauner Zucker", "default_unit": "g", "category": "Backen", "pack_size": 500},
    {"name": "Puderzucker", "default_unit": "g", "category": "Backen", "pack_size": 250},
    {"name": "Vanillezucker", "default_unit": "Pck", "category": "Backen", "pack_size": 1},
    {"name": "Backpulver", "default_unit": "Pck", "category": "Backen", "pack_size": 1},
    {"name": "Hefe", "default_unit": "Pck", "category": "Backen", "aliases": ["Trockenhefe"], "pack_size": 1},
    {"name": "Speisestärke", "default_unit": "g", "category": "Backen", "pack_size": 250},
    {"name": "Salz", "default_unit": "Prise", "category": "Gewürze"},
    {"name": "Pfeffer", "default_unit": "Prise", "category": "Gewürze"},
    {"name": "Paprikapulver", "default_unit": "TL", "category": "Gewürze"},
    {"name": "Curry", "default_unit": "TL", "category": "Gewürze"},
    {"name": "Kreuzkümmel", "default_unit": "TL", "category": "Gewürze"},
    {"name": "Oregano", "default_unit": "TL", "category": "Gewürze"},
    {"name": "Basilikum", "default_unit": "Bund", "category": "Gewürze", "pack_size": 1},
    {"name": "Petersilie", "default_unit": "Bund", "category": "Gewürze", "pack_size": 1},
    {"name": "Schnittlauch", "default_unit": "Bund", "category": "Gewürze", "pack_size": 1},
    {"name": "Thymian", "default_unit": "Bund", "category": "Gewürze", "pack_size": 1},
    {"name": "Rosmarin", "default_unit": "Bund", "category": "Gewürze", "pack_size": 1},
    # Öle / Saucen
    {"name": "Olivenöl", "default_unit": "ml", "category": "Öl & Essig", "pack_size": 500},
    {"name": "Sonnenblumenöl", "default_unit": "ml", "category": "Öl & Essig", "pack_size": 1000},
    {"name": "Rapsöl", "default_unit": "ml", "category": "Öl & Essig", "pack_size": 1000},
    {"name": "Essig", "default_unit": "ml", "category": "Öl & Essig", "aliases": ["Weißweinessig"], "pack_size": 500},
    {"name": "Balsamico", "default_unit": "ml", "category": "Öl & Essig", "pack_size": 500},
    {"name": "Sojasauce", "default_unit": "ml", "category": "Öl & Essig", "pack_size": 250},
    {"name": "Senf", "default_unit": "g", "category": "Öl & Essig", "pack_size": 250},
    {"name": "Ketchup", "default_unit": "ml", "category": "Öl & Essig", "pack_size": 500},
    # Fleisch / Fisch
    {"name": "Hackfleisch", "default_unit": "g", "category": "Fleisch", "aliases": ["Rinderhack", "Hack"], "pack_size": 500},
    {"name": "Hähnchenbrust", "default_unit": "g", "category": "Fleisch", "pack_size": 500},
    {"name": "Putenbrust", "default_unit": "g", "category": "Fleisch", "pack_size": 500},
    {"name": "Schweineschnitzel", "default_unit": "Stk", "category": "Fleisch", "pack_size": 4},
    {"name": "Speck", "default_unit": "g", "category": "Fleisch", "pack_size": 100},
    {"name": "Schinken", "default_unit": "Scheibe", "category": "Fleisch", "pack_size": 8},
    {"name": "Lachs", "default_unit": "g", "category": "Fisch", "pack_size": 200},
    {"name": "Thunfisch", "default_unit": "Dose", "category": "Fisch", "pack_size": 1},
    # Gemüse
    {"name": "Zwiebel", "default_unit": "Stk", "category": "Gemüse", "aliases": ["Zwiebeln"]},
    {"name": "Knoblauch", "default_unit": "Zehe", "category": "Gemüse"},
    {"name": "Tomate", "default_unit": "Stk", "category": "Gemüse", "aliases": ["Tomaten"]},
    {"name": "Tomaten passiert", "default_unit": "g", "category": "Gemüse", "aliases": ["passierte Tomaten"], "pack_size": 500},
    {"name": "Tomaten gehackt", "default_unit": "g", "category": "Gemüse", "aliases": ["gehackte Tomaten"], "pack_size": 400},
    {"name": "Paprika", "default_unit": "Stk", "category": "Gemüse"},
    {"name": "Karotte", "default_unit": "Stk", "category": "Gemüse", "aliases": ["Möhre", "Karotten", "Möhren"]},
    {"name": "Kartoffel", "default_unit": "kg", "category": "Gemüse", "aliases": ["Kartoffeln"], "pack_size": 2.5},
    {"name": "Süßkartoffel", "default_unit": "Stk", "category": "Gemüse"},
    {"name": "Zucchini", "default_unit": "Stk", "category": "Gemüse"},
    {"name": "Aubergine", "default_unit": "Stk", "category": "Gemüse"},
    {"name": "Champignons", "default_unit": "g", "category": "Gemüse", "aliases": ["Pilze"], "pack_size": 250},
    {"name": "Brokkoli", "default_unit": "Stk", "category": "Gemüse"},
    {"name": "Blumenkohl", "default_unit": "Stk", "category": "Gemüse"},
    {"name": "Spinat", "default_unit": "g", "category": "Gemüse", "pack_size": 250},
    {"name": "Salat", "default_unit": "Stk", "category": "Gemüse"},
    {"name": "Gurke", "default_unit": "Stk", "category": "Gemüse"},
    {"name": "Lauch", "default_unit": "Stk", "category": "Gemüse"},
    {"name": "Sellerie", "default_unit": "Stk", "category": "Gemüse"},
    {"name": "Ingwer", "default_unit": "g", "category": "Gemüse", "pack_size": 100},
    {"name": "Chili", "default_unit": "Stk", "category": "Gemüse"},
    # Obst
    {"name": "Apfel", "default_unit": "Stk", "category": "Obst", "aliases": ["Äpfel"]},
    {"name": "Banane", "default_unit": "Stk", "category": "Obst", "aliases": ["Bananen"]},
    {"name": "Zitrone", "default_unit": "Stk", "category": "Obst"},
    {"name": "Limette", "default_unit": "Stk", "category": "Obst"},
    {"name": "Orange", "default_unit": "Stk", "category": "Obst"},
    {"name": "Beeren", "default_unit": "g", "category": "Obst", "pack_size": 250},
    {"name": "Erdbeeren", "default_unit": "g", "category": "Obst", "pack_size": 500},
    # Trockenwaren / Pasta / Reis
    {"name": "Reis", "default_unit": "g", "category": "Trockenwaren", "pack_size": 1000},
    {"name": "Basmatireis", "default_unit": "g", "category": "Trockenwaren", "pack_size": 1000},
    {"name": "Risottoreis", "default_unit": "g", "category": "Trockenwaren", "pack_size": 500},
    {"name": "Spaghetti", "default_unit": "g", "category": "Pasta", "pack_size": 500},
    {"name": "Penne", "default_unit": "g", "category": "Pasta", "pack_size": 500},
    {"name": "Tagliatelle", "default_unit": "g", "category": "Pasta", "pack_size": 500},
    {"name": "Lasagneplatten", "default_unit": "Pck", "category": "Pasta", "pack_size": 1},
    {"name": "Linsen", "default_unit": "g", "category": "Trockenwaren", "pack_size": 500},
    {"name": "Kichererbsen", "default_unit": "Dose", "category": "Trockenwaren", "pack_size": 1},
    {"name": "Bohnen", "default_unit": "Dose", "category": "Trockenwaren", "pack_size": 1},
    {"name": "Mais", "default_unit": "Dose", "category": "Trockenwaren", "pack_size": 1},
    # Brot
    {"name": "Brot", "default_unit": "Stk", "category": "Brot", "pack_size": 1},
    {"name": "Brötchen", "default_unit": "Stk", "category": "Brot", "pack_size": 6},
    {"name": "Toast", "default_unit": "Scheibe", "category": "Brot", "pack_size": 20},
    # Getränke
    {"name": "Wasser", "default_unit": "l", "category": "Getränke", "pack_size": 1.5},
    {"name": "Mineralwasser", "default_unit": "l", "category": "Getränke", "pack_size": 1.5},
    {"name": "Apfelsaft", "default_unit": "l", "category": "Getränke", "pack_size": 1.0},
    {"name": "Bier", "default_unit": "Stk", "category": "Getränke", "pack_size": 6},
    {"name": "Wein rot", "default_unit": "ml", "category": "Getränke", "aliases": ["Rotwein"], "pack_size": 750},
    {"name": "Wein weiß", "default_unit": "ml", "category": "Getränke", "aliases": ["Weißwein"], "pack_size": 750},
    {"name": "Kaffee", "default_unit": "g", "category": "Getränke", "pack_size": 500},
    {"name": "Tee", "default_unit": "Pck", "category": "Getränke", "pack_size": 1},
]


async def seed_products():
    """Idempotently insert seed entries. Also backfill pack_size on existing
    entries that haven't been customised yet (pack_size is missing or 0)."""
    inserted = 0
    updated = 0
    for entry in SEED:
        existing = await products.find_one(
            {"name": {"$regex": f"^{entry['name']}$", "$options": "i"}},
            {"_id": 0, "id": 1, "pack_size": 1},
        )
        if existing:
            seed_pack = entry.get("pack_size", 0) or 0
            current_pack = existing.get("pack_size") or 0
            if seed_pack and not current_pack:
                await products.update_one(
                    {"id": existing["id"]},
                    {"$set": {"pack_size": seed_pack}},
                )
                updated += 1
            continue
        p = Product(**entry)
        await products.insert_one(p.model_dump())
        inserted += 1
    return {"inserted": inserted, "updated": updated}
