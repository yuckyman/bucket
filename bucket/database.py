"""Database models and connection management for bucket."""

import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
# Optional SQLAlchemy imports
try:
    from sqlalchemy import (
        Column, Integer, String, Text, DateTime, Boolean, 
        ForeignKey, create_engine, MetaData, Table, Index
    )
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, relationship
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.pool import StaticPool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    # Mock classes for when SQLAlchemy is not available
    class Column:
        def __init__(self, *args, **kwargs): pass
    class Integer:
        def __init__(self, *args, **kwargs): pass
    class String:
        def __init__(self, *args, **kwargs): pass
    class Text:
        def __init__(self, *args, **kwargs): pass
    class DateTime:
        def __init__(self, *args, **kwargs): pass
    class Boolean:
        def __init__(self, *args, **kwargs): pass
    class ForeignKey:
        def __init__(self, *args, **kwargs): pass
    class Index:
        def __init__(self, *args, **kwargs): pass
    class declarative_base:
        def __init__(self, *args, **kwargs): pass
    class sessionmaker:
        def __init__(self, *args, **kwargs): pass
    class relationship:
        def __init__(self, *args, **kwargs): pass
    class create_async_engine:
        def __init__(self, *args, **kwargs): pass
    class AsyncSession:
        def __init__(self, *args, **kwargs): pass
    class StaticPool:
        def __init__(self, *args, **kwargs): pass
from .models import Article, Feed, Summary, Delivery, ArticleStatus, ArticlePriority


Base = declarative_base()


class ArticleTable(Base):
    """SQLAlchemy model for articles."""
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True)
    url = Column(String(2048), nullable=False, unique=True)
    title = Column(String(500), nullable=False)
    content = Column(Text)
    cleaned_content = Column(Text)
    author = Column(String(200))
    published_date = Column(DateTime)
    fetched_date = Column(DateTime)
    status = Column(String(20), default=ArticleStatus.PENDING.value)
    priority = Column(String(20), default=ArticlePriority.MEDIUM.value)
    tags = Column(Text)  # JSON string
    source = Column(String(200))
    word_count = Column(Integer)
    reading_time = Column(Integer)
    metadata = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    summaries = relationship("SummaryTable", back_populates="article")
    deliveries = relationship("DeliveryTable", back_populates="article")
    
    __table_args__ = (
        Index('idx_articles_status', 'status'),
        Index('idx_articles_priority', 'priority'),
        Index('idx_articles_created_at', 'created_at'),
        Index('idx_articles_url', 'url'),
    )


class SummaryTable(Base):
    """SQLAlchemy model for summaries."""
    __tablename__ = "summaries"
    
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    content = Column(Text, nullable=False)
    model_used = Column(String(100), nullable=False)
    tokens_used = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    article = relationship("ArticleTable", back_populates="summaries")


class FeedTable(Base):
    """SQLAlchemy model for RSS feeds."""
    __tablename__ = "feeds"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    url = Column(String(2048), nullable=False, unique=True)
    description = Column(Text)
    last_fetched = Column(DateTime)
    is_active = Column(Boolean, default=True)
    tags = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_feeds_url', 'url'),
        Index('idx_feeds_active', 'is_active'),
    )


class DeliveryTable(Base):
    """SQLAlchemy model for deliveries."""
    __tablename__ = "deliveries"
    
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    method = Column(String(20), nullable=False)
    status = Column(String(20), default="pending")
    destination = Column(String(500))
    file_path = Column(String(500))
    delivered_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    article = relationship("ArticleTable", back_populates="deliveries")
    
    __table_args__ = (
        Index('idx_deliveries_status', 'status'),
        Index('idx_deliveries_method', 'method'),
    )


class Database:
    """Database manager for bucket system."""
    
    def __init__(self, db_path: str = "bucket.db"):
        self.db_path = db_path
        self.engine = None
        self.SessionLocal = None
        self.async_engine = None
        self.AsyncSessionLocal = None
    
    def initialize(self, async_mode: bool = True):
        """Initialize database connection."""
        if not SQLALCHEMY_AVAILABLE:
            print("⚠️  SQLAlchemy not available, database features disabled")
            return
            
        if async_mode:
            self.async_engine = create_async_engine(
                f"sqlite+aiosqlite:///{self.db_path}",
                echo=False,
                poolclass=StaticPool,
            )
            self.AsyncSessionLocal = sessionmaker(
                self.async_engine, class_=AsyncSession, expire_on_commit=False
            )
        else:
            self.engine = create_engine(
                f"sqlite:///{self.db_path}",
                echo=False,
                poolclass=StaticPool,
            )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    async def create_tables(self):
        """Create all tables."""
        if not SQLALCHEMY_AVAILABLE:
            print("⚠️  SQLAlchemy not available, skipping table creation")
            return
            
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def get_session(self):
        """Get async database session."""
        if not self.AsyncSessionLocal:
            raise RuntimeError("Database not initialized in async mode")
        async with self.AsyncSessionLocal() as session:
            yield session
    
    def get_sync_session(self):
        """Get sync database session."""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized in sync mode")
        return self.SessionLocal()
    
    async def close(self):
        """Close database connections."""
        if self.async_engine:
            await self.async_engine.dispose()
        if self.engine:
            self.engine.dispose()


# Utility functions for model conversion
def article_to_model(article_table: ArticleTable) -> Article:
    """Convert ArticleTable to Article model."""
    import json
    
    return Article(
        id=article_table.id,
        url=article_table.url,
        title=article_table.title,
        content=article_table.content,
        cleaned_content=article_table.cleaned_content,
        author=article_table.author,
        published_date=article_table.published_date,
        fetched_date=article_table.fetched_date,
        status=ArticleStatus(article_table.status),
        priority=ArticlePriority(article_table.priority),
        tags=json.loads(article_table.tags) if article_table.tags else [],
        source=article_table.source,
        word_count=article_table.word_count,
        reading_time=article_table.reading_time,
        metadata=json.loads(article_table.metadata) if article_table.metadata else {},
        created_at=article_table.created_at,
        updated_at=article_table.updated_at,
    )


def model_to_article(article: Article) -> Dict[str, Any]:
    """Convert Article model to dict for database insertion."""
    import json
    
    return {
        "url": str(article.url),
        "title": article.title,
        "content": article.content,
        "cleaned_content": article.cleaned_content,
        "author": article.author,
        "published_date": article.published_date,
        "fetched_date": article.fetched_date,
        "status": article.status.value,
        "priority": article.priority.value,
        "tags": json.dumps(article.tags),
        "source": article.source,
        "word_count": article.word_count,
        "reading_time": article.reading_time,
        "metadata": json.dumps(article.metadata),
        "created_at": article.created_at,
        "updated_at": article.updated_at,
    }