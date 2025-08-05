"""Data models for the bucket system."""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
# Optional Pydantic imports
try:
    from pydantic import BaseModel, Field, HttpUrl
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # Mock classes for when Pydantic is not available
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    class Field:
        def __init__(self, default_factory=None, **kwargs):
            self.default_factory = default_factory
    class HttpUrl:
        def __init__(self, url):
            self.url = url
        def __str__(self):
            return self.url


class ArticleStatus(str, Enum):
    """Status of an article in the pipeline."""
    PENDING = "pending"
    FETCHED = "fetched"
    SUMMARIZED = "summarized"
    DELIVERED = "delivered"
    FAILED = "failed"


class ArticlePriority(str, Enum):
    """Priority levels for articles."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Article(BaseModel):
    """Model representing an article in the system."""
    id: Optional[int] = None
    url: HttpUrl
    title: str
    content: Optional[str] = None
    cleaned_content: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    fetched_date: Optional[datetime] = None
    status: ArticleStatus = ArticleStatus.PENDING
    priority: ArticlePriority = ArticlePriority.MEDIUM
    tags: List[str] = Field(default_factory=list)
    source: Optional[str] = None
    word_count: Optional[int] = None
    reading_time: Optional[int] = None  # in minutes
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Summary(BaseModel):
    """Model representing a summary of an article."""
    id: Optional[int] = None
    article_id: int
    content: str
    model_used: str
    tokens_used: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Feed(BaseModel):
    """Model representing an RSS feed."""
    id: Optional[int] = None
    name: str
    url: HttpUrl
    description: Optional[str] = None
    last_fetched: Optional[datetime] = None
    is_active: bool = True
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DeliveryMethod(str, Enum):
    """Methods for delivering content."""
    PDF = "pdf"
    MARKDOWN = "markdown"
    API = "api"
    DISCORD = "discord"


class DeliveryStatus(str, Enum):
    """Status of content delivery."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"


class Delivery(BaseModel):
    """Model representing a delivery of content."""
    id: Optional[int] = None
    article_id: int
    method: DeliveryMethod
    status: DeliveryStatus = DeliveryStatus.PENDING
    destination: Optional[str] = None
    file_path: Optional[str] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)