"""Comprehensive CookPilot backend API tests."""
import os
import io
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cookpilot-kitchen.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@cookpilot.local"
ADMIN_PASSWORD = "CookPilot!2026"


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and "user" in data
    assert data["user"]["email"] == ADMIN_EMAIL
    assert data["user"]["role"] == "admin"
    assert "_id" not in data["user"]
    return data["token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# --------- HEALTH & AUTH ---------
def test_health():
    r = requests.get(f"{API}/health")
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_auth_me(admin_headers):
    r = requests.get(f"{API}/auth/me", headers=admin_headers)
    assert r.status_code == 200
    u = r.json()
    assert u["email"] == ADMIN_EMAIL
    assert "_id" not in u


def test_auth_missing_token_401():
    r = requests.get(f"{API}/recipes")
    assert r.status_code in (401, 403)


def test_auth_invalid_login():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
    assert r.status_code in (400, 401)


# --------- RECIPES ---------
def test_recipes_crud(admin_headers):
    payload = {
        "title": "TEST_Spaghetti Bolognese",
        "description": "Klassisches italienisches Nudelgericht",
        "category": "Mittag",
        "tags": ["pasta", "fleisch"],
        "servings": 4,
        "cook_time_min": 40,
        "difficulty": "mittel",
        "ingredients": [
            {"name": "Spaghetti", "amount": 500, "unit": "g"},
            {"name": "Hackfleisch", "amount": 400, "unit": "g"},
        ],
        "steps": ["Nudeln kochen", "Sauce zubereiten"],
    }
    r = requests.post(f"{API}/recipes", json=payload, headers=admin_headers)
    assert r.status_code in (200, 201), r.text
    rec = r.json()
    assert rec["title"] == payload["title"]
    assert "_id" not in rec
    rid = rec["id"]

    # GET list
    r = requests.get(f"{API}/recipes", headers=admin_headers)
    assert r.status_code == 200
    assert any(x["id"] == rid for x in r.json())

    # GET detail
    r = requests.get(f"{API}/recipes/{rid}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["id"] == rid

    # PATCH
    r = requests.patch(f"{API}/recipes/{rid}", json={"servings": 6}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["servings"] == 6

    # favorite toggle
    r = requests.post(f"{API}/recipes/{rid}/favorite", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    # value should be boolean
    assert "favorite" in data or data.get("ok") is True

    # DELETE
    r = requests.delete(f"{API}/recipes/{rid}", headers=admin_headers)
    assert r.status_code in (200, 204)
    r = requests.get(f"{API}/recipes/{rid}", headers=admin_headers)
    assert r.status_code == 404


# --------- SHOPPING ---------
def test_shopping_flow(admin_headers):
    r = requests.post(f"{API}/shopping", json={"name": "TEST_Milch", "amount": 2, "unit": "L", "category": "Milchprodukte"}, headers=admin_headers)
    assert r.status_code in (200, 201), r.text
    item = r.json()
    assert "_id" not in item
    sid = item["id"]

    r = requests.get(f"{API}/shopping", headers=admin_headers)
    assert r.status_code == 200
    assert any(i["id"] == sid for i in r.json())

    r = requests.post(f"{API}/shopping/{sid}/toggle", headers=admin_headers)
    assert r.status_code == 200

    # clear-checked
    r = requests.post(f"{API}/shopping/clear-checked", headers=admin_headers)
    assert r.status_code == 200

    # Ensure item is gone (since toggled to checked then cleared)
    r = requests.get(f"{API}/shopping", headers=admin_headers)
    assert all(i["id"] != sid for i in r.json())

    # low-stock seed (add then low)
    p = requests.post(f"{API}/pantry", json={"name": "TEST_LowItem", "amount": 0, "min_amount": 5, "unit": "Stk"}, headers=admin_headers)
    assert p.status_code in (200, 201)
    r = requests.post(f"{API}/shopping/from-low-stock", headers=admin_headers)
    assert r.status_code == 200


def test_shopping_from_recipe(admin_headers):
    rec = requests.post(
        f"{API}/recipes",
        json={"title": "TEST_Pfannkuchen", "ingredients": [{"name": "Mehl", "amount": 250, "unit": "g"}], "steps": ["Rühren"]},
        headers=admin_headers,
    ).json()
    r = requests.post(f"{API}/shopping/from-recipe", json={"recipe_id": rec["id"]}, headers=admin_headers)
    assert r.status_code in (200, 201), r.text
    requests.delete(f"{API}/recipes/{rec['id']}", headers=admin_headers)


# --------- PANTRY ---------
def test_pantry_flow(admin_headers):
    r = requests.post(f"{API}/pantry", json={"name": "TEST_Butter", "amount": 3, "unit": "Stk", "min_amount": 2, "mhd": "2026-05-01"}, headers=admin_headers)
    assert r.status_code in (200, 201), r.text
    item = r.json()
    assert "_id" not in item
    pid = item["id"]

    r = requests.get(f"{API}/pantry", headers=admin_headers)
    assert r.status_code == 200

    r = requests.patch(f"{API}/pantry/{pid}", json={"location": "Kühlschrank"}, headers=admin_headers)
    assert r.status_code == 200

    r = requests.post(f"{API}/pantry/{pid}/adjust", json={"delta": -1}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["amount"] == 2

    r = requests.get(f"{API}/pantry/low-stock", headers=admin_headers)
    assert r.status_code == 200

    r = requests.delete(f"{API}/pantry/{pid}", headers=admin_headers)
    assert r.status_code in (200, 204)


# --------- INVITES + ACCEPT ---------
def test_invites_and_accept(admin_headers):
    email = f"TEST_invite_{uuid.uuid4().hex[:6]}@cookpilot.local"
    r = requests.post(f"{API}/invites", json={"email": email, "role": "user"}, headers=admin_headers)
    assert r.status_code in (200, 201), r.text
    inv = r.json()
    assert "token" in inv
    token = inv["token"]

    r = requests.get(f"{API}/auth/invite/{token}")
    assert r.status_code == 200
    assert r.json().get("email", "").lower() == email.lower()

    r = requests.post(f"{API}/auth/accept-invite", json={"token": token, "name": "Test User", "password": "Passwort!2026"})
    assert r.status_code in (200, 201), r.text
    data = r.json()
    assert "token" in data and data["user"]["email"].lower() == email.lower()

    # listing invites
    r = requests.get(f"{API}/invites", headers=admin_headers)
    assert r.status_code == 200


# --------- USERS ---------
def test_users_admin_only(admin_headers):
    r = requests.get(f"{API}/users", headers=admin_headers)
    assert r.status_code == 200
    users = r.json()
    assert any(u["email"] == ADMIN_EMAIL for u in users)
    assert all("_id" not in u for u in users)


def test_users_forbidden_for_non_admin(admin_headers):
    email = f"TEST_nonadmin_{uuid.uuid4().hex[:6]}@cookpilot.local"
    inv = requests.post(f"{API}/invites", json={"email": email, "role": "user"}, headers=admin_headers).json()
    accepted = requests.post(f"{API}/auth/accept-invite", json={"token": inv["token"], "name": "NA", "password": "Passwort!2026"}).json()
    user_headers = {"Authorization": f"Bearer {accepted['token']}"}
    r = requests.get(f"{API}/users", headers=user_headers)
    assert r.status_code == 403


# --------- SETTINGS ---------
def test_settings_flow(admin_headers):
    r = requests.get(f"{API}/settings", headers=admin_headers)
    assert r.status_code == 200
    s = r.json()
    assert "openai_api_key_set" in s
    assert "openai_api_key" not in s  # never leak secret

    r = requests.put(f"{API}/settings", json={"openai_api_key": "", "smtp_host": "smtp.example.com", "aria_shared_secret": "test-secret"}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["smtp_host"] == "smtp.example.com"
    assert r.json()["aria_shared_secret_set"] is True


# --------- WIDGETS ---------
def test_widgets(admin_headers):
    r = requests.get(f"{API}/widgets/catalog", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) > 0

    r = requests.get(f"{API}/widgets/dashboard", headers=admin_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    r = requests.get(f"{API}/widgets/tablet", headers=admin_headers)
    assert r.status_code == 200

    r = requests.put(
        f"{API}/widgets/dashboard",
        json={"widgets": [{"widget": "shopping_list"}, {"widget": "favorites"}]},
        headers=admin_headers,
    )
    assert r.status_code == 200


# --------- ARIA ---------
def test_aria_sso_and_aggregate(admin_headers):
    # Ensure secret is configured
    requests.put(f"{API}/settings", json={"aria_shared_secret": "test-secret"}, headers=admin_headers)

    ext_id = f"aria_{uuid.uuid4().hex[:8]}"
    email = f"TEST_aria_{ext_id}@example.com"
    r = requests.post(f"{API}/aria/sso", json={"shared_secret": "test-secret", "external_id": ext_id, "email": email, "name": "Aria User"})
    assert r.status_code == 200, r.text
    assert "token" in r.json()

    r = requests.post(f"{API}/aria/allergies", json={"shared_secret": "test-secret", "external_id": ext_id, "allergies": ["nuss"], "diet": "vegetarisch"})
    assert r.status_code == 200

    # add purchase and aggregate
    user_token = r.json() if False else None
    sso = requests.post(f"{API}/aria/sso", json={"shared_secret": "test-secret", "external_id": ext_id, "email": email, "name": "Aria User"}).json()
    headers = {"Authorization": f"Bearer {sso['token']}"}
    requests.post(f"{API}/purchases", json={"product_name": "Milch", "quantity": 2, "unit": "L", "price_cents": 299, "purchase_date": "2026-04-15"}, headers=headers)

    r = requests.get(
        f"{API}/aria/purchases/aggregate",
        params={"product": "milch", "start_date": "2026-04-01", "end_date": "2026-04-30"},
        headers={"X-Aria-Secret": "test-secret"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["count"] >= 1

    # wrong secret
    r = requests.get(
        f"{API}/aria/purchases/aggregate",
        params={"product": "milch", "start_date": "2026-04-01", "end_date": "2026-04-30"},
        headers={"X-Aria-Secret": "wrong"},
    )
    assert r.status_code == 401


# --------- CHAT ---------
def test_chat_without_api_key(admin_headers):
    # Make sure openai key is empty
    requests.put(f"{API}/settings", json={"openai_api_key": ""}, headers=admin_headers)
    r = requests.post(f"{API}/chat/send", json={"message": "Hallo"}, headers=admin_headers)
    assert r.status_code == 503, r.text
    assert "konfiguriert" in r.text.lower() or "nicht" in r.text.lower()

    r = requests.get(f"{API}/chat/sessions", headers=admin_headers)
    assert r.status_code == 200


# --------- RECEIPTS & PURCHASES ---------
def test_receipt_upload(admin_headers):
    # 1x1 jpg bytes
    jpg_bytes = bytes.fromhex(
        "ffd8ffe000104a46494600010100000100010000ffdb0043000806060706050806070707090908"
        "0a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434"
        "341f27393d38323c2e333432ffc0000b080001000101011100ffc4001f0000010501010101010100"
        "000000000000000102030405060708090a0bffc400b5100002010303020403050504040000017d"
        "01020300041105122131410613516107227114328191a1082342b1c11552d1f02433627282090a"
        "161718191a25262728292a3435363738393a434445464748494a535455565758595a636465666768"
        "696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5"
        "b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7"
        "f8f9faffda0008010100003f00fbfcffd9"
    )
    files = {"file": ("test.jpg", io.BytesIO(jpg_bytes), "image/jpeg")}
    r = requests.post(f"{API}/receipts/upload", files=files, headers=admin_headers)
    assert r.status_code in (200, 201), r.text
    assert "id" in r.json()

    r = requests.get(f"{API}/receipts", headers=admin_headers)
    assert r.status_code == 200


def test_purchases_crud(admin_headers):
    r = requests.post(f"{API}/purchases", json={"product_name": "Milch", "quantity": 2, "unit": "L", "price_cents": 299, "purchase_date": "2026-04-15"}, headers=admin_headers)
    assert r.status_code in (200, 201), r.text
    r = requests.get(f"{API}/purchases", params={"product": "milch"}, headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1
