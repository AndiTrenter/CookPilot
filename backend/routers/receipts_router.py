"""Receipt + Purchase routes (Phase 3 preparation).

Upload is supported now; OCR parsing is stubbed until Tesseract binary is present.
The purchases collection is already fully queryable.
"""
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from db import receipts, purchases
from auth import get_current_user
from models import Purchase, PurchaseCreate

router = APIRouter(prefix="/api/receipts", tags=["receipts"])

UPLOAD_DIR = Path(os.environ.get("COOKPILOT_UPLOADS", "/app/backend/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _normalise(product: str) -> str:
    return (product or "").strip().lower()


@router.post("/upload")
async def upload_receipt(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    ext = (file.filename or "").split(".")[-1].lower() or "bin"
    if ext not in {"jpg", "jpeg", "png", "pdf", "webp", "heic"}:
        raise HTTPException(status_code=400, detail="Nur JPG/PNG/PDF/WebP/HEIC erlaubt")
    rid = str(uuid.uuid4())
    dest = UPLOAD_DIR / f"{rid}.{ext}"
    with open(dest, "wb") as fh:
        fh.write(await file.read())
    rec = {
        "id": rid,
        "user_id": user["id"],
        "filename": file.filename,
        "path": str(dest),
        "mime": file.content_type,
        "ocr_status": "pending",  # pending | done | failed | disabled
        "ocr_text": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await receipts.insert_one(rec.copy())
    # OCR kept as hook - see /api/receipts/{id}/ocr (stub)
    return {"id": rid, "ocr_status": "pending"}


@router.get("")
async def list_receipts(user: dict = Depends(get_current_user)):
    docs = await receipts.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return docs


@router.post("/{receipt_id}/ocr")
async def run_ocr(receipt_id: str, user: dict = Depends(get_current_user)):
    """OCR hook - runs Tesseract if available, else returns disabled status."""
    rec = await receipts.find_one({"id": receipt_id, "user_id": user["id"]}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="Kassenzettel nicht gefunden")
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(rec["path"])
        text = pytesseract.image_to_string(img, lang="deu")
        await receipts.update_one({"id": receipt_id}, {"$set": {"ocr_status": "done", "ocr_text": text}})
        return {"ocr_status": "done", "text_preview": text[:500]}
    except Exception as exc:
        await receipts.update_one({"id": receipt_id}, {"$set": {"ocr_status": "failed", "ocr_error": str(exc)}})
        return {"ocr_status": "failed", "error": str(exc), "hint": "Tesseract-Binary (deu) muss im Container installiert sein"}


# ---------- Purchases (queryable by Aria) ----------
purchase_router = APIRouter(prefix="/api/purchases", tags=["purchases"])


@purchase_router.get("", response_model=List[Purchase])
async def list_purchases(
    user: dict = Depends(get_current_user),
    product: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    q = {"user_id": user["id"]}
    if product:
        q["product_key"] = _normalise(product)
    if start_date or end_date:
        q["purchase_date"] = {}
        if start_date:
            q["purchase_date"]["$gte"] = start_date
        if end_date:
            q["purchase_date"]["$lte"] = end_date
    docs = await purchases.find(q, {"_id": 0}).sort("purchase_date", -1).to_list(2000)
    return [Purchase(**d) for d in docs]


@purchase_router.post("", response_model=Purchase)
async def add_purchase(body: PurchaseCreate, user: dict = Depends(get_current_user)):
    data = body.model_dump()
    data["product_key"] = _normalise(data.get("product_key") or data.get("product_name", ""))
    p = Purchase(user_id=user["id"], **data)
    await purchases.insert_one(p.model_dump())
    return p


@purchase_router.delete("/{purchase_id}")
async def delete_purchase(purchase_id: str, user: dict = Depends(get_current_user)):
    await purchases.delete_one({"id": purchase_id, "user_id": user["id"]})
    return {"ok": True}
