"""Aria integration routes - SSO + data aggregation endpoints.

All routes in this module require a valid shared secret (configured by admin)
since they're meant for machine-to-machine communication between Aria and
CookPilot.
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Header
from db import users, purchases, get_settings
from models import User, AriaSSORequest, AriaAllergyUpdate
from auth import create_token

router = APIRouter(prefix="/api/aria", tags=["aria"])


async def _check_secret(provided: str):
    settings = await get_settings()
    expected = settings.get("aria_shared_secret") or ""
    if not expected:
        raise HTTPException(status_code=503, detail="Aria Shared Secret ist nicht konfiguriert")
    if provided != expected:
        raise HTTPException(status_code=401, detail="Aria Shared Secret ungültig")


@router.post("/sso")
async def aria_sso(body: AriaSSORequest):
    """Return a JWT for the mapped CookPilot user given the Aria user context.

    If no mapping exists yet, automatically create a CookPilot user tied to the
    external_id so future logins resolve automatically.
    """
    await _check_secret(body.shared_secret)

    user = await users.find_one({"external_id": body.external_id}, {"_id": 0})
    if not user:
        # Try email match to merge into existing account
        user = await users.find_one({"email": body.email.lower()}, {"_id": 0})
        if user:
            await users.update_one({"id": user["id"]}, {"$set": {"external_id": body.external_id}})
        else:
            new = User(
                email=body.email.lower(),
                name=body.name,
                role=body.role or "user",
                external_id=body.external_id,
                password_hash=None,
            )
            await users.insert_one(new.model_dump())
            user = new.model_dump()

    if not user.get("active", True):
        raise HTTPException(status_code=403, detail="Benutzer deaktiviert")

    token = create_token(user["id"], user["role"])
    return {"token": token, "user_id": user["id"], "role": user["role"]}


@router.post("/allergies")
async def aria_update_allergies(body: AriaAllergyUpdate):
    """Used by CaseDesk via Aria to push user allergies/diet into CookPilot."""
    await _check_secret(body.shared_secret)
    user = await users.find_one({"external_id": body.external_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    patch = {"allergies": body.allergies}
    if body.diet is not None:
        patch["diet"] = body.diet
    await users.update_one({"id": user["id"]}, {"$set": patch})
    return {"ok": True}


@router.get("/purchases/aggregate")
async def aria_purchases_aggregate(
    product: str,
    start_date: str,
    end_date: str,
    agg: str = "sum_price",  # sum_price | sum_quantity | count
    external_id: Optional[str] = None,
    x_aria_secret: str = Header(..., alias="X-Aria-Secret"),
):
    """Query purchase aggregates.

    Example: GET /api/aria/purchases/aggregate?product=milch&start_date=2026-04-01&end_date=2026-04-30&agg=sum_price
    """
    await _check_secret(x_aria_secret)

    query = {
        "product_key": product.lower(),
        "purchase_date": {"$gte": start_date, "$lte": end_date},
    }
    if external_id:
        user = await users.find_one({"external_id": external_id}, {"_id": 0})
        if user:
            query["user_id"] = user["id"]

    docs = await purchases.find(query, {"_id": 0}).to_list(5000)

    result = {
        "product": product,
        "start_date": start_date,
        "end_date": end_date,
        "count": len(docs),
        "sum_price_cents": sum(d.get("price_cents", 0) for d in docs),
        "sum_price_eur": round(sum(d.get("price_cents", 0) for d in docs) / 100, 2),
        "sum_quantity": sum(float(d.get("quantity", 0) or 0) for d in docs),
        "unit_hint": docs[0].get("unit", "") if docs else "",
    }
    if agg == "count":
        result["value"] = result["count"]
    elif agg == "sum_quantity":
        result["value"] = result["sum_quantity"]
    else:
        result["value"] = result["sum_price_eur"]
    return result


@router.get("/health")
async def health():
    """Public health probe for Aria."""
    return {"ok": True, "service": "CookPilot"}
