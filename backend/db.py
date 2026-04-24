"""Database connection & settings accessor for CookPilot."""
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
from dotenv import load_dotenv
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


# Collections
users = db.users
invites = db.invites
recipes = db.recipes
shopping_items = db.shopping_items
pantry_items = db.pantry_items
chat_sessions = db.chat_sessions
chat_messages = db.chat_messages
app_settings = db.app_settings
receipts = db.receipts
purchases = db.purchases
widget_configs = db.widget_configs


SETTINGS_ID = "global"


async def get_settings() -> dict:
    """Return the single global settings document (create default if missing)."""
    doc = await app_settings.find_one({"id": SETTINGS_ID}, {"_id": 0})
    if not doc:
        default = {
            "id": SETTINGS_ID,
            "openai_api_key": "",
            "openai_model": "gpt-5.2",
            "smtp_host": "",
            "smtp_port": 587,
            "smtp_user": "",
            "smtp_password": "",
            "smtp_from": "",
            "smtp_use_tls": True,
            "aria_shared_secret": os.environ.get("ARIA_SHARED_SECRET", ""),
            "app_name": "CookPilot",
        }
        await app_settings.insert_one(default.copy())
        return default
    return doc


async def update_settings(patch: dict) -> dict:
    await app_settings.update_one(
        {"id": SETTINGS_ID},
        {"$set": patch},
        upsert=True,
    )
    return await get_settings()
