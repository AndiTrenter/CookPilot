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
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProductCreate(BaseModel):
    name: str
    default_unit: str = ""
    category: str = ""
    aliases: List[str] = []


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
    {"name": "Milch", "default_unit": "l", "category": "Milchprodukte"},
    {"name": "Butter", "default_unit": "g", "category": "Milchprodukte"},
    {"name": "Sahne", "default_unit": "ml", "category": "Milchprodukte", "aliases": ["Schlagsahne", "Rahm"]},
    {"name": "Quark", "default_unit": "g", "category": "Milchprodukte"},
    {"name": "Joghurt", "default_unit": "g", "category": "Milchprodukte"},
    {"name": "Frischkäse", "default_unit": "g", "category": "Milchprodukte"},
    {"name": "Mozzarella", "default_unit": "g", "category": "Milchprodukte"},
    {"name": "Parmesan", "default_unit": "g", "category": "Milchprodukte"},
    {"name": "Gouda", "default_unit": "g", "category": "Milchprodukte"},
    {"name": "Feta", "default_unit": "g", "category": "Milchprodukte"},
    {"name": "Schmand", "default_unit": "g", "category": "Milchprodukte"},
    {"name": "Crème fraîche", "default_unit": "g", "category": "Milchprodukte"},
    # Eier
    {"name": "Ei", "default_unit": "Stk", "category": "Milchprodukte", "aliases": ["Eier", "Hühnerei"]},
    # Backwaren / Mehl & Co.
    {"name": "Mehl", "default_unit": "g", "category": "Backen", "aliases": ["Weizenmehl"]},
    {"name": "Zucker", "default_unit": "g", "category": "Backen"},
    {"name": "Brauner Zucker", "default_unit": "g", "category": "Backen"},
    {"name": "Puderzucker", "default_unit": "g", "category": "Backen"},
    {"name": "Vanillezucker", "default_unit": "Pck", "category": "Backen"},
    {"name": "Backpulver", "default_unit": "Pck", "category": "Backen"},
    {"name": "Hefe", "default_unit": "Pck", "category": "Backen", "aliases": ["Trockenhefe"]},
    {"name": "Speisestärke", "default_unit": "g", "category": "Backen"},
    {"name": "Salz", "default_unit": "Prise", "category": "Gewürze"},
    {"name": "Pfeffer", "default_unit": "Prise", "category": "Gewürze"},
    {"name": "Paprikapulver", "default_unit": "TL", "category": "Gewürze"},
    {"name": "Curry", "default_unit": "TL", "category": "Gewürze"},
    {"name": "Kreuzkümmel", "default_unit": "TL", "category": "Gewürze"},
    {"name": "Oregano", "default_unit": "TL", "category": "Gewürze"},
    {"name": "Basilikum", "default_unit": "Bund", "category": "Gewürze"},
    {"name": "Petersilie", "default_unit": "Bund", "category": "Gewürze"},
    {"name": "Schnittlauch", "default_unit": "Bund", "category": "Gewürze"},
    {"name": "Thymian", "default_unit": "Bund", "category": "Gewürze"},
    {"name": "Rosmarin", "default_unit": "Bund", "category": "Gewürze"},
    # Öle / Saucen
    {"name": "Olivenöl", "default_unit": "ml", "category": "Öl & Essig"},
    {"name": "Sonnenblumenöl", "default_unit": "ml", "category": "Öl & Essig"},
    {"name": "Rapsöl", "default_unit": "ml", "category": "Öl & Essig"},
    {"name": "Essig", "default_unit": "ml", "category": "Öl & Essig", "aliases": ["Weißweinessig"]},
    {"name": "Balsamico", "default_unit": "ml", "category": "Öl & Essig"},
    {"name": "Sojasauce", "default_unit": "ml", "category": "Öl & Essig"},
    {"name": "Senf", "default_unit": "g", "category": "Öl & Essig"},
    {"name": "Ketchup", "default_unit": "ml", "category": "Öl & Essig"},
    # Fleisch / Fisch
    {"name": "Hackfleisch", "default_unit": "g", "category": "Fleisch", "aliases": ["Rinderhack", "Hack"]},
    {"name": "Hähnchenbrust", "default_unit": "g", "category": "Fleisch"},
    {"name": "Putenbrust", "default_unit": "g", "category": "Fleisch"},
    {"name": "Schweineschnitzel", "default_unit": "Stk", "category": "Fleisch"},
    {"name": "Speck", "default_unit": "g", "category": "Fleisch"},
    {"name": "Schinken", "default_unit": "Scheibe", "category": "Fleisch"},
    {"name": "Lachs", "default_unit": "g", "category": "Fisch"},
    {"name": "Thunfisch", "default_unit": "Dose", "category": "Fisch"},
    # Gemüse
    {"name": "Zwiebel", "default_unit": "Stk", "category": "Gemüse", "aliases": ["Zwiebeln"]},
    {"name": "Knoblauch", "default_unit": "Zehe", "category": "Gemüse"},
    {"name": "Tomate", "default_unit": "Stk", "category": "Gemüse", "aliases": ["Tomaten"]},
    {"name": "Tomaten passiert", "default_unit": "g", "category": "Gemüse", "aliases": ["passierte Tomaten"]},
    {"name": "Tomaten gehackt", "default_unit": "g", "category": "Gemüse", "aliases": ["gehackte Tomaten"]},
    {"name": "Paprika", "default_unit": "Stk", "category": "Gemüse"},
    {"name": "Karotte", "default_unit": "Stk", "category": "Gemüse", "aliases": ["Möhre", "Karotten", "Möhren"]},
    {"name": "Kartoffel", "default_unit": "kg", "category": "Gemüse", "aliases": ["Kartoffeln"]},
    {"name": "Süßkartoffel", "default_unit": "Stk", "category": "Gemüse"},
    {"name": "Zucchini", "default_unit": "Stk", "category": "Gemüse"},
    {"name": "Aubergine", "default_unit": "Stk", "category": "Gemüse"},
    {"name": "Champignons", "default_unit": "g", "category": "Gemüse", "aliases": ["Pilze"]},
    {"name": "Brokkoli", "default_unit": "Stk", "category": "Gemüse"},
    {"name": "Blumenkohl", "default_unit": "Stk", "category": "Gemüse"},
    {"name": "Spinat", "default_unit": "g", "category": "Gemüse"},
    {"name": "Salat", "default_unit": "Stk", "category": "Gemüse"},
    {"name": "Gurke", "default_unit": "Stk", "category": "Gemüse"},
    {"name": "Lauch", "default_unit": "Stk", "category": "Gemüse"},
    {"name": "Sellerie", "default_unit": "Stk", "category": "Gemüse"},
    {"name": "Ingwer", "default_unit": "g", "category": "Gemüse"},
    {"name": "Chili", "default_unit": "Stk", "category": "Gemüse"},
    # Obst
    {"name": "Apfel", "default_unit": "Stk", "category": "Obst", "aliases": ["Äpfel"]},
    {"name": "Banane", "default_unit": "Stk", "category": "Obst", "aliases": ["Bananen"]},
    {"name": "Zitrone", "default_unit": "Stk", "category": "Obst"},
    {"name": "Limette", "default_unit": "Stk", "category": "Obst"},
    {"name": "Orange", "default_unit": "Stk", "category": "Obst"},
    {"name": "Beeren", "default_unit": "g", "category": "Obst"},
    {"name": "Erdbeeren", "default_unit": "g", "category": "Obst"},
    # Trockenwaren / Pasta / Reis
    {"name": "Reis", "default_unit": "g", "category": "Trockenwaren"},
    {"name": "Basmatireis", "default_unit": "g", "category": "Trockenwaren"},
    {"name": "Risottoreis", "default_unit": "g", "category": "Trockenwaren"},
    {"name": "Spaghetti", "default_unit": "g", "category": "Pasta"},
    {"name": "Penne", "default_unit": "g", "category": "Pasta"},
    {"name": "Tagliatelle", "default_unit": "g", "category": "Pasta"},
    {"name": "Lasagneplatten", "default_unit": "Pck", "category": "Pasta"},
    {"name": "Linsen", "default_unit": "g", "category": "Trockenwaren"},
    {"name": "Kichererbsen", "default_unit": "Dose", "category": "Trockenwaren"},
    {"name": "Bohnen", "default_unit": "Dose", "category": "Trockenwaren"},
    {"name": "Mais", "default_unit": "Dose", "category": "Trockenwaren"},
    # Brot
    {"name": "Brot", "default_unit": "Stk", "category": "Brot"},
    {"name": "Brötchen", "default_unit": "Stk", "category": "Brot"},
    {"name": "Toast", "default_unit": "Scheibe", "category": "Brot"},
    # Getränke
    {"name": "Wasser", "default_unit": "l", "category": "Getränke"},
    {"name": "Mineralwasser", "default_unit": "l", "category": "Getränke"},
    {"name": "Apfelsaft", "default_unit": "l", "category": "Getränke"},
    {"name": "Bier", "default_unit": "Stk", "category": "Getränke"},
    {"name": "Wein rot", "default_unit": "ml", "category": "Getränke", "aliases": ["Rotwein"]},
    {"name": "Wein weiß", "default_unit": "ml", "category": "Getränke", "aliases": ["Weißwein"]},
    {"name": "Kaffee", "default_unit": "g", "category": "Getränke"},
    {"name": "Tee", "default_unit": "Pck", "category": "Getränke"},
]


async def seed_products():
    """Idempotently insert seed entries that don't already exist by name."""
    inserted = 0
    for entry in SEED:
        existing = await products.find_one(
            {"name": {"$regex": f"^{entry['name']}$", "$options": "i"}},
            {"_id": 0, "id": 1},
        )
        if existing:
            continue
        p = Product(**entry)
        await products.insert_one(p.model_dump())
        inserted += 1
    return inserted
