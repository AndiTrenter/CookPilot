"""Admin seed and helpers."""
import os
import logging
from db import users
from models import User
from auth import hash_password

logger = logging.getLogger(__name__)


async def seed_admin():
    email = (os.environ.get("COOKPILOT_ADMIN_EMAIL") or "admin@cookpilot.local").lower()
    password = os.environ.get("COOKPILOT_ADMIN_PASSWORD") or "CookPilot!2026"

    existing = await users.find_one({"email": email}, {"_id": 0})
    if existing:
        # Ensure it's an admin and active
        if existing.get("role") != "admin" or not existing.get("active", True):
            await users.update_one({"id": existing["id"]}, {"$set": {"role": "admin", "active": True}})
            logger.info("Seed: promoted %s to admin", email)
        return

    admin = User(
        email=email,
        name="Administrator",
        role="admin",
        password_hash=hash_password(password),
    )
    await users.insert_one(admin.model_dump())
    logger.info("Seed: created admin %s", email)
