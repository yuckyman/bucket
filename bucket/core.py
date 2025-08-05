"""Core bucket system that orchestrates all components."""

import asyncio
import time
from datetime import datetime, timedelta

# Optional import for scheduling
try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False
    schedule = None
from typing import List, Optional, Dict, Any
from pathlib import Path
import os
from .database import Database
from .fetcher import ContentFetcher, RSSFetcher
from .summarizer import SummarizerFactory, BatchSummarizer
from .pdf_generator import PDFGenerator, ObsidianExporter
from .discord_bot import DiscordManager
from .api import BucketAPI
from .models import Article, Feed, Summary, ArticleStatus, ArticlePriority


class BucketCore:
    """Core bucket system that orchestrates all components."""
    
    def __init__(
        self,
        db_path: str = "bucket.db",
        output_dir: str = "output",
        obsidian_vault: Optional[str] = None,
        discord_token: Optional[str] = None,
        summarizer_type: str = "ollama",
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "llama2"
    ):
        self.db_path = db_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.db = Database(db_path)
        self.fetcher = ContentFetcher()
        self.rss_fetcher = RSSFetcher(self.fetcher)
        self.pdf_generator = PDFGenerator(output_dir=str(self.output_dir))
        
        # Optional components
        self.obsidian_exporter = None
        if obsidian_vault:
            self.obsidian_exporter = ObsidianExporter(obsidian_vault)
        
        self.discord_manager = None
        if discord_token:
            self.discord_manager = DiscordManager(discord_token)
        
        # Initialize summarizer
        self.summarizer = SummarizerFactory.create_summarizer(
            summarizer_type=summarizer_type,
            model_name=ollama_model,
            base_url=ollama_url
        )
        self.batch_summarizer = BatchSummarizer(self.summarizer)
        
        # API
        self.api = BucketAPI(self.db, self.pdf_generator)
        
        # State
        self.running = False
        self.scheduler = schedule.Scheduler() if SCHEDULE_AVAILABLE else None
    
    async def initialize(self):
        """Initialize the bucket system."""
        print("🪣 Initializing bucket system...")
        
        # Initialize database
        self.db.initialize()
        await self.db.create_tables()
        
        print("✅ Database initialized")
        
        # Test summarizer connection
        try:
            async with self.summarizer:
                print("✅ Summarizer connected")
        except Exception as e:
            print(f"⚠️  Summarizer connection failed: {e}")
        
        print("✅ Bucket system initialized")
    
    async def add_url(self, url: str, priority: ArticlePriority = ArticlePriority.MEDIUM, tags: List[str] = None) -> Optional[Article]:
        """Add a URL to the bucket."""
        try:
            async with self.fetcher:
                article = await self.fetcher.fetch_article(url)
            
            if not article:
                print(f"❌ Failed to fetch article: {url}")
                return None
            
            article.priority = priority
            article.tags = tags or []
            
            # Save to database (this would be implemented)
            # await self.save_article(article)
            
            print(f"✅ Added article: {article.title}")
            
            # Queue for summarization
            asyncio.create_task(self.summarize_article(article))
            
            return article
            
        except Exception as e:
            print(f"❌ Error adding URL {url}: {e}")
            return None
    
    async def add_feed(self, name: str, url: str, tags: List[str] = None) -> bool:
        """Add an RSS feed to the bucket."""
        try:
            feed = Feed(
                name=name,
                url=url,
                tags=tags or []
            )
            
            # Save feed to database (this would be implemented)
            # await self.save_feed(feed)
            
            print(f"✅ Added feed: {name}")
            return True
            
        except Exception as e:
            print(f"❌ Error adding feed {name}: {e}")
            return False
    
    async def fetch_feeds(self):
        """Fetch all RSS feeds."""
        print("📡 Fetching RSS feeds...")
        
        # This would get feeds from database
        feeds = []  # Mock feeds for now
        
        for feed in feeds:
            try:
                articles = await self.rss_fetcher.fetch_feed(str(feed.url))
                
                for article in articles:
                    article.tags.extend(feed.tags)
                    # Save article to database
                    # await self.save_article(article)
                    print(f"✅ Fetched: {article.title}")
                
            except Exception as e:
                print(f"❌ Error fetching feed {feed.name}: {e}")
    
    async def summarize_article(self, article: Article):
        """Summarize an article."""
        try:
            async with self.summarizer:
                summary = await self.summarizer.summarize(article)
            
            if summary:
                # Save summary to database (this would be implemented)
                # await self.save_summary(summary)
                article.status = ArticleStatus.SUMMARIZED
                print(f"✅ Summarized: {article.title}")
            else:
                print(f"⚠️  Failed to summarize: {article.title}")
                
        except Exception as e:
            print(f"❌ Error summarizing {article.title}: {e}")
    
    async def generate_briefing(
        self,
        title: str = "Daily Briefing",
        days_back: int = 7,
        tags: List[str] = None,
        priority: ArticlePriority = None
    ) -> Optional[str]:
        """Generate a PDF briefing."""
        try:
            # This would query database for articles
            articles = []  # Mock articles for now
            
            if not articles:
                print("⚠️  No articles found for briefing")
                return None
            
            # Filter articles
            if tags:
                articles = [a for a in articles if any(tag in a.tags for tag in tags)]
            
            if priority:
                articles = [a for a in articles if a.priority == priority]
            
            if not articles:
                print("⚠️  No articles match the criteria")
                return None
            
            # Generate PDF
            pdf_path = await self.pdf_generator.generate_briefing(
                articles=articles,
                title=title,
                date=datetime.now()
            )
            
            print(f"✅ Generated briefing: {pdf_path}")
            return pdf_path
            
        except Exception as e:
            print(f"❌ Error generating briefing: {e}")
            return None
    
    async def export_to_obsidian(self, articles: List[Article], category: str = "10.00"):
        """Export articles to Obsidian vault."""
        if not self.obsidian_exporter:
            print("⚠️  Obsidian exporter not configured")
            return
        
        try:
            for article in articles:
                file_path = self.obsidian_exporter.export_article(article, category)
                print(f"✅ Exported to Obsidian: {file_path}")
                
        except Exception as e:
            print(f"❌ Error exporting to Obsidian: {e}")
    
    def setup_scheduler(self):
        """Setup scheduled tasks."""
        if not SCHEDULE_AVAILABLE:
            print("⚠️  Schedule module not available, scheduling disabled")
            return
            
        # Daily briefing at 8 AM
        self.scheduler.every().day.at("08:00").do(
            lambda: asyncio.create_task(self.generate_briefing())
        )
        
        # Fetch RSS feeds every 4 hours
        self.scheduler.every(4).hours.do(
            lambda: asyncio.create_task(self.fetch_feeds())
        )
        
        # Summarize pending articles every hour
        self.scheduler.every().hour.do(
            lambda: asyncio.create_task(self.summarize_pending_articles())
        )
    
    async def summarize_pending_articles(self):
        """Summarize all pending articles."""
        # This would query database for pending articles
        pending_articles = []  # Mock data
        
        if pending_articles:
            summaries = await self.batch_summarizer.summarize_batch(pending_articles)
            print(f"✅ Summarized {len(summaries)} articles")
    
    async def start_discord_bot(self):
        """Start the Discord bot."""
        if not self.discord_manager:
            print("⚠️  Discord manager not configured")
            return
        
        try:
            await self.discord_manager.start_bot()
        except Exception as e:
            print(f"❌ Error starting Discord bot: {e}")
    
    async def start_api_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the API server."""
        import uvicorn
        
        app = self.api.get_app()
        
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info"
        )
        
        server = uvicorn.Server(config)
        await server.serve()
    
    async def run(self):
        """Run the bucket system."""
        await self.initialize()
        
        # Setup scheduler
        self.setup_scheduler()
        
        self.running = True
        print("🚀 Bucket system running...")
        
        # Start background tasks
        tasks = []
        
        # Start Discord bot if configured
        if self.discord_manager:
            tasks.append(asyncio.create_task(self.start_discord_bot()))
        
        # Start scheduler
        tasks.append(asyncio.create_task(self._run_scheduler()))
        
        # Wait for all tasks
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down bucket system...")
            self.running = False
    
    async def _run_scheduler(self):
        """Run the scheduler loop."""
        if not SCHEDULE_AVAILABLE or not self.scheduler:
            return
            
        while self.running:
            self.scheduler.run_pending()
            await asyncio.sleep(60)  # Check every minute
    
    async def close(self):
        """Close the bucket system."""
        self.running = False
        
        if self.discord_manager:
            await self.discord_manager.stop_bot()
        
        await self.db.close()
        print("✅ Bucket system closed")


# Convenience functions
async def create_bucket(
    db_path: str = "bucket.db",
    output_dir: str = "output",
    obsidian_vault: Optional[str] = None,
    discord_token: Optional[str] = None,
    summarizer_type: str = "ollama"
) -> BucketCore:
    """Create and initialize a bucket system."""
    bucket = BucketCore(
        db_path=db_path,
        output_dir=output_dir,
        obsidian_vault=obsidian_vault,
        discord_token=discord_token,
        summarizer_type=summarizer_type
    )
    
    await bucket.initialize()
    return bucket