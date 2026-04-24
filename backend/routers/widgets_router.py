"""Widget configuration routes (dashboard + tablet)."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from db import widget_configs
from auth import get_current_user, require_admin
from models import WidgetConfig, WidgetConfigUpdate

router = APIRouter(prefix="/api/widgets", tags=["widgets"])

# Catalog of available widgets. Keys used on frontend as well.
WIDGET_CATALOG = [
    {"key": "quick_actions", "label": "Schnellaktionen", "views": ["dashboard", "tablet"]},
    {"key": "shopping_list", "label": "Einkaufsliste", "views": ["dashboard", "tablet"]},
    {"key": "low_stock", "label": "Bestandswarnungen", "views": ["dashboard", "tablet"]},
    {"key": "mhd_soon", "label": "MHD-Warnungen", "views": ["dashboard", "tablet"]},
    {"key": "favorites", "label": "Favoriten-Rezepte", "views": ["dashboard", "tablet"]},
    {"key": "recipe_of_day", "label": "Rezept des Tages", "views": ["dashboard", "tablet"]},
    {"key": "chat_quick", "label": "Koch-Chat", "views": ["dashboard", "tablet"]},
    {"key": "pantry_summary", "label": "Vorrats-Übersicht", "views": ["dashboard", "tablet"]},
]


@router.get("/catalog")
async def catalog(_: dict = Depends(get_current_user)):
    return WIDGET_CATALOG


@router.get("/{view}")
async def list_for_view(view: str, user: dict = Depends(get_current_user)):
    if view not in {"dashboard", "tablet"}:
        raise HTTPException(status_code=400, detail="Ungültige Ansicht")
    docs = await widget_configs.find({"view": view}, {"_id": 0}).sort("order", 1).to_list(100)
    if not docs:
        # Defaults
        defaults = [w for w in WIDGET_CATALOG if view in w["views"]]
        docs = [
            {"id": f"default-{view}-{i}", "view": view, "widget": w["key"], "order": i, "visible": True, "config": {}}
            for i, w in enumerate(defaults)
        ]
    return docs


@router.put("/{view}")
async def save_for_view(view: str, body: WidgetConfigUpdate, admin: dict = Depends(require_admin)):
    if view not in {"dashboard", "tablet"}:
        raise HTTPException(status_code=400, detail="Ungültige Ansicht")
    await widget_configs.delete_many({"view": view})
    for i, w in enumerate(body.widgets):
        w = dict(w)
        w["view"] = view
        w["order"] = i
        w.setdefault("visible", True)
        w.setdefault("config", {})
        w.setdefault("id", f"{view}-{w.get('widget','x')}-{i}")
        await widget_configs.insert_one(w.copy())
    return {"ok": True}
