"""Admin settings routes."""
from fastapi import APIRouter, Depends
from db import get_settings, update_settings
from auth import require_admin
from models import SettingsUpdate, SettingsPublic

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _to_public(doc: dict) -> SettingsPublic:
    return SettingsPublic(
        openai_api_key_set=bool(doc.get("openai_api_key")),
        openai_model=doc.get("openai_model") or "gpt-5.2",
        smtp_host=doc.get("smtp_host") or "",
        smtp_port=int(doc.get("smtp_port") or 587),
        smtp_user=doc.get("smtp_user") or "",
        smtp_from=doc.get("smtp_from") or "",
        smtp_use_tls=bool(doc.get("smtp_use_tls", True)),
        smtp_password_set=bool(doc.get("smtp_password")),
        aria_shared_secret_set=bool(doc.get("aria_shared_secret")),
        app_name=doc.get("app_name") or "CookPilot",
    )


@router.get("", response_model=SettingsPublic)
async def read_settings(_: dict = Depends(require_admin)):
    s = await get_settings()
    return _to_public(s)


@router.put("", response_model=SettingsPublic)
async def write_settings(body: SettingsUpdate, _: dict = Depends(require_admin)):
    patch = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    s = await update_settings(patch)
    return _to_public(s)
