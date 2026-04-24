"""Tests for rezepte.lidl.ch URL-Import + external search/refresh/status."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cookpilot-kitchen.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@cookpilot.local"
ADMIN_PASSWORD = "CookPilot!2026"

LIDL_URL = "https://rezepte.lidl.ch/rezepte/erdbeer-rhabarber-konfi"


@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def user_headers(admin_headers):
    """Create a non-admin user via invite to test 403s."""
    email = f"TEST_rimp_{uuid.uuid4().hex[:6]}@cookpilot.local"
    inv = requests.post(f"{API}/invites", json={"email": email, "role": "user"}, headers=admin_headers).json()
    accepted = requests.post(
        f"{API}/auth/accept-invite",
        json={"token": inv["token"], "name": "RecipeTestUser", "password": "Passwort!2026"},
    ).json()
    return {"Authorization": f"Bearer {accepted['token']}"}


# ---------- preview-url ----------
def test_preview_url_lidl(admin_headers):
    r = requests.post(f"{API}/recipes/preview-url", json={"url": LIDL_URL}, headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["title"]
    assert isinstance(data["ingredients"], list) and len(data["ingredients"]) >= 3
    assert isinstance(data["steps"], list) and len(data["steps"]) >= 5
    assert data.get("image_url")
    assert data.get("source", "").startswith("lidl:")
    assert data.get("cook_time_min") and data["cook_time_min"] > 0
    assert data.get("difficulty") in ("leicht", "mittel", "schwer")
    assert data.get("servings", 0) >= 1


def test_preview_url_invalid_scheme(admin_headers):
    r = requests.post(f"{API}/recipes/preview-url", json={"url": "ftp://example.com/x"}, headers=admin_headers)
    assert r.status_code == 400


def test_preview_url_unsupported_domain(admin_headers):
    r = requests.post(f"{API}/recipes/preview-url", json={"url": "https://example.com"}, headers=admin_headers)
    assert r.status_code == 400
    # Generic JSON-LD fallback now handles any URL; example.com has no Recipe JSON-LD
    body = r.text.lower()
    assert "unterst" in body or "json-ld" in body or "rezept" in body


# ---------- import-url (idempotent) ----------
def test_import_url_idempotent(admin_headers):
    r1 = requests.post(f"{API}/recipes/import-url", json={"url": LIDL_URL}, headers=admin_headers, timeout=30)
    assert r1.status_code == 200, r1.text
    rec1 = r1.json()
    rid1 = rec1["id"]
    assert rec1["source"].startswith("lidl:")
    assert "_id" not in rec1

    # Second import should return SAME id (no duplicate)
    r2 = requests.post(f"{API}/recipes/import-url", json={"url": LIDL_URL}, headers=admin_headers, timeout=30)
    assert r2.status_code == 200, r2.text
    rec2 = r2.json()
    assert rec2["id"] == rid1, "Second import created a duplicate - should return existing recipe"

    # GET should find it
    rg = requests.get(f"{API}/recipes/{rid1}", headers=admin_headers)
    assert rg.status_code == 200

    # cleanup
    requests.delete(f"{API}/recipes/{rid1}", headers=admin_headers)


def test_import_url_invalid_scheme(admin_headers):
    r = requests.post(f"{API}/recipes/import-url", json={"url": "not-a-url"}, headers=admin_headers)
    assert r.status_code == 400


def test_import_url_unsupported_domain(admin_headers):
    r = requests.post(f"{API}/recipes/import-url", json={"url": "https://example.com/foo"}, headers=admin_headers)
    assert r.status_code == 400
    body = r.text.lower()
    assert "unterst" in body or "json-ld" in body or "rezept" in body


# ---------- external/refresh ----------
def test_external_refresh_admin(admin_headers):
    r = requests.post(f"{API}/recipes/external/refresh", headers=admin_headers, timeout=45)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("ok") is True
    assert data.get("indexed", 0) > 0
    assert data.get("indexed_at")


def test_external_refresh_forbidden_for_non_admin(user_headers):
    r = requests.post(f"{API}/recipes/external/refresh", headers=user_headers)
    assert r.status_code == 403


# ---------- external/search ----------
def test_external_search_toblerone(admin_headers):
    r = requests.get(f"{API}/recipes/external/search", params={"q": "toblerone"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "count" in data and "results" in data
    assert data["count"] >= 1
    for res in data["results"]:
        assert "slug" in res
        assert "title" in res
        assert "source_url" in res
        assert "_id" not in res


def test_external_search_empty_q(admin_headers):
    r = requests.get(f"{API}/recipes/external/search", params={"q": ""}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["count"] >= 1


# ---------- external/status ----------
def test_external_status(admin_headers):
    r = requests.get(f"{API}/recipes/external/status", headers=admin_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["count"] > 0
    assert data.get("last_indexed_at")
    assert "source" in data


# ---------- Path collision regression ----------
def test_no_collision_external_search_vs_recipe_id(admin_headers):
    """GET /api/recipes/external/search must NOT be interpreted as /{recipe_id}=external."""
    r = requests.get(f"{API}/recipes/external/search", headers=admin_headers)
    assert r.status_code == 200
    # make sure it is not the 404 'Rezept nicht gefunden'
    assert "Rezept nicht gefunden" not in r.text


def test_no_collision_external_status_vs_recipe_id(admin_headers):
    r = requests.get(f"{API}/recipes/external/status", headers=admin_headers)
    assert r.status_code == 200
    assert "Rezept nicht gefunden" not in r.text
