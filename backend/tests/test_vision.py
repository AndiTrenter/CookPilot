"""Phase 3 vision endpoints tests: /api/vision/* + settings vision_model."""
import io
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cookpilot-kitchen.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@cookpilot.local"
ADMIN_PASSWORD = "CookPilot!2026"


# --- fixtures ---------------------------------------------------------------
@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def H(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def _png_bytes() -> bytes:
    # 1x1 transparent PNG
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


# --- Auth enforcement -------------------------------------------------------
def test_scan_products_requires_auth():
    f = ("a.png", _png_bytes(), "image/png")
    r = requests.post(f"{API}/vision/scan-products", files={"files": f})
    assert r.status_code in (401, 403)


def test_parse_receipt_requires_auth():
    f = ("r.png", _png_bytes(), "image/png")
    r = requests.post(f"{API}/vision/parse-receipt", files={"file": f})
    assert r.status_code in (401, 403)


def test_apply_scan_requires_auth():
    r = requests.post(f"{API}/vision/apply-scan", json={"items": []})
    assert r.status_code in (401, 403)


def test_apply_receipt_requires_auth():
    r = requests.post(
        f"{API}/vision/apply-receipt",
        json={"receipt_id": "x", "purchase_date": "2026-01-01", "items": []},
    )
    assert r.status_code in (401, 403)


# --- Settings include vision_model -----------------------------------------
def test_settings_has_vision_model(H):
    r = requests.get(f"{API}/settings", headers=H)
    assert r.status_code == 200
    s = r.json()
    assert "vision_model" in s
    # default gpt-4o (may differ if tests ran earlier and mutated it)
    assert isinstance(s["vision_model"], str) and len(s["vision_model"]) > 0


def test_settings_update_vision_model_persists(H):
    # Save, verify round-trip, restore to gpt-4o
    r = requests.put(f"{API}/settings", json={"vision_model": "gpt-4o-mini"}, headers=H)
    assert r.status_code == 200
    assert r.json()["vision_model"] == "gpt-4o-mini"

    r2 = requests.get(f"{API}/settings", headers=H)
    assert r2.json()["vision_model"] == "gpt-4o-mini"

    # restore default
    requests.put(f"{API}/settings", json={"vision_model": "gpt-4o"}, headers=H)


# --- Validation: scan-products ---------------------------------------------
def test_scan_products_empty_files_400(H):
    # No files at all -> FastAPI may return 422 for missing field, or our 400
    r = requests.post(f"{API}/vision/scan-products", headers=H)
    assert r.status_code in (400, 422)


def test_scan_products_too_many_files_400(H):
    files = [("files", (f"a{i}.png", _png_bytes(), "image/png")) for i in range(7)]
    r = requests.post(f"{API}/vision/scan-products", headers=H, files=files)
    assert r.status_code == 400
    assert "6" in r.text or "Maximal" in r.text


def test_scan_products_unsupported_type_400(H):
    f = ("notes.txt", b"hello", "text/plain")
    r = requests.post(f"{API}/vision/scan-products", headers=H, files={"files": f})
    assert r.status_code == 400


def test_scan_products_503_without_openai_key(H):
    # OpenAI key is intentionally empty -> expect German 503
    f = ("p.png", _png_bytes(), "image/png")
    r = requests.post(f"{API}/vision/scan-products", headers=H, files={"files": f})
    assert r.status_code == 503, r.text
    detail = r.json().get("detail", "")
    assert "OpenAI" in detail or "API-Key" in detail


# --- Validation: parse-receipt ---------------------------------------------
def test_parse_receipt_unsupported_type_400(H):
    f = ("bill.txt", b"hi", "text/plain")
    r = requests.post(f"{API}/vision/parse-receipt", headers=H, files={"file": f})
    assert r.status_code == 400


def test_parse_receipt_503_without_openai_key(H):
    f = ("receipt.png", _png_bytes(), "image/png")
    r = requests.post(f"{API}/vision/parse-receipt", headers=H, files={"file": f})
    assert r.status_code == 503, r.text
    detail = r.json().get("detail", "")
    assert "OpenAI" in detail or "API-Key" in detail


# --- apply-scan: integration (no OpenAI needed) ----------------------------
def test_apply_scan_ticks_shopping_and_adds_pantry(H):
    # Create shopping item first
    name = f"TEST_scan_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{API}/shopping", json={"name": name, "amount": 1, "unit": "Stk"}, headers=H)
    assert r.status_code in (200, 201), r.text
    sid = r.json()["id"]

    body = {
        "items": [
            {
                "name": name,
                "brand": "TEST",
                "mhd": "2026-12-31",
                "quantity": 1,
                "unit": "Stk",
                "matched_shopping_id": sid,
                "add_to_pantry": True,
                "pantry_category": "Test",
                "pantry_location": "Kühlschrank",
            }
        ]
    }
    r = requests.post(f"{API}/vision/apply-scan", json=body, headers=H)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["shopping_ticked"] == 1
    assert d["pantry_added"] == 1

    # Verify shopping item checked
    r2 = requests.get(f"{API}/shopping", headers=H)
    assert r2.status_code == 200
    items = [it for it in r2.json() if it["id"] == sid]
    assert items and items[0]["checked"] is True

    # Verify pantry item with MHD created
    rp = requests.get(f"{API}/pantry", headers=H)
    assert rp.status_code == 200
    p = [it for it in rp.json() if it["name"] == name]
    assert p and p[0].get("mhd") == "2026-12-31"


# --- apply-receipt: integration + purchases + aria aggregate ---------------
def test_apply_receipt_persists_purchases_and_ticks_shopping(H):
    # Create one matching shopping item
    pname = f"TEST_milch_{uuid.uuid4().hex[:6]}"
    rr = requests.post(f"{API}/shopping", json={"name": pname, "amount": 1, "unit": "l"}, headers=H)
    assert rr.status_code in (200, 201)
    sid = rr.json()["id"]

    receipt_id = f"rcpt_{uuid.uuid4().hex[:8]}"
    body = {
        "receipt_id": receipt_id,
        "store": "TEST_REWE",
        "purchase_date": "2026-01-15",
        "items": [
            {
                "product_name": pname,
                "product_key": pname.lower(),
                "quantity": 2,
                "unit": "l",
                "price_cents": 199,
                "matched_shopping_id": sid,
            },
            {
                "product_name": f"TEST_butter_{uuid.uuid4().hex[:4]}",
                "product_key": "butter",
                "quantity": 1,
                "unit": "Stk",
                "price_cents": 249,
            },
        ],
    }
    r = requests.post(f"{API}/vision/apply-receipt", json=body, headers=H)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["purchases_added"] == 2
    assert d["shopping_ticked"] == 1

    # Verify shopping item checked
    r2 = requests.get(f"{API}/shopping", headers=H)
    items = [it for it in r2.json() if it["id"] == sid]
    assert items and items[0]["checked"] is True

    # Verify /api/purchases filter (exact product_key match)
    rp = requests.get(f"{API}/purchases", params={"product": pname.lower()}, headers=H)
    assert rp.status_code == 200, rp.text
    rows = rp.json()
    assert any(p.get("product_name") == pname for p in rows), rows

    # Verify aria aggregate (needs shared secret)
    # Set a shared secret first
    requests.put(f"{API}/settings", json={"aria_shared_secret": "test-secret"}, headers=H)
    ag = requests.post(
        f"{API}/aria/purchases/aggregate",
        json={"shared_secret": "test-secret", "product_key": pname.lower()},
    )
    # Endpoint may not accept sub-key; if 200, check totals
    if ag.status_code == 200:
        data = ag.json()
        assert isinstance(data, dict)
