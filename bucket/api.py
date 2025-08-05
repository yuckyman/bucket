"""REST API for bucket system."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
# Optional FastAPI imports
try:
    from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None
    HTTPException = None
    Depends = None
    BackgroundTasks = None
    FileResponse = None
    JSONResponse = None
    CORSMiddleware = None

try:
    from pydantic import BaseModel, HttpUrl
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = None
    HttpUrl = None

try:
    import uvicorn
    UVICORN_AVAILABLE = True
except ImportError:
    UVICORN_AVAILABLE = False
    uvicorn = None
from .models import Article, Feed, Summary, ArticleStatus, ArticlePriority
from .database import Database
from .fetcher import ContentFetcher
from .summarizer import SummarizerFactory
from .pdf_generator import PDFGenerator


# API Models
if PYDANTIC_AVAILABLE:
    class ArticleCreate(BaseModel):
        url: HttpUrl
        priority: Optional[ArticlePriority] = ArticlePriority.MEDIUM
        tags: Optional[List[str]] = []


    class ArticleResponse(BaseModel):
        id: int
        url: str
        title: str
        author: Optional[str]
        published_date: Optional[datetime]
        status: ArticleStatus
        priority: ArticlePriority
        tags: List[str]
        word_count: Optional[int]
        reading_time: Optional[int]
        created_at: datetime


    class FeedCreate(BaseModel):
        name: str
        url: HttpUrl
        description: Optional[str] = None
        tags: Optional[List[str]] = []


    class BriefingRequest(BaseModel):
        title: str = "Daily Briefing"
        days_back: int = 7
        tags: Optional[List[str]] = None
        priority: Optional[ArticlePriority] = None
else:
    # Mock classes when Pydantic is not available
    class ArticleCreate:
        def __init__(self, **kwargs): pass
    class ArticleResponse:
        def __init__(self, **kwargs): pass
    class FeedCreate:
        def __init__(self, **kwargs): pass
    class BriefingRequest:
        def __init__(self, **kwargs): pass


class BucketAPI:
    """FastAPI application for bucket system."""
    
    def __init__(self, db: Database, pdf_generator: PDFGenerator):
        self.db = db
        self.pdf_generator = pdf_generator
        
        if not FASTAPI_AVAILABLE:
            raise RuntimeError("FastAPI not available")
            
        self.app = FastAPI(
            title="Bucket API",
            description="API for bucket read-later system",
            version="0.1.0"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Setup routes
        self.setup_routes()
    
    def setup_routes(self):
        """Setup API routes."""
        
        @self.app.get("/")
        async def root():
            """Root endpoint."""
            return {
                "message": "Bucket API",
                "version": "0.1.0",
                "status": "running"
            }
        
        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            return {"status": "healthy", "timestamp": datetime.utcnow()}
        
        # Articles endpoints
        @self.app.post("/articles", response_model=ArticleResponse)
        async def create_article(article_data: ArticleCreate, background_tasks: BackgroundTasks):
            """Add a new article to the bucket."""
            try:
                # Fetch the article
                fetcher = ContentFetcher()
                async with fetcher:
                    article = await fetcher.fetch_article(str(article_data.url))
                
                if not article:
                    raise HTTPException(status_code=400, detail="Failed to fetch article")
                
                # Set priority and tags
                article.priority = article_data.priority
                article.tags = article_data.tags or []
                
                # Save to database (this would be implemented)
                # article_id = await self.save_article(article)
                article.id = 1  # Mock ID for now
                
                # Queue for summarization
                background_tasks.add_task(self.summarize_article, article.id)
                
                return ArticleResponse(
                    id=article.id,
                    url=str(article.url),
                    title=article.title,
                    author=article.author,
                    published_date=article.published_date,
                    status=article.status,
                    priority=article.priority,
                    tags=article.tags,
                    word_count=article.word_count,
                    reading_time=article.reading_time,
                    created_at=article.created_at
                )
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/articles", response_model=List[ArticleResponse])
        async def get_articles(
            status: Optional[ArticleStatus] = None,
            priority: Optional[ArticlePriority] = None,
            tags: Optional[str] = None,
            limit: int = 50,
            offset: int = 0
        ):
            """Get articles with optional filtering."""
            # This would query the database
            # For now, return mock data
            return []
        
        @self.app.get("/articles/{article_id}", response_model=ArticleResponse)
        async def get_article(article_id: int):
            """Get a specific article."""
            # This would query the database
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Feeds endpoints
        @self.app.post("/feeds", response_model=Dict[str, Any])
        async def create_feed(feed_data: FeedCreate):
            """Add a new RSS feed."""
            try:
                feed = Feed(
                    name=feed_data.name,
                    url=feed_data.url,
                    description=feed_data.description,
                    tags=feed_data.tags or []
                )
                
                # Save to database (this would be implemented)
                # feed_id = await self.save_feed(feed)
                
                return {
                    "id": 1,  # Mock ID
                    "name": feed.name,
                    "url": str(feed.url),
                    "description": feed.description,
                    "tags": feed.tags,
                    "created_at": feed.created_at
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/feeds", response_model=List[Dict[str, Any]])
        async def get_feeds():
            """Get all RSS feeds."""
            # This would query the database
            return []
        
        # Briefing endpoints
        @self.app.post("/briefings/generate")
        async def generate_briefing(request: BriefingRequest):
            """Generate a PDF briefing."""
            try:
                # Get articles for briefing (this would query the database)
                articles = []  # Mock articles
                
                if not articles:
                    raise HTTPException(status_code=404, detail="No articles found for briefing")
                
                # Generate PDF
                pdf_path = await self.pdf_generator.generate_briefing(
                    articles=articles,
                    title=request.title,
                    date=datetime.now()
                )
                
                return {
                    "message": "Briefing generated successfully",
                    "pdf_path": pdf_path,
                    "article_count": len(articles)
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/briefings/{filename}")
        async def download_briefing(filename: str):
            """Download a generated briefing."""
            file_path = Path(self.pdf_generator.output_dir) / filename
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="Briefing not found")
            
            return FileResponse(
                path=str(file_path),
                filename=filename,
                media_type="application/pdf"
            )
        
        @self.app.get("/briefings")
        async def list_briefings():
            """List available briefings."""
            output_dir = Path(self.pdf_generator.output_dir)
            briefings = []
            
            for file_path in output_dir.glob("*.pdf"):
                briefings.append({
                    "filename": file_path.name,
                    "size": file_path.stat().st_size,
                    "created": datetime.fromtimestamp(file_path.stat().st_ctime)
                })
            
            return sorted(briefings, key=lambda x: x["created"], reverse=True)
        
        # Stats endpoints
        @self.app.get("/stats")
        async def get_stats():
            """Get system statistics."""
            # This would query the database
            return {
                "total_articles": 0,
                "articles_today": 0,
                "total_feeds": 0,
                "pending_summaries": 0,
                "total_words": 0,
                "total_reading_time": 0
            }
    
    async def summarize_article(self, article_id: int):
        """Summarize an article in the background."""
        try:
            # This would get the article from database and summarize it
            print(f"Summarizing article {article_id}")
        except Exception as e:
            print(f"Error summarizing article {article_id}: {e}")
    
    def get_app(self) -> FastAPI:
        """Get the FastAPI application."""
        return self.app


def create_api_app(db_path: str = "bucket.db") -> FastAPI:
    """Create and configure the API application."""
    db = Database(db_path)
    pdf_generator = PDFGenerator()
    
    api = BucketAPI(db, pdf_generator)
    return api.get_app()


def run_api_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False
):
    """Run the API server."""
    app = create_api_app()
    
    uvicorn.run(
        "bucket.api:create_api_app",
        host=host,
        port=port,
        reload=reload
    )