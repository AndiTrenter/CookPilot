"""Pydantic models for CookPilot."""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal
from datetime import datetime, timezone
import uuid


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------- USER / AUTH ----------
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_uuid)
    email: str
    name: str
    role: Literal["admin", "user"] = "user"
    password_hash: Optional[str] = None
    active: bool = True
    allergies: List[str] = Field(default_factory=list)
    diet: Optional[str] = None  # e.g. 'vegetarisch', 'vegan'
    external_id: Optional[str] = None  # aria user id mapping
    created_at: str = Field(default_factory=_now_iso)


class UserPublic(BaseModel):
    id: str
    email: str
    name: str
    role: str
    active: bool
    allergies: List[str] = []
    diet: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: UserPublic


class Invite(BaseModel):
    id: str = Field(default_factory=_uuid)
    email: str
    role: Literal["admin", "user"] = "user"
    token: str
    invited_by: str
    accepted: bool = False
    created_at: str = Field(default_factory=_now_iso)
    expires_at: str


class InviteCreate(BaseModel):
    email: str
    role: Literal["admin", "user"] = "user"


class AcceptInviteRequest(BaseModel):
    token: str
    name: str
    password: str = Field(min_length=8)


# ---------- RECIPES ----------
class Ingredient(BaseModel):
    name: str
    amount: float
    unit: str = ""  # e.g. g, ml, Stk


class Recipe(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_uuid)
    title: str
    description: str = ""
    category: str = ""  # Frühstück, Mittag, Dessert …
    tags: List[str] = Field(default_factory=list)
    servings: int = 2
    cook_time_min: Optional[int] = None
    difficulty: Optional[Literal["leicht", "mittel", "schwer"]] = None
    ingredients: List[Ingredient] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    favorite: bool = False
    image_url: Optional[str] = None
    source: Optional[str] = None  # manuell, ki, import
    owner_id: Optional[str] = None
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)


class RecipeCreate(BaseModel):
    title: str
    description: str = ""
    category: str = ""
    tags: List[str] = []
    servings: int = 2
    cook_time_min: Optional[int] = None
    difficulty: Optional[Literal["leicht", "mittel", "schwer"]] = None
    ingredients: List[Ingredient] = []
    steps: List[str] = []
    favorite: bool = False
    image_url: Optional[str] = None


class RecipeUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    servings: Optional[int] = None
    cook_time_min: Optional[int] = None
    difficulty: Optional[Literal["leicht", "mittel", "schwer"]] = None
    ingredients: Optional[List[Ingredient]] = None
    steps: Optional[List[str]] = None
    favorite: Optional[bool] = None
    image_url: Optional[str] = None


# ---------- SHOPPING ----------
class ShoppingItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_uuid)
    name: str
    amount: float = 1
    unit: str = ""
    category: str = ""  # Obst, Gemüse, Milchprodukte …
    checked: bool = False
    source: Optional[str] = None  # manuell, rezept:<id>, vorrat:<id>
    note: Optional[str] = None
    created_at: str = Field(default_factory=_now_iso)
    checked_at: Optional[str] = None


class ShoppingItemCreate(BaseModel):
    name: str
    amount: float = 1
    unit: str = ""
    category: str = ""
    note: Optional[str] = None


class ShoppingItemUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    unit: Optional[str] = None
    category: Optional[str] = None
    checked: Optional[bool] = None
    note: Optional[str] = None


class AddRecipeIngredientsRequest(BaseModel):
    recipe_id: str
    servings: Optional[int] = None  # override


# ---------- PANTRY ----------
class PantryItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_uuid)
    name: str
    amount: float = 0
    unit: str = ""
    min_amount: float = 0
    category: str = ""
    location: str = ""  # Kühlschrank, Vorratsschrank
    mhd: Optional[str] = None  # ISO date string
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)


class PantryItemCreate(BaseModel):
    name: str
    amount: float = 0
    unit: str = ""
    min_amount: float = 0
    category: str = ""
    location: str = ""
    mhd: Optional[str] = None


class PantryItemUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    unit: Optional[str] = None
    min_amount: Optional[float] = None
    category: Optional[str] = None
    location: Optional[str] = None
    mhd: Optional[str] = None


class PantryAdjust(BaseModel):
    delta: float  # positive or negative


# ---------- CHAT ----------
class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_uuid)
    session_id: str
    user_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: str = Field(default_factory=_now_iso)


class ChatSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_uuid)
    user_id: str
    title: str = "Neuer Chat"
    created_at: str = Field(default_factory=_now_iso)


class ChatSendRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


# ---------- SETTINGS ----------
class SettingsUpdate(BaseModel):
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    vision_model: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    smtp_use_tls: Optional[bool] = None
    aria_shared_secret: Optional[str] = None
    app_name: Optional[str] = None


class SettingsPublic(BaseModel):
    openai_api_key_set: bool
    openai_model: str
    vision_model: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_from: str
    smtp_use_tls: bool
    smtp_password_set: bool
    aria_shared_secret_set: bool
    app_name: str


# ---------- WIDGETS ----------
class WidgetConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_uuid)
    view: Literal["dashboard", "tablet"]
    widget: str  # key identifier (e.g. 'shopping_list', 'low_stock', 'favorites')
    order: int = 0
    visible: bool = True
    config: dict = Field(default_factory=dict)


class WidgetConfigUpdate(BaseModel):
    widgets: List[dict]


# ---------- PURCHASES (Phase 3 stub but queryable) ----------
class Purchase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_uuid)
    user_id: str
    product_name: str
    product_key: str  # normalised: e.g. 'milch'
    quantity: float = 1
    unit: str = ""
    price_cents: int = 0
    purchase_date: str  # ISO
    receipt_id: Optional[str] = None
    mhd: Optional[str] = None
    store: Optional[str] = None
    created_at: str = Field(default_factory=_now_iso)


class PurchaseCreate(BaseModel):
    product_name: str
    product_key: Optional[str] = None
    quantity: float = 1
    unit: str = ""
    price_cents: int = 0
    purchase_date: str
    receipt_id: Optional[str] = None
    mhd: Optional[str] = None
    store: Optional[str] = None


# ---------- ARIA ----------
class AriaSSORequest(BaseModel):
    shared_secret: str
    external_id: str
    email: str
    name: str
    role: Optional[Literal["admin", "user"]] = "user"


class AriaAllergyUpdate(BaseModel):
    shared_secret: str
    external_id: str
    allergies: List[str] = []
    diet: Optional[str] = None
