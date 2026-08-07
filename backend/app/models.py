import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey,
    Integer, String, Text, JSON, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ScraperType(str, enum.Enum):
    wordpress = "wordpress"
    generic_rss = "generic_rss"
    html_sitemap = "html_sitemap"
    single_page = "single_page"


class ScrapeStatus(str, enum.Enum):
    running = "running"
    success = "success"
    partial = "partial"
    error = "error"
    cancelled = "cancelled"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Source(Base):
    __tablename__ = "sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    scraper_type = Column(Enum(ScraperType), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    frequency_hours = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_scraped_at = Column(DateTime(timezone=True), nullable=True)

    recipes = relationship("Recipe", back_populates="source", cascade="all, delete-orphan")
    scrape_runs = relationship("ScrapeRun", back_populates="source", cascade="all, delete-orphan")
    skipped_urls = relationship("SkippedUrl", back_populates="source", cascade="all, delete-orphan")


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    source_url = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    ingredients = Column(JSON, nullable=True)
    instructions = Column(JSON, nullable=True)
    prep_time = Column(Integer, nullable=True)
    cook_time = Column(Integer, nullable=True)
    servings = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    is_dairy_free = Column(Boolean, nullable=True)
    mentions_mammal_ingredients = Column(Boolean, default=False, nullable=False)
    disclaimer = Column(Text, nullable=True)
    needs_review = Column(Boolean, default=True, nullable=False)
    published = Column(Boolean, default=False, nullable=False)
    extracted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    source = relationship("Source", back_populates="recipes")


class SkippedUrl(Base):
    __tablename__ = "skipped_urls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    url = Column(String, unique=True, nullable=False, index=True)
    reason = Column(String, nullable=True)
    skipped_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    source = relationship("Source", back_populates="skipped_urls")


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(ScrapeStatus), default=ScrapeStatus.running, nullable=False)
    recipes_found = Column(Integer, default=0, nullable=False)
    recipes_added = Column(Integer, default=0, nullable=False)
    recipes_updated = Column(Integer, default=0, nullable=False)
    recipes_skipped_non_recipe = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)

    source = relationship("Source", back_populates="scrape_runs")
