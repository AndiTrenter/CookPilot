"""LLM-powered recipe suggestions based on pantry, allergies, and user's recipe library."""
import json
import logging
import re
from typing import List, Optional
from openai import AsyncOpenAI
from db import get_settings, recipes, pantry_items

logger = logging.getLogger(__name__)


class SuggestionsNotConfigured(Exception):
    pass


async def _client() -> tuple[AsyncOpenAI, str]:
    settings = await get_settings()
    api_key = settings.get("openai_api_key") or ""
    model = settings.get("openai_model") or "gpt-5.2"
    if not api_key:
        raise SuggestionsNotConfigured(
            "OpenAI API-Key ist nicht hinterlegt - bitte im Admin-Bereich unter Einstellungen eintragen."
        )
    return AsyncOpenAI(api_key=api_key), model


def _extract_json(text: str):
    if not text:
        return None
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"[\[{].*[\]}]", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


async def suggest_from_pantry(user: dict, max_results: int = 3, hint: Optional[str] = None) -> dict:
    """Ask the LLM to recommend up to `max_results` of the user's own recipes,
    favouring those whose ingredients overlap with the pantry and respecting allergies."""
    client, model = await _client()

    # Fetch full recipe library (capped)
    rec_docs = await recipes.find({}, {"_id": 0}).limit(200).to_list(200)
    if not rec_docs:
        return {"reasoning": "Du hast noch keine Rezepte gespeichert. Importiere oder lege welche an, dann kann ich dir konkrete Vorschläge machen.", "suggestions": []}

    pantry = await pantry_items.find({}, {"_id": 0}).to_list(300)

    pantry_summary = ", ".join(
        f"{p.get('name')} ({p.get('amount', 0)}{p.get('unit') or ''})" for p in pantry[:80]
    ) or "leer"
    allergies = ", ".join(user.get("allergies") or []) or "keine"
    diet = user.get("diet") or "keine spezielle"

    catalog = [
        {
            "id": r["id"],
            "title": r["title"],
            "category": r.get("category", ""),
            "cook_time_min": r.get("cook_time_min"),
            "ingredients": [i.get("name", "") for i in (r.get("ingredients") or [])][:25],
        }
        for r in rec_docs
    ]

    system = (
        "Du bist CookPilot, ein deutscher Küchen-Assistent. "
        "Du wählst aus einer GEGEBENEN Rezeptliste die besten 1-3 Vorschläge für JETZT aus. "
        "Bevorzuge Rezepte, deren Zutaten möglichst weit aus dem Vorrat abgedeckt sind. "
        "Schließe Rezepte aus, die Allergene oder Verbots-Diät enthalten. "
        "Erfinde KEINE neuen Rezepte."
    )

    user_prompt = (
        f"Vorrat: {pantry_summary}\n"
        f"Allergien (strikt vermeiden): {allergies}\n"
        f"Ernährungsform: {diet}\n"
        f"Wunsch des Nutzers: {hint or 'keine besondere Vorgabe'}\n\n"
        f"Verfügbare Rezepte (JSON):\n{json.dumps(catalog, ensure_ascii=False)}\n\n"
        f"Antworte NUR mit JSON in genau diesem Format:\n"
        f'{{"reasoning":"kurze deutsche Begründung","suggestions":[{{"recipe_id":"...","reason":"warum","missing_ingredients":["..."]}}]}}'
        f"\nMaximal {max_results} Vorschläge. Wenn keines passt: leeres suggestions-Array."
    )

    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
    except Exception:
        # Fallback without response_format (older models)
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
        )

    raw = resp.choices[0].message.content or ""
    parsed = _extract_json(raw) or {}
    suggestions_raw = parsed.get("suggestions") or []

    # Hydrate with full recipe info; drop bogus ids
    by_id = {r["id"]: r for r in rec_docs}
    suggestions = []
    for s in suggestions_raw[:max_results]:
        if not isinstance(s, dict):
            continue
        rid = s.get("recipe_id")
        if rid not in by_id:
            continue
        r = by_id[rid]
        suggestions.append({
            "recipe_id": rid,
            "title": r["title"],
            "image_url": r.get("image_url"),
            "category": r.get("category", ""),
            "cook_time_min": r.get("cook_time_min"),
            "reason": s.get("reason") or "",
            "missing_ingredients": s.get("missing_ingredients") or [],
        })

    return {
        "reasoning": parsed.get("reasoning") or "",
        "suggestions": suggestions,
    }
