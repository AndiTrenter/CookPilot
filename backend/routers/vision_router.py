"""Vision routes: product photo scan + receipt parse (Phase 3)."""
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from db import shopping_items, pantry_items, receipts, purchases
from auth import get_current_user
from vision_service import scan_products, parse_receipt, match_product_to_shopping, VisionNotConfigured

router = APIRouter(prefix="/api/vision", tags=["vision"])

UPLOAD_DIR = Path(os.environ.get("COOKPILOT_UPLOADS", "/app/backend/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXT = {"jpg", "jpeg", "png", "webp", "heic"}


async def _save_upload(file: UploadFile) -> str:
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() or "jpg"
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"Nur {', '.join(sorted(ALLOWED_EXT))} erlaubt")
    dest = UPLOAD_DIR / f"{uuid.uuid4()}.{ext}"
    data = await file.read()
    with open(dest, "wb") as fh:
        fh.write(data)
    return str(dest)


# -----------------------------------------------------------------------------
# Product scan
# -----------------------------------------------------------------------------
class ScanApplyItem(BaseModel):
    name: str
    brand: Optional[str] = None
    mhd: Optional[str] = None
    quantity: Optional[float] = None
    unit: str = ""
    matched_shopping_id: Optional[str] = None  # if user wants to tick off
    add_to_pantry: bool = True
    pantry_category: str = ""
    pantry_location: str = ""


class ScanApplyRequest(BaseModel):
    items: List[ScanApplyItem] = Field(default_factory=list)


@router.post("/scan-products")
async def scan_product_photos(
    files: List[UploadFile] = File(...),
    user: dict = Depends(get_current_user),
):
    if not files:
        raise HTTPException(status_code=400, detail="Keine Bilder übergeben")
    if len(files) > 6:
        raise HTTPException(status_code=400, detail="Maximal 6 Bilder auf einmal")
    paths = [await _save_upload(f) for f in files]

    try:
        detected = await scan_products(paths)
    except VisionNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Vision-Fehler: {exc}")

    # Suggest matches against open shopping items
    shop = await shopping_items.find({"checked": False}, {"_id": 0}).to_list(1000)
    for d in detected:
        d["suggested_shopping_id"] = match_product_to_shopping(d["name"], shop)

    return {"products": detected, "image_count": len(paths)}


@router.post("/apply-scan")
async def apply_scan(body: ScanApplyRequest, user: dict = Depends(get_current_user)):
    """Tick off matched shopping items and add detected products to pantry."""
    shopping_ticked = 0
    pantry_added = 0
    for item in body.items:
        if item.matched_shopping_id:
            res = await shopping_items.update_one(
                {"id": item.matched_shopping_id},
                {"$set": {"checked": True, "checked_at": datetime.now(timezone.utc).isoformat()}},
            )
            if res.modified_count:
                shopping_ticked += 1
        if item.add_to_pantry:
            now = datetime.now(timezone.utc).isoformat()
            doc = {
                "id": str(uuid.uuid4()),
                "name": item.name,
                "amount": item.quantity or 1,
                "unit": item.unit or "",
                "min_amount": 0,
                "category": item.pantry_category or "",
                "location": item.pantry_location or "",
                "mhd": item.mhd or None,
                "created_at": now,
                "updated_at": now,
            }
            await pantry_items.insert_one(doc.copy())
            pantry_added += 1
    return {"shopping_ticked": shopping_ticked, "pantry_added": pantry_added}


# -----------------------------------------------------------------------------
# Receipt parse
# -----------------------------------------------------------------------------
class ReceiptApplyItem(BaseModel):
    product_name: str
    product_key: str
    quantity: float = 1
    unit: str = ""
    price_cents: int = 0
    matched_shopping_id: Optional[str] = None


class ReceiptApplyRequest(BaseModel):
    receipt_id: str
    store: Optional[str] = None
    purchase_date: str  # ISO YYYY-MM-DD
    items: List[ReceiptApplyItem] = Field(default_factory=list)


@router.post("/parse-receipt")
async def parse_receipt_endpoint(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    path = await _save_upload(file)
    rid = Path(path).stem
    # persist receipt metadata
    rec = {
        "id": rid,
        "user_id": user["id"],
        "filename": file.filename,
        "path": path,
        "mime": file.content_type,
        "ocr_status": "pending",
        "ocr_text": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await receipts.insert_one(rec.copy())

    try:
        parsed = await parse_receipt(path)
    except VisionNotConfigured as exc:
        await receipts.update_one({"id": rid}, {"$set": {"ocr_status": "disabled"}})
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        await receipts.update_one({"id": rid}, {"$set": {"ocr_status": "failed", "ocr_error": str(exc)}})
        raise HTTPException(status_code=502, detail=f"Vision-Fehler: {exc}")

    await receipts.update_one({"id": rid}, {"$set": {"ocr_status": "done", "parsed": parsed}})

    # Suggest shopping matches
    shop = await shopping_items.find({"checked": False}, {"_id": 0}).to_list(1000)
    for it in parsed.get("items", []):
        it["suggested_shopping_id"] = match_product_to_shopping(it["product_name"], shop)

    return {
        "receipt_id": rid,
        "store": parsed.get("store"),
        "purchase_date": parsed.get("purchase_date"),
        "total_cents": parsed.get("total_cents", 0),
        "items": parsed.get("items", []),
    }


@router.post("/apply-receipt")
async def apply_receipt(body: ReceiptApplyRequest, user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    shopping_ticked = 0
    purchases_added = 0
    for it in body.items:
        # Persist purchase
        purchase_doc = {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "product_name": it.product_name,
            "product_key": (it.product_key or it.product_name).strip().lower(),
            "quantity": it.quantity,
            "unit": it.unit or "",
            "price_cents": it.price_cents or 0,
            "purchase_date": body.purchase_date,
            "receipt_id": body.receipt_id,
            "mhd": None,
            "store": body.store or None,
            "created_at": now,
        }
        await purchases.insert_one(purchase_doc.copy())
        purchases_added += 1

        if it.matched_shopping_id:
            res = await shopping_items.update_one(
                {"id": it.matched_shopping_id},
                {"$set": {"checked": True, "checked_at": now}},
            )
            if res.modified_count:
                shopping_ticked += 1

    await receipts.update_one(
        {"id": body.receipt_id},
        {"$set": {"applied": True, "applied_at": now, "applied_count": purchases_added}},
    )
    return {"shopping_ticked": shopping_ticked, "purchases_added": purchases_added}
