"""OpenAI LLM integration for CookPilot (direct SDK, no third-party wrappers)."""
import logging
from typing import List, Dict
from openai import AsyncOpenAI
from db import get_settings

logger = logging.getLogger(__name__)


class LLMNotConfigured(Exception):
    pass


async def _client() -> tuple[AsyncOpenAI, str]:
    settings = await get_settings()
    api_key = settings.get("openai_api_key") or ""
    model = settings.get("openai_model") or "gpt-5.2"
    if not api_key:
        raise LLMNotConfigured(
            "OpenAI API-Key ist noch nicht hinterlegt. Bitte im Admin-Bereich unter Einstellungen eintragen."
        )
    return AsyncOpenAI(api_key=api_key), model


def build_system_prompt(user: dict, pantry: List[dict], recipes_count: int) -> str:
    allergies = ", ".join(user.get("allergies", []) or []) or "keine"
    diet = user.get("diet") or "keine spezielle"
    pantry_summary = (
        ", ".join([f"{p['name']} ({p.get('amount',0)}{p.get('unit','')})" for p in pantry[:40]])
        or "unbekannt"
    )
    return (
        "Du bist CookPilot, ein freundlicher deutscher Küchen-Assistent. "
        "Antworte immer auf Deutsch, praxisnah und knapp. "
        "Schlage Rezepte, Mengen, Einkaufslisten und Wochenpläne vor.\n"
        f"Allergien des Nutzers: {allergies}. Berücksichtige diese strikt.\n"
        f"Ernährungsform: {diet}.\n"
        f"Aktueller Vorrat: {pantry_summary}.\n"
        f"Anzahl gespeicherter Rezepte: {recipes_count}.\n"
        "Wenn der Nutzer nach Rezepten fragt, bevorzuge Zutaten aus dem Vorrat. "
        "Gib bei Mengen immer metrische Einheiten an."
    )


async def chat_completion(system_prompt: str, history: List[Dict[str, str]], user_message: str) -> str:
    client, model = await _client()
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=messages,
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:
        logger.exception("OpenAI call failed")
        # Try fallback model if new one not available
        fallback = "gpt-4o"
        if model != fallback:
            try:
                resp = await client.chat.completions.create(
                    model=fallback,
                    messages=messages,
                )
                return resp.choices[0].message.content or ""
            except Exception as exc2:
                raise RuntimeError(f"OpenAI Fehler: {exc2}") from exc2
        raise RuntimeError(f"OpenAI Fehler: {exc}") from exc
