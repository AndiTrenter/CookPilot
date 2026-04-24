"""Recipe import from external sources (rezepte.lidl.ch focus, extensible).

Parses Next.js React Server Component flight data embedded in the HTML and
returns a CookPilot-shaped recipe dict.
"""
import asyncio
import json
import logging
import re
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; CookPilot/0.2; +https://github.com/cookpilot)"

LIDL_HOST = "rezepte.lidl.ch"
LIDL_DEFAULT_CATEGORY = "monsieur-cuisine-smart"

DIFFICULTY_MAP = {"1": "leicht", "2": "mittel", "3": "schwer"}


class RecipeImportError(Exception):
    pass


async def _fetch(url: str, timeout: float = 15.0) -> str:
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "de-DE,de-CH,de,en;q=0.7"})
        resp.raise_for_status()
        return resp.text


def _parse_flight(html: str) -> dict:
    """Extract RSC rows from Next.js flight data into a rowId -> value dict."""
    payloads = re.findall(r'self\.__next_f\.push\(\[1,"(.+?)"\]\)', html, re.DOTALL)
    if not payloads:
        return {}
    full = "".join(json.loads('"' + p + '"') for p in payloads)

    rows: dict = {}
    i = 0
    dec = json.JSONDecoder()
    while i < len(full):
        m = re.match(r"([0-9a-f]+):", full[i:])
        if not m:
            nl = full.find("\n", i)
            if nl == -1:
                break
            i = nl + 1
            continue
        rid = m.group(1)
        i += m.end()
        try:
            val, end = dec.raw_decode(full, i)
            rows[rid] = val
            i = end
            if i < len(full) and full[i] == "\n":
                i += 1
        except Exception:
            nl = full.find("\n", i)
            if nl == -1:
                break
            i = nl + 1
    return rows


def _resolve(value, rows: dict, depth: int = 0, seen: Optional[set] = None):
    if depth > 20:
        return value
    if seen is None:
        seen = set()
    if isinstance(value, str) and re.fullmatch(r"\$[0-9a-f]+", value):
        rid = value[1:]
        if rid in seen:
            return None
        seen = seen | {rid}
        return _resolve(rows.get(rid), rows, depth + 1, seen)
    if isinstance(value, list):
        return [_resolve(v, rows, depth + 1, seen) for v in value]
    if isinstance(value, dict):
        return {k: _resolve(v, rows, depth + 1, seen) for k, v in value.items()}
    return value


def _lidl_image_url(recipe_id: str, slug: str, aspect: str = "16x9") -> str:
    """Fallback only - prefer using imageInfo.prefix + imageInfo.name directly."""
    if not recipe_id or not slug:
        return ""
    return (
        f"https://cdn.recipes.lidl/images-v2/recipes/de-CH/{recipe_id}/"
        f"{aspect}_fallback_{slug}.jpeg"
    )


def _lidl_image_from_info(image_info: Optional[dict], aspect: str = "16x9") -> str:
    """Compose the full CDN URL from the recipe's imageInfo structure."""
    if not isinstance(image_info, dict):
        return ""
    name = image_info.get("name") or ""
    prefix = image_info.get("prefix") or ""
    if not name or not prefix:
        return ""
    # Strip extension from `name`
    stem = name.rsplit(".", 1)[0]
    return f"https://cdn.recipes.lidl/images-v2{prefix}/{aspect}_fallback_{stem}.jpeg"


def _build_ingredient_line(ing: dict) -> dict:
    unit_obj = ing.get("unit") or {}
    unit = ""
    if isinstance(unit_obj, dict):
        unit = unit_obj.get("singular") or unit_obj.get("plural") or ""
    qty = ing.get("quantityFrom") or 0
    to = ing.get("quantityTo") or 0
    amount = qty if (not to or to == qty) else (qty + to) / 2
    name = ing.get("singular") or ing.get("plural") or ""
    if ing.get("additionalText"):
        name = f"{name} ({ing['additionalText']})".strip()
    return {
        "name": name.strip(),
        "amount": float(amount or 0),
        "unit": unit or "",
    }


def _find_recipe_row(rows: dict) -> Optional[dict]:
    for rid, v in rows.items():
        if (
            isinstance(v, dict)
            and v.get("ingredientGroups") is not None
            and v.get("recipePreparations") is not None
            and v.get("name")
        ):
            return v
    return None


async def import_from_lidl(url: str) -> dict:
    html = await _fetch(url)
    rows = _parse_flight(html)
    raw = _find_recipe_row(rows)
    if not raw:
        raise RecipeImportError("Kein Rezept auf dieser Seite gefunden. URL prüfen?")

    recipe = _resolve(raw, rows)

    slug = recipe.get("slug") or url.rstrip("/").rsplit("/", 1)[-1]
    recipe_id = recipe.get("id")

    ingredients: list = []
    for grp in recipe.get("ingredientGroups") or []:
        grp = grp or {}
        for ing in grp.get("ingredients") or []:
            if not isinstance(ing, dict):
                continue
            ingredients.append(_build_ingredient_line(ing))

    steps = [
        (s.get("content") or "").strip()
        for s in (recipe.get("recipePreparations") or [])
        if isinstance(s, dict)
        and s.get("preparationType") == "COOKING_STEP"
        and (s.get("content") or "").strip()
    ]

    prep_min = int(recipe.get("preparationTime") or 0)
    cook_min = int(recipe.get("cookingTime") or 0)
    total_min = (prep_min + cook_min) or None

    difficulty = DIFFICULTY_MAP.get(str(recipe.get("difficulty") or ""))

    # Category: first course name or "Lidl Cuisine"
    category = ""
    courses = recipe.get("courses") or []
    for c in courses:
        if isinstance(c, dict) and c.get("name"):
            category = c["name"]
            break
    if not category:
        category = "Lidl"

    tags = []
    for key in ("diets", "foodTypes", "collections", "regions", "seasons", "tools"):
        for entry in recipe.get(key) or []:
            if isinstance(entry, dict) and entry.get("name"):
                tags.append(entry["name"])

    image_url = _lidl_image_from_info(recipe.get("imageInfo")) or _lidl_image_url(recipe_id, slug)

    return {
        "title": recipe.get("name") or slug.replace("-", " ").title(),
        "description": (recipe.get("meta") or {}).get("description") or "",
        "category": category,
        "tags": tags,
        "servings": int(recipe.get("servingType") or 4) if str(recipe.get("servingType") or "").isdigit() else 4,
        "cook_time_min": total_min,
        "difficulty": difficulty,
        "ingredients": ingredients,
        "steps": steps,
        "image_url": image_url,
        "source": f"lidl:{slug}",
        "source_url": url,
    }


async def import_from_url(url: str) -> dict:
    """Dispatch to the appropriate importer based on host."""
    if not url or not url.startswith(("http://", "https://")):
        raise RecipeImportError("Bitte eine gültige HTTPS-URL angeben.")
    if LIDL_HOST in url:
        return await import_from_lidl(url)
    raise RecipeImportError(
        "Diese Quelle wird noch nicht unterstützt. Aktuell: rezepte.lidl.ch."
    )


# ---------------------------------------------------------------------------
# External catalog (search index cache)
# ---------------------------------------------------------------------------
CATEGORY_URL = f"https://{LIDL_HOST}/{LIDL_DEFAULT_CATEGORY}"


async def fetch_lidl_category_index() -> list[dict]:
    """Scrape the Monsieur Cuisine Smart category page and return list of
    {slug, title, image_url, source_url, cook_time_min, difficulty}.
    """
    html = await _fetch(CATEGORY_URL)
    items: dict[str, dict] = {}

    # Each card is an <article data-name="Title" data-testid="/rezepte/slug">...</article>
    article_pattern = re.compile(
        r'<article[^>]*\bdata-name="(?P<title>[^"]+)"[^>]*\bdata-testid="/rezepte/(?P<slug>[a-z0-9-]+)"'
        r'(?P<body>[\s\S]*?)</article>',
        re.IGNORECASE,
    )
    # Pick the fallback jpeg URL (stable format, works everywhere).
    image_pattern = re.compile(
        r'(https://cdn\.recipes\.lidl/images-v2/recipes/de-CH/[a-f0-9-]{36}/16x9_fallback_[^" \s]+\.jpe?g)',
        re.IGNORECASE,
    )
    time_pattern = re.compile(
        r'>\s*(?:(?P<h>\d+)\s*h)?\s*(?P<m>\d+)?\s*min\s*<', re.IGNORECASE,
    )
    diff_pattern = re.compile(r'>(?P<diff>Leicht|Mittel|Schwer)<', re.IGNORECASE)

    for m in article_pattern.finditer(html):
        slug = m.group("slug")
        if slug in items:
            continue
        body = m.group("body")
        img_m = image_pattern.search(body)
        image = img_m.group(1) if img_m else ""

        mins = None
        t = time_pattern.search(body)
        if t:
            total = 0
            if t.group("h"):
                total += int(t.group("h")) * 60
            if t.group("m"):
                total += int(t.group("m"))
            mins = total or None

        diff_m = diff_pattern.search(body)
        difficulty = diff_m.group("diff").lower() if diff_m else None

        items[slug] = {
            "slug": slug,
            "title": m.group("title"),
            "image_url": image,
            "source_url": f"https://{LIDL_HOST}/rezepte/{slug}",
            "cook_time_min": mins,
            "difficulty": difficulty,
        }

    # Fallback: link-only scan
    if not items:
        for slug in dict.fromkeys(re.findall(r'href="/rezepte/([a-z0-9-]+)"', html)):
            items[slug] = {
                "slug": slug,
                "title": slug.replace("-", " ").title(),
                "image_url": "",
                "source_url": f"https://{LIDL_HOST}/rezepte/{slug}",
                "cook_time_min": None,
                "difficulty": None,
            }

    return list(items.values())
