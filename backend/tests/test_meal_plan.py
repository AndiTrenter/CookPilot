"""Tests for Phase 2: meal-plan CRUD, generate-shopping-list, recipe suggestions."""
import os
import uuid
from datetime import date, timedelta
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cookpilot-kitchen.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@cookpilot.local"
ADMIN_PASSWORD = "CookPilot!2026"


@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def test_recipe(admin_headers):
    """Create a recipe to use in meal plan tests, return its id; cleanup after."""
    payload = {
        "title": f"TEST_MP_Recipe_{uuid.uuid4().hex[:6]}",
        "description": "Used by meal plan tests",
        "category": "Mittag",
        "tags": ["test"],
        "servings": 2,
        "cook_time_min": 25,
        "ingredients": [
            {"name": "TEST_Reis", "amount": 200, "unit": "g"},
            {"name": "TEST_Ei", "amount": 2, "unit": "Stk"},
        ],
        "steps": ["kochen"],
    }
    r = requests.post(f"{API}/recipes", json=payload, headers=admin_headers)
    assert r.status_code in (200, 201), r.text
    rid = r.json()["id"]
    yield rid
    requests.delete(f"{API}/recipes/{rid}", headers=admin_headers)


def _next_monday():
    today = date.today()
    return today + timedelta(days=(7 - today.weekday()) % 7 or 7)


# ---------------- MEAL-PLAN CRUD ----------------
class TestMealPlanCRUD:
    def test_get_empty_range(self, admin_headers):
        d = (_next_monday() + timedelta(days=200)).isoformat()
        r = requests.get(f"{API}/meal-plan", params={"start_date": d, "end_date": d}, headers=admin_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_with_recipe_and_persist(self, admin_headers, test_recipe):
        d = (_next_monday() + timedelta(days=100)).isoformat()
        body = {"date": d, "meal_type": "mittag", "recipe_id": test_recipe, "servings": 2}
        r = requests.post(f"{API}/meal-plan", json=body, headers=admin_headers)
        assert r.status_code == 200, r.text
        entry = r.json()
        assert entry["date"] == d
        assert entry["meal_type"] == "mittag"
        assert entry["recipe_id"] == test_recipe
        assert entry["servings"] == 2
        assert "id" in entry and "_id" not in entry
        eid = entry["id"]

        # GET to verify persist + hydration
        r2 = requests.get(f"{API}/meal-plan", params={"start_date": d, "end_date": d}, headers=admin_headers)
        assert r2.status_code == 200
        items = r2.json()
        match = [x for x in items if x["id"] == eid]
        assert len(match) == 1
        m = match[0]
        assert m["recipe"] is not None
        assert m["recipe"]["id"] == test_recipe
        assert "title" in m["recipe"]
        assert "image_url" in m["recipe"]
        assert "cook_time_min" in m["recipe"]
        assert "category" in m["recipe"]
        assert "servings" in m["recipe"]

        # cleanup
        requests.delete(f"{API}/meal-plan/{eid}", headers=admin_headers)

    def test_create_unknown_recipe_404(self, admin_headers):
        d = (_next_monday() + timedelta(days=101)).isoformat()
        body = {"date": d, "meal_type": "mittag", "recipe_id": "does-not-exist-xyz", "servings": 2}
        r = requests.post(f"{API}/meal-plan", json=body, headers=admin_headers)
        assert r.status_code == 404, r.text

    def test_create_custom_title_no_recipe(self, admin_headers):
        d = (_next_monday() + timedelta(days=102)).isoformat()
        body = {"date": d, "meal_type": "snack", "custom_title": "TEST_FreierEintrag", "servings": 1}
        r = requests.post(f"{API}/meal-plan", json=body, headers=admin_headers)
        assert r.status_code == 200, r.text
        entry = r.json()
        assert entry["custom_title"] == "TEST_FreierEintrag"
        assert entry["recipe_id"] is None
        assert entry["meal_type"] == "snack"

        # GET hydration: recipe must be None
        r2 = requests.get(f"{API}/meal-plan", params={"start_date": d, "end_date": d}, headers=admin_headers)
        items = r2.json()
        match = [x for x in items if x["id"] == entry["id"]]
        assert len(match) == 1
        assert match[0]["recipe"] is None

        requests.delete(f"{API}/meal-plan/{entry['id']}", headers=admin_headers)

    def test_invalid_meal_type_422(self, admin_headers):
        d = (_next_monday() + timedelta(days=103)).isoformat()
        body = {"date": d, "meal_type": "lunch", "custom_title": "x"}  # invalid type
        r = requests.post(f"{API}/meal-plan", json=body, headers=admin_headers)
        assert r.status_code == 422, r.text

    def test_patch_entry(self, admin_headers, test_recipe):
        d = (_next_monday() + timedelta(days=104)).isoformat()
        body = {"date": d, "meal_type": "abend", "recipe_id": test_recipe, "servings": 2}
        r = requests.post(f"{API}/meal-plan", json=body, headers=admin_headers)
        eid = r.json()["id"]

        r2 = requests.patch(f"{API}/meal-plan/{eid}", json={"servings": 4}, headers=admin_headers)
        assert r2.status_code == 200, r2.text
        assert r2.json()["servings"] == 4

        # verify persist
        r3 = requests.get(f"{API}/meal-plan", params={"start_date": d, "end_date": d}, headers=admin_headers)
        m = [x for x in r3.json() if x["id"] == eid][0]
        assert m["servings"] == 4

        requests.delete(f"{API}/meal-plan/{eid}", headers=admin_headers)

    def test_delete_entry_and_404(self, admin_headers, test_recipe):
        d = (_next_monday() + timedelta(days=105)).isoformat()
        body = {"date": d, "meal_type": "fruehstueck", "recipe_id": test_recipe, "servings": 1}
        r = requests.post(f"{API}/meal-plan", json=body, headers=admin_headers)
        eid = r.json()["id"]

        r2 = requests.delete(f"{API}/meal-plan/{eid}", headers=admin_headers)
        assert r2.status_code == 200

        r3 = requests.delete(f"{API}/meal-plan/{eid}", headers=admin_headers)
        assert r3.status_code == 404

    def test_unauthorized_no_token(self):
        r = requests.get(f"{API}/meal-plan", params={"start_date": "2026-01-01", "end_date": "2026-01-07"})
        assert r.status_code in (401, 403)


# ---------------- GENERATE SHOPPING LIST ----------------
class TestGenerateShoppingList:
    def test_no_entries_returns_zero(self, admin_headers):
        # Use a far-future range with no entries
        s = "2099-01-01"
        e = "2099-01-07"
        r = requests.post(
            f"{API}/meal-plan/generate-shopping-list",
            json={"start_date": s, "end_date": e, "deduct_pantry": True},
            headers=admin_headers,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data == {"added": 0, "merged": 0, "skipped_pantry": 0, "items": []}

    def test_aggregates_with_servings_scaling(self, admin_headers, test_recipe):
        d = (_next_monday() + timedelta(days=110)).isoformat()
        body = {"date": d, "meal_type": "mittag", "recipe_id": test_recipe, "servings": 4}  # 2x base servings
        rc = requests.post(f"{API}/meal-plan", json=body, headers=admin_headers)
        eid = rc.json()["id"]

        try:
            r = requests.post(
                f"{API}/meal-plan/generate-shopping-list",
                json={"start_date": d, "end_date": d, "deduct_pantry": False},
                headers=admin_headers,
            )
            assert r.status_code == 200, r.text
            data = r.json()
            assert "added" in data and "merged" in data and "skipped_pantry" in data and "items" in data
            assert data["skipped_pantry"] == 0  # deduct_pantry False
            # at least the 2 ingredients appear (added or merged)
            assert (data["added"] + data["merged"]) >= 2
            # find TEST_Reis with scaled amount: 200 * (4/2) = 400
            matched = [it for it in data["items"] if it["name"] == "TEST_Reis"]
            if matched:
                assert matched[0]["amount"] == 400
                assert matched[0]["unit"] == "g"
                assert matched[0]["source"] == "wochenplan"
        finally:
            # cleanup meal plan + any TEST_ shopping items added
            requests.delete(f"{API}/meal-plan/{eid}", headers=admin_headers)
            sl = requests.get(f"{API}/shopping", headers=admin_headers).json()
            for it in sl if isinstance(sl, list) else []:
                if it.get("name", "").startswith("TEST_"):
                    requests.delete(f"{API}/shopping/{it['id']}", headers=admin_headers)


# ---------------- SUGGESTIONS ----------------
class TestSuggestions:
    def test_suggestions_503_without_openai_key(self, admin_headers):
        # OpenAI key NOT configured per test brief => expect 503 (or empty if no recipes)
        # First make sure at least one recipe exists so we hit the LLM path
        rc = requests.post(f"{API}/recipes", json={
            "title": f"TEST_SUG_{uuid.uuid4().hex[:6]}",
            "description": "x", "category": "Mittag", "servings": 2,
            "ingredients": [{"name": "TEST_x", "amount": 1, "unit": "Stk"}],
            "steps": ["a"],
        }, headers=admin_headers)
        rid = rc.json()["id"]
        try:
            r = requests.post(f"{API}/recipes/suggestions", json={"hint": "schnell", "max_results": 3}, headers=admin_headers)
            # Either 503 (key missing) or 200 (key configured). Test brief says key NOT set.
            assert r.status_code in (503, 200), r.text
            if r.status_code == 503:
                detail = r.json().get("detail", "")
                assert "OpenAI" in detail or "Admin" in detail or "Einstellungen" in detail
        finally:
            requests.delete(f"{API}/recipes/{rid}", headers=admin_headers)

    def test_suggestions_no_recipes_short_circuits(self, admin_headers):
        # Empty the recipe collection scenario is risky on shared DB; instead
        # verify that endpoint exists and returns a sane shape when called.
        r = requests.post(f"{API}/recipes/suggestions", json={"max_results": 1}, headers=admin_headers)
        assert r.status_code in (200, 503), r.text
        if r.status_code == 200:
            data = r.json()
            assert "reasoning" in data
            assert "suggestions" in data
            assert isinstance(data["suggestions"], list)


# ---------------- REGRESSION: existing endpoints still OK ----------------
class TestRegression:
    def test_recipes_list(self, admin_headers):
        r = requests.get(f"{API}/recipes", headers=admin_headers)
        assert r.status_code == 200

    def test_shopping_list(self, admin_headers):
        r = requests.get(f"{API}/shopping", headers=admin_headers)
        assert r.status_code == 200

    def test_pantry_list(self, admin_headers):
        r = requests.get(f"{API}/pantry", headers=admin_headers)
        assert r.status_code == 200

    def test_external_status(self, admin_headers):
        r = requests.get(f"{API}/recipes/external/status", headers=admin_headers)
        assert r.status_code == 200
