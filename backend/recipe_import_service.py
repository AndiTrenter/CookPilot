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

USER_AGENT = "Mozilla/5.0 (compatible; CookPilot/0.3; +https://github.com/cookpilot)"

LIDL_HOST = "rezepte.lidl.ch"
LIDL_KOCHEN_HOST = "www.lidl-kochen.de"
LIDL_DEFAULT_CATEGORY = "monsieur-cuisine-smart"

LIDL_KOCHEN_SEARCH_URL = "https://www.lidl-kochen.de/search_v2/api/search/recipes"

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


def _lidl_image_from_info(image_info: Optional[dict], aspect: str = "16x9") -> str:
    """Compose the full CDN URL from the recipe's imageInfo structure."""
    if not isinstance(image_info, dict):
        return ""
    name = image_info.get("name") or ""
    prefix = image_info.get("prefix") or ""
    if not name or not prefix:
        return ""
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

    image_url = _lidl_image_from_info(recipe.get("imageInfo"))

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
    if LIDL_KOCHEN_HOST in url:
        return await import_from_jsonld(url, source_prefix="lidl_kochen")
    # Generic JSON-LD fallback - works for many recipe sites (chefkoch, lecker, …)
    try:
        return await import_from_jsonld(url, source_prefix="url")
    except RecipeImportError:
        raise
    except Exception:
        raise RecipeImportError(
            "Diese Quelle wird noch nicht unterstützt. Aktuell funktionieren rezepte.lidl.ch, "
            "lidl-kochen.de und generische JSON-LD Rezepte (schema.org/Recipe)."
        )


# ---------------------------------------------------------------------------
# Generic JSON-LD (schema.org/Recipe) importer
# ---------------------------------------------------------------------------
_JSONLD_PATTERN = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)
_ISO_DURATION = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?")
# Splits "Langkornreis 300 g" or "200 g Mehl" into (amount, unit, name).
_ING_RE = re.compile(
    r"""^\s*
        (?:(?P<amount1>[\d.,½¼¾⅓⅔]+)\s*(?P<unit1>[a-zA-Zäöü.]*)\s+(?P<name1>.+?)
         |(?P<name2>.+?)\s+(?P<amount2>[\d.,½¼¾⅓⅔]+)\s*(?P<unit2>[a-zA-Zäöü.]*)
         |(?P<name3>.+))
        \s*$""",
    re.VERBOSE,
)
_FRAC = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3}


def _iso_to_min(val) -> Optional[int]:
    if not val or not isinstance(val, str):
        return None
    m = _ISO_DURATION.match(val)
    if not m:
        return None
    h = int(m.group(1) or 0)
    mn = int(m.group(2) or 0)
    total = h * 60 + mn
    return total or None


def _to_float(raw: str) -> float:
    raw = raw.strip().replace(",", ".")
    frac = sum(_FRAC.get(ch, 0) for ch in raw if ch in _FRAC)
    digit = re.sub(r"[½¼¾⅓⅔]", "", raw).strip()
    try:
        return float(digit) + frac if digit else float(frac)
    except ValueError:
        return 0.0


def _parse_ingredient(s: str) -> dict:
    """Best-effort split of a free-form ingredient line."""
    raw = (s or "").strip()
    if not raw:
        return {"name": "", "amount": 0, "unit": ""}
    m = _ING_RE.match(raw)
    if not m:
        return {"name": raw, "amount": 0, "unit": ""}
    if m.group("amount1") is not None:
        return {
            "name": m.group("name1").strip(" ,"),
            "amount": _to_float(m.group("amount1")),
            "unit": (m.group("unit1") or "").strip(),
        }
    if m.group("amount2") is not None:
        return {
            "name": m.group("name2").strip(" ,"),
            "amount": _to_float(m.group("amount2")),
            "unit": (m.group("unit2") or "").strip(),
        }
    return {"name": m.group("name3").strip(), "amount": 0, "unit": ""}


def _find_jsonld_recipe(html: str) -> Optional[dict]:
    for m in _JSONLD_PATTERN.finditer(html):
        raw = m.group(1).strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue

        candidates = data if isinstance(data, list) else [data]
        # Handle @graph structure
        extra = []
        for c in candidates:
            if isinstance(c, dict) and isinstance(c.get("@graph"), list):
                extra.extend(c["@graph"])
        candidates = candidates + extra

        for c in candidates:
            if not isinstance(c, dict):
                continue
            t = c.get("@type")
            types = t if isinstance(t, list) else [t]
            if "Recipe" in types:
                return c
    return None


async def import_from_jsonld(url: str, source_prefix: str = "url") -> dict:
    html = await _fetch(url)
    recipe = _find_jsonld_recipe(html)
    if not recipe:
        raise RecipeImportError(
            "Auf dieser Seite wurde kein strukturiertes Rezept gefunden (kein schema.org/Recipe JSON-LD)."
        )

    title = recipe.get("name") or ""
    if isinstance(title, list):
        title = title[0] if title else ""

    # image can be string, list of strings, or list/dict with @type ImageObject
    image_url = ""
    image = recipe.get("image")
    if isinstance(image, str):
        image_url = image
    elif isinstance(image, list) and image:
        first = image[0]
        image_url = first if isinstance(first, str) else (first.get("url") if isinstance(first, dict) else "")
    elif isinstance(image, dict):
        image_url = image.get("url") or ""

    description = recipe.get("description") or ""
    if isinstance(description, list):
        description = " ".join(str(x) for x in description)

    # servings
    yield_raw = recipe.get("recipeYield")
    servings = 4
    if isinstance(yield_raw, (int, float)):
        servings = int(yield_raw) or 4
    elif isinstance(yield_raw, str):
        m = re.search(r"\d+", yield_raw)
        if m:
            servings = int(m.group(0))
    elif isinstance(yield_raw, list) and yield_raw:
        m = re.search(r"\d+", str(yield_raw[0]))
        if m:
            servings = int(m.group(0))

    prep = _iso_to_min(recipe.get("prepTime")) or 0
    cook = _iso_to_min(recipe.get("cookTime")) or 0
    total = _iso_to_min(recipe.get("totalTime")) or (prep + cook) or None

    # ingredients
    ingredients = [_parse_ingredient(x) for x in (recipe.get("recipeIngredient") or []) if x]

    # instructions - may be list of HowToStep or HowToSection, or single string
    def _flatten_steps(node) -> list[str]:
        if node is None:
            return []
        if isinstance(node, str):
            return [node.strip()] if node.strip() else []
        if isinstance(node, dict):
            t = node.get("@type")
            if t == "HowToStep":
                txt = (node.get("text") or node.get("name") or "").strip()
                return [txt] if txt else []
            if t == "HowToSection":
                out = []
                for item in node.get("itemListElement") or []:
                    out.extend(_flatten_steps(item))
                return out
            txt = (node.get("text") or "").strip()
            return [txt] if txt else []
        if isinstance(node, list):
            out = []
            for item in node:
                out.extend(_flatten_steps(item))
            return out
        return []

    steps = _flatten_steps(recipe.get("recipeInstructions"))

    # category / tags
    category = ""
    cat_raw = recipe.get("recipeCategory")
    if isinstance(cat_raw, str):
        category = cat_raw.split(",")[0].strip()
    elif isinstance(cat_raw, list) and cat_raw:
        category = str(cat_raw[0])

    tags = []
    keywords = recipe.get("keywords")
    if isinstance(keywords, str):
        tags = [k.strip() for k in keywords.split(",") if k.strip()]
    elif isinstance(keywords, list):
        tags = [str(k) for k in keywords]

    # slug for source tag
    slug = url.rstrip("/").rsplit("/", 1)[-1]

    return {
        "title": title or slug.replace("-", " ").title(),
        "description": description.strip(),
        "category": category,
        "tags": tags[:15],
        "servings": servings,
        "cook_time_min": total,
        "difficulty": None,
        "ingredients": ingredients,
        "steps": steps,
        "image_url": image_url,
        "source": f"{source_prefix}:{slug}",
        "source_url": url,
    }


# ---------------------------------------------------------------------------
# Live-Suche Lidl-Kochen (lidl-kochen.de)
# ---------------------------------------------------------------------------
LIDL_KOCHEN_DIFFICULTY = {0: None, 1: "leicht", 2: "mittel", 3: "schwer"}


async def search_lidl_kochen(text: str, per_page: int = 20) -> list[dict]:
    """Query the live recipe search API and normalise results."""
    if not text.strip():
        return []
    params = {
        "perPage": max(1, min(per_page, 100)),
        "sort": "-relevant",
        "s": text.strip(),
    }
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(
            LIDL_KOCHEN_SEARCH_URL,
            params=params,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
    out: list[dict] = []
    for r in data.get("list", []) or []:
        if not isinstance(r, dict):
            continue
        out.append({
            "slug": str(r.get("recipeId") or r.get("url", "").rsplit("/", 1)[-1]),
            "title": r.get("name") or "",
            "image_url": r.get("photo") or "",
            "source_url": r.get("url") or "",
            "cook_time_min": r.get("preparationTotalTime") or r.get("preparationTime") or None,
            "difficulty": LIDL_KOCHEN_DIFFICULTY.get(r.get("difficulty") or 0),
            "likes": r.get("likeCount") or 0,
            "source_name": "lidl_kochen",
        })
    return out


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
