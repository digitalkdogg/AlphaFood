import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import ScraperType, ScrapeStatus


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    is_active: bool
    created_at: datetime


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SourceCreate(BaseModel):
    name: str
    url: str
    scraper_type: ScraperType
    active: bool = True
    frequency_hours: Optional[int] = None


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    scraper_type: Optional[ScraperType] = None
    active: Optional[bool] = None
    frequency_hours: Optional[int] = None


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    url: str
    scraper_type: ScraperType
    active: bool
    frequency_hours: Optional[int]
    created_at: datetime
    last_scraped_at: Optional[datetime]


class IngredientItem(BaseModel):
    quantity: str = ""
    unit: str = ""
    item: str = ""


class RecipeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    source_url: str
    image_url: Optional[str]
    prep_time: Optional[int]
    cook_time: Optional[int]
    is_dairy_free: Optional[bool]
    needs_review: bool
    published: bool
    created_at: datetime
    source_id: uuid.UUID


class RecipeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_id: uuid.UUID
    source_url: str
    title: str
    ingredients: Optional[Any]
    instructions: Optional[Any]
    prep_time: Optional[int]
    cook_time: Optional[int]
    servings: Optional[str]
    image_url: Optional[str]
    is_dairy_free: Optional[bool]
    mentions_mammal_ingredients: bool
    disclaimer: Optional[str] = None
    needs_review: bool
    published: bool
    extracted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class ScrapeRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_id: Optional[uuid.UUID]
    started_at: datetime
    finished_at: Optional[datetime]
    status: ScrapeStatus
    recipes_found: int
    recipes_added: int
    recipes_updated: int
    recipes_skipped_non_recipe: int
    error_message: Optional[str]


class ScrapeStartResponse(BaseModel):
    run_id: str
    status: str = "started"


class RecipesPage(BaseModel):
    items: list[RecipeListItem]
    total: int
    page: int
    limit: int


class SkippedUrlOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_id: uuid.UUID
    url: str
    reason: Optional[str]
    permanent: bool = False
    skipped_at: datetime


class SkippedUrlsPage(BaseModel):
    items: list[SkippedUrlOut]
    total: int
    page: int
    limit: int
