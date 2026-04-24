"""Tests for lidl-kochen.de URL-Import, generic JSON-LD and live-search."""
import os
import asyncio
import pytest
import requests

import sys
sys.path.insert(0, "/app/backend")
from recipe_import_service import (
    _parse_ingredient,
    _iso_to_min,
    import_from_jsonld,
    RecipeImportError,
)

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cookpilot-kitchen.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@cookpilot.local"
ADMIN_PASSWORD = "CookPilot!2026"

LIDL_KOCHEN_URL = "https://www.lidl-kochen.de/rezeptwelt/gebratener-reis-mit-gemuese-150971"


@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ---------- Unit tests (no HTTP) ----------
def test_iso_duration_pt30m():
    assert _iso_to_min("PT30M") == 30


def test_iso_duration_pt1h15m():
    assert _iso_to_min("PT1H15M") == 75


def test_iso_duration_invalid_returns_none():
    assert _iso_to_min("") is None
    assert _iso_to_min(None) is None
    assert _iso_to_min("garbage") is None


def test_ingredient_parser_amount_unit_name():
    res = _parse_ingredient("300 g Langkornreis")
    assert res["name"] == "Langkornreis"
    assert res["amount"] == 300.0
    assert res["unit"] == "g"


def test_ingredient_parser_comma_decimal():
    res = _parse_ingredient("1,5 kg Mehl")
    assert res["amount"] == 1.5
    assert res["unit"] == "kg"
    assert res["name"] == "Mehl"


def test_ingredient_parser_no_amount():
    res = _parse_ingredient("Salz")
    assert res["name"] == "Salz"
    assert res["amount"] == 0


# ---------- Generic JSON-LD error on non-recipe page ----------
def test_generic_jsonld_no_recipe_raises():
    async def run():
        with pytest.raises(RecipeImportError):
            await import_from_jsonld("https://example.com", source_prefix="url")
    asyncio.run(run())


# ---------- lidl-kochen.de end-to-end import ----------
def test_import_url_lidl_kochen(admin_headers):
    r = requests.post(
        f"{API}/recipes/import-url",
        json={"url": LIDL_KOCHEN_URL},
        headers=admin_headers,
        timeout=45,
    )
    assert r.status_code == 200, r.text
    rec = r.json()
    assert "_id" not in rec
    assert rec["source"].startswith("lidl_kochen:gebratener-reis-mit-gemuese-150971")
    assert rec["servings"] == 4
    assert rec["cook_time_min"] == 30
    assert len(rec["ingredients"]) == 13
    # ingredients must be structured {name, amount, unit}
    for ing in rec["ingredients"]:
        assert set(["name", "amount", "unit"]).issubset(ing.keys())
    assert len(rec["steps"]) == 6
    assert rec["image_url"]
    assert rec["category"] == "Mittagessen"

    # idempotent
    r2 = requests.post(
        f"{API}/recipes/import-url",
        json={"url": LIDL_KOCHEN_URL},
        headers=admin_headers,
        timeout=45,
    )
    assert r2.status_code == 200
    assert r2.json()["id"] == rec["id"]

    # cleanup
    requests.delete(f"{API}/recipes/{rec['id']}", headers=admin_headers)


# ---------- live-search Lidl DE ----------
def test_live_search_lasagne(admin_headers):
    r = requests.get(
        f"{API}/recipes/external/live-search",
        params={"q": "lasagne", "source": "lidl_kochen"},
        headers=admin_headers,
        timeout=30,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "count" in data and "results" in data
    assert data["count"] >= 3, f"expected >=3 results for lasagne, got {data['count']}"
    lasagne_hits = [r for r in data["results"] if "lasagne" in (r["title"] or "").lower()]
    assert len(lasagne_hits) >= 1
    first = data["results"][0]
    for k in ("slug", "title", "image_url", "source_url", "source_name"):
        assert k in first, f"missing {k} in {first}"
    assert first["source_name"] == "lidl_kochen"


def test_live_search_missing_q(admin_headers):
    r = requests.get(
        f"{API}/recipes/external/live-search",
        params={"source": "lidl_kochen"},
        headers=admin_headers,
    )
    assert r.status_code == 422


def test_live_search_unknown_source(admin_headers):
    r = requests.get(
        f"{API}/recipes/external/live-search",
        params={"q": "lasagne", "source": "unknown"},
        headers=admin_headers,
    )
    assert r.status_code == 400
    assert "Unbekannte Quelle" in r.text


# ---------- combined external/search should mix cache + live ----------
def test_combined_external_search_lasagne(admin_headers):
    r = requests.get(
        f"{API}/recipes/external/search",
        params={"q": "lasagne"},
        headers=admin_headers,
        timeout=30,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    sources = {x.get("source_name") for x in data["results"]}
    # At least the live Lidl-DE must be present for "lasagne"
    assert "lidl_kochen" in sources


# ---------- generic JSON-LD via import-url (example.com -> 400) ----------
def test_import_url_generic_jsonld_fails_on_non_recipe(admin_headers):
    r = requests.post(
        f"{API}/recipes/import-url",
        json={"url": "https://example.com"},
        headers=admin_headers,
    )
    assert r.status_code == 400
