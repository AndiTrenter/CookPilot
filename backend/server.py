"""CookPilot main FastAPI application.

Fully independent of Emergent. Designed to run as a single Docker container
on Unraid. The React frontend is compiled to static files during the Docker
build and is served by this FastAPI app at '/'. The API lives under '/api'.

During local Emergent development the React dev server runs separately on
port 3000 and this app is reached via REACT_APP_BACKEND_URL.
"""
import os
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("cookpilot")

from db import client  # noqa: E402
from seed import seed_admin  # noqa: E402

# Routers
from routers.auth_router import router as auth_router  # noqa: E402
from routers.users_router import router as users_router  # noqa: E402
from routers.invites_router import router as invites_router  # noqa: E402
from routers.recipes_router import router as recipes_router  # noqa: E402
from routers.shopping_router import router as shopping_router  # noqa: E402
from routers.pantry_router import router as pantry_router  # noqa: E402
from routers.chat_router import router as chat_router  # noqa: E402
from routers.settings_router import router as settings_router  # noqa: E402
from routers.widgets_router import router as widgets_router  # noqa: E402
from routers.aria_router import router as aria_router  # noqa: E402
from routers.receipts_router import router as receipts_router, purchase_router  # noqa: E402
from routers.vision_router import router as vision_router  # noqa: E402
from routers.meal_plan_router import router as meal_plan_router  # noqa: E402
from routers.products_router import router as products_router, seed_products  # noqa: E402

APP_VERSION = os.environ.get("APP_VERSION", "0.1.0")

app = FastAPI(title="CookPilot", version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api")
async def api_root():
    return {"service": "CookPilot", "version": APP_VERSION}


@app.get("/api/health")
async def api_health():
    return {"ok": True, "version": APP_VERSION}


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(invites_router)
app.include_router(recipes_router)
app.include_router(shopping_router)
app.include_router(pantry_router)
app.include_router(chat_router)
app.include_router(settings_router)
app.include_router(widgets_router)
app.include_router(aria_router)
app.include_router(receipts_router)
app.include_router(purchase_router)
app.include_router(vision_router)
app.include_router(meal_plan_router)
app.include_router(products_router)


# Serve compiled frontend in production container.
FRONTEND_DIR = Path(os.environ.get("COOKPILOT_FRONTEND_DIR", "/app/frontend_dist"))
if FRONTEND_DIR.exists() and (FRONTEND_DIR / "index.html").exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(FRONTEND_DIR / "static")) if (FRONTEND_DIR / "static").exists() else StaticFiles(directory=str(FRONTEND_DIR)),
        name="static",
    )

    @app.get("/{full_path:path}")
    async def spa_catch_all(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        asset = FRONTEND_DIR / full_path
        if full_path and asset.exists() and asset.is_file():
            return FileResponse(str(asset))
        return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.on_event("startup")
async def on_startup():
    logger.info("CookPilot startup - v%s", APP_VERSION)
    await seed_admin()
    inserted = await seed_products()
    if inserted:
        logger.info("Produkt-Katalog: %d neue Einträge angelegt", inserted)


@app.on_event("shutdown")
async def on_shutdown():
    client.close()
