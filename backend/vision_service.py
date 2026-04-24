"""Vision helpers: product recognition + receipt parsing via OpenAI Vision."""
import base64
import json
import logging
import re
from pathlib import Path
from typing import List, Optional
from openai import AsyncOpenAI
from db import get_settings

logger = logging.getLogger(__name__)


class VisionNotConfigured(Exception):
    pass


async def _client() -> tuple[AsyncOpenAI, str]:
    settings = await get_settings()
    api_key = settings.get("openai_api_key") or ""
    model = settings.get("vision_model") or "gpt-4o"
    if not api_key:
        raise VisionNotConfigured(
            "OpenAI API-Key ist noch nicht hinterlegt. Bitte im Admin-Bereich unter Einstellungen eintragen."
        )
    return AsyncOpenAI(api_key=api_key), model


def _image_data_url(path: str) -> str:
    p = Path(path)
    data = p.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    ext = p.suffix.lower().lstrip(".") or "jpeg"
    if ext == "jpg":
        ext = "jpeg"
    return f"data:image/{ext};base64,{b64}"


def _extract_json(text: str):
    """Extract first JSON object/array from LLM response (handles code fences)."""
    if not text:
        return None
    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        pass
    # Find first { or [
    match = re.search(r"[\[{].*[\]}]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return None
    return None


PRODUCT_PROMPT = """Du bist ein Vision-Assistent für eine Küchen-App.
Analysiere das Bild und erkenne JEDES sichtbare Lebensmittel- oder Haushaltsprodukt (Verpackung).
Extrahiere für jedes Produkt folgende Felder:
- name: Produktbezeichnung auf Deutsch, so wie man sie auf einer Einkaufsliste schreiben würde (z.B. "Milch 1,5%", "Butter", "Joghurt Natur")
- brand: Marke wenn erkennbar, sonst null
- mhd: Mindesthaltbarkeitsdatum im Format YYYY-MM-DD wenn lesbar, sonst null. Lese alle Datumsangaben im Format DD.MM.YYYY oder DD.MM.YY und wandle in ISO um.
- quantity: Füllmenge als Zahl (z.B. 1, 0.5, 500), sonst null
- unit: Einheit (l, ml, g, kg, Stk), sonst ""
- confidence: 0.0 bis 1.0, wie sicher du bist

Antworte AUSSCHLIESSLICH mit einem JSON-Array von Objekten, ohne weitere Erklärungen.
Beispiel: [{"name":"Milch 1,5%","brand":"Weihenstephan","mhd":"2026-05-10","quantity":1,"unit":"l","confidence":0.92}]

Wenn keine Produkte erkennbar sind, antworte mit []."""


RECEIPT_PROMPT = """Du bist ein Vision-Assistent und analysierst den Foto eines deutschen Kassenzettels.
Extrahiere ALLE Einzelposten (keine Zwischensummen, kein Mehrwertsteuerblock).
Für jeden Posten:
- product_name: Produktbezeichnung wie auf dem Zettel (oft abgekürzt), zusätzlich bitte normalisiert in product_key
- product_key: normalisierter Schlüssel, kleingeschrieben, nur grundlegende Wortstämme (z.B. "milch", "butter", "joghurt natur", "bananen")
- quantity: Zahl, Default 1
- unit: Einheit falls sichtbar (kg, l, Stk), sonst ""
- price_cents: Endpreis in Cent als Integer (z.B. 1,49 EUR -> 149)

Zusätzlich:
- store: Name des Geschäfts (z.B. "REWE", "EDEKA", "Aldi"), null wenn nicht erkennbar
- purchase_date: Datum ISO YYYY-MM-DD wenn erkennbar, sonst null
- total_cents: Gesamtbetrag in Cent

Antworte AUSSCHLIESSLICH mit einem JSON-Objekt:
{"store":"REWE","purchase_date":"2026-04-23","total_cents":1299,"items":[{"product_name":"VOLLMILCH 1,5%","product_key":"milch","quantity":1,"unit":"l","price_cents":119}]}

Wenn kein Kassenzettel erkennbar ist, antworte mit {"items":[]}."""


async def scan_products(image_paths: List[str]) -> List[dict]:
    """Return a flat list of detected products across all images."""
    client, model = await _client()
    content = [{"type": "text", "text": PRODUCT_PROMPT}]
    for p in image_paths:
        content.append({"type": "image_url", "image_url": {"url": _image_data_url(p)}})

    resp = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": content}],
    )
    raw = resp.choices[0].message.content or ""
    parsed = _extract_json(raw)
    if not isinstance(parsed, list):
        logger.warning("Vision product scan returned non-list: %s", raw[:200])
        return []
    # Sanitise
    out = []
    for item in parsed:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        out.append({
            "name": str(item.get("name", "")).strip(),
            "brand": item.get("brand") or None,
            "mhd": item.get("mhd") or None,
            "quantity": item.get("quantity") if isinstance(item.get("quantity"), (int, float)) else None,
            "unit": str(item.get("unit") or ""),
            "confidence": float(item.get("confidence") or 0.5),
        })
    return out


async def parse_receipt(image_path: str) -> dict:
    client, model = await _client()
    content = [
        {"type": "text", "text": RECEIPT_PROMPT},
        {"type": "image_url", "image_url": {"url": _image_data_url(image_path)}},
    ]
    resp = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": content}],
    )
    raw = resp.choices[0].message.content or ""
    parsed = _extract_json(raw)
    if not isinstance(parsed, dict):
        return {"store": None, "purchase_date": None, "total_cents": 0, "items": []}
    items = parsed.get("items") or []
    clean_items = []
    for it in items:
        if not isinstance(it, dict) or not it.get("product_name"):
            continue
        clean_items.append({
            "product_name": str(it.get("product_name", "")).strip(),
            "product_key": str(it.get("product_key") or it.get("product_name", "")).strip().lower(),
            "quantity": float(it.get("quantity") or 1),
            "unit": str(it.get("unit") or ""),
            "price_cents": int(it.get("price_cents") or 0),
        })
    return {
        "store": parsed.get("store") or None,
        "purchase_date": parsed.get("purchase_date") or None,
        "total_cents": int(parsed.get("total_cents") or 0),
        "items": clean_items,
    }


def match_product_to_shopping(product_name: str, shopping_items: List[dict]) -> Optional[str]:
    """Naive but effective fuzzy-ish match: lowercase substring either way."""
    n = (product_name or "").lower().strip()
    if not n:
        return None
    # Try exact-ish first
    for it in shopping_items:
        if it.get("checked"):
            continue
        name = (it.get("name") or "").lower()
        if not name:
            continue
        if n == name or n in name or name in n:
            return it["id"]
    # Token overlap
    n_tokens = set(re.findall(r"\w{3,}", n))
    best_id, best_score = None, 0
    for it in shopping_items:
        if it.get("checked"):
            continue
        tokens = set(re.findall(r"\w{3,}", (it.get("name") or "").lower()))
        score = len(n_tokens & tokens)
        if score > best_score:
            best_id, best_score = it["id"], score
    return best_id if best_score >= 1 else None
