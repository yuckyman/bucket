"""Modular RSS feed manager for dynamic operations and briefing generation."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    feedparser = None

from .models import Feed, Article, ArticleStatus, ArticlePriority
from .database import Database
from .fetcher import RSSFetcher, ContentFetcher


@dataclass
class RSSBriefingConfig:
    """Configuration for RSS briefing generation."""
    max_articles_per_feed: int = 5
    max_total_articles: int = 25
    days_back: int = 7
    include_summaries: bool = True
    sort_by_priority: bool = True
    group_by_feed: bool = True


class RSSManager:
    """Modular RSS feed manager for dynamic operations."""
    
    def __init__(self, database: Database):
        """Initialize RSS manager with database connection."""
        self.db = database
        self.rss_fetcher = RSSFetcher()
        self.content_fetcher = ContentFetcher()
    
    async def get_active_feeds(self) -> List[Feed]:
        """Get all active RSS feeds."""
        return await self.db.get_feeds(active_only=True)
    
    async def add_feed(self, name: str, url: str, tags: List[str] = None, 
                      description: str = None) -> Feed:
        """Add a new RSS feed."""
        feed = Feed(
            name=name,
            url=url,
            description=description,
            tags=tags or [],
            is_active=True
        )
        return await self.db.add_feed(feed)
    
    async def update_feed(self, feed_id: int, **kwargs) -> Optional[Feed]:
        """Update an existing RSS feed."""
        return await self.db.update_feed(feed_id, **kwargs)
    
    async def remove_feed(self, feed_id: int) -> bool:
        """Remove an RSS feed."""
        return await self.db.delete_feed(feed_id)
    
    async def toggle_feed(self, feed_id: int, active: bool = None) -> Optional[Feed]:
        """Toggle feed active status or set explicitly."""
        feed = await self.db.get_feed(feed_id)
        if not feed:
            return None
        
        new_status = not feed.is_active if active is None else active
        return await self.db.update_feed(feed_id, is_active=new_status)
    
    async def fetch_feed_articles(self, feed: Feed, max_articles: int = 10) -> List[Article]:
        """Fetch latest articles from a specific RSS feed."""
        try:
            articles = await self.rss_fetcher.fetch_articles(str(feed.url), max_articles)
            
            # Process and save articles to database
            saved_articles = []
            for article_data in articles:
                try:
                    # Check if article already exists
                    existing = await self.db.get_article_by_url(article_data['url'])
                    if existing:
                        continue
                    
                    # Create new article
                    article = Article(
                        url=article_data['url'],
                        title=article_data['title'],
                        content=article_data.get('content', ''),
                        author=article_data.get('author'),
                        published_date=article_data.get('published_date'),
                        source=feed.name,
                        tags=feed.tags.copy(),
                        status=ArticleStatus.FETCHED,
                        priority=ArticlePriority.MEDIUM
                    )
                    
                    saved_article = await self.db.add_article(article)
                    saved_articles.append(saved_article)
                    
                except Exception as e:
                    print(f"❌ Error processing article from {feed.name}: {e}")
                    continue
            
            # Update feed's last_fetched timestamp
            await self.db.update_feed(feed.id, last_fetched=datetime.utcnow())
            
            return saved_articles
            
        except Exception as e:
            print(f"❌ Error fetching from feed {feed.name}: {e}")
            return []
    
    async def fetch_all_feeds(self, max_articles_per_feed: int = 10) -> Dict[str, List[Article]]:
        """Fetch articles from all active RSS feeds."""
        feeds = await self.get_active_feeds()
        results = {}
        
        tasks = []
        for feed in feeds:
            task = self.fetch_feed_articles(feed, max_articles_per_feed)
            tasks.append((feed.name, task))
        
        # Run all fetches concurrently
        for feed_name, task in tasks:
            try:
                articles = await task
                results[feed_name] = articles
                print(f"✅ Fetched {len(articles)} new articles from {feed_name}")
            except Exception as e:
                print(f"❌ Error fetching {feed_name}: {e}")
                results[feed_name] = []
        
        return results
    
    async def generate_rss_briefing(self, config: RSSBriefingConfig = None) -> Dict[str, Any]:
        """Generate a comprehensive RSS briefing."""
        if config is None:
            config = RSSBriefingConfig()
        
        # Get recent articles from RSS feeds
        cutoff_date = datetime.utcnow() - timedelta(days=config.days_back)
        recent_articles = await self.db.get_articles_since(cutoff_date, limit=config.max_total_articles)
        
        # Filter for RSS-sourced articles
        rss_articles = [a for a in recent_articles if a.source]
        
        # Get active feeds
        feeds = await self.get_active_feeds()
        
        # Group articles by feed if requested
        if config.group_by_feed:
            articles_by_feed = {}
            for article in rss_articles:
                feed_name = article.source or "Unknown"
                if feed_name not in articles_by_feed:
                    articles_by_feed[feed_name] = []
                articles_by_feed[feed_name].append(article)
            
            # Limit articles per feed
            for feed_name in articles_by_feed:
                articles_by_feed[feed_name] = articles_by_feed[feed_name][:config.max_articles_per_feed]
        else:
            articles_by_feed = {"All Feeds": rss_articles[:config.max_total_articles]}
        
        # Sort by priority if requested
        if config.sort_by_priority:
            priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
            for feed_name in articles_by_feed:
                articles_by_feed[feed_name].sort(
                    key=lambda a: (priority_order.get(a.priority.value, 4), a.created_at),
                    reverse=True
                )
        
        # Generate statistics
        stats = {
            "total_articles": len(rss_articles),
            "total_feeds": len(feeds),
            "active_feeds": len([f for f in feeds if f.is_active]),
            "total_reading_time": sum(a.reading_time or 0 for a in rss_articles),
            "total_words": sum(a.word_count or 0 for a in rss_articles),
            "date_range": f"Last {config.days_back} days",
            "generated_at": datetime.utcnow()
        }
        
        return {
            "articles_by_feed": articles_by_feed,
            "feeds": feeds,
            "stats": stats,
            "config": config
        }
    
    async def get_feed_stats(self, feed_id: int = None) -> Dict[str, Any]:
        """Get statistics for a specific feed or all feeds."""
        if feed_id:
            feed = await self.db.get_feed(feed_id)
            if not feed:
                return {}
            
            articles = await self.db.get_articles_by_source(feed.name)
            return {
                "feed": feed,
                "article_count": len(articles),
                "last_fetched": feed.last_fetched,
                "is_active": feed.is_active,
                "recent_articles": articles[:5]
            }
        else:
            feeds = await self.db.get_feeds()
            stats = []
            
            for feed in feeds:
                articles = await self.db.get_articles_by_source(feed.name)
                stats.append({
                    "feed": feed,
                    "article_count": len(articles),
                    "last_fetched": feed.last_fetched,
                    "is_active": feed.is_active
                })
            
            return {
                "feeds": stats,
                "total_feeds": len(feeds),
                "active_feeds": len([f for f in feeds if f.is_active]),
                "total_articles": sum(s["article_count"] for s in stats)
            }
    
    async def refresh_feed(self, feed_id: int, max_articles: int = 10) -> Dict[str, Any]:
        """Manually refresh a specific RSS feed."""
        feed = await self.db.get_feed(feed_id)
        if not feed:
            return {"error": "Feed not found"}
        
        if not feed.is_active:
            return {"error": "Feed is not active"}
        
        try:
            articles = await self.fetch_feed_articles(feed, max_articles)
            return {
                "success": True,
                "feed": feed,
                "new_articles": len(articles),
                "articles": articles
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def search_feeds(self, query: str) -> List[Feed]:
        """Search feeds by name, description, or tags."""
        feeds = await self.db.get_feeds()
        query_lower = query.lower()
        
        matching_feeds = []
        for feed in feeds:
            if (query_lower in feed.name.lower() or 
                (feed.description and query_lower in feed.description.lower()) or
                any(query_lower in tag.lower() for tag in feed.tags)):
                matching_feeds.append(feed)
        
        return matching_feeds


class RSSBriefingFormatter:
    """Formats RSS briefing data for different output formats."""
    
    @staticmethod
    def format_discord_embed(briefing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format briefing data for Discord embed."""
        stats = briefing_data["stats"]
        articles_by_feed = briefing_data["articles_by_feed"]
        
        embed_data = {
            "title": f"📡 RSS Briefing - {stats['date_range']}",
            "description": f"*Generated on {stats['generated_at'].strftime('%B %d, %Y at %I:%M %p')}*",
            "color": 0x00ff00,  # Green
            "fields": []
        }
        
        # Add summary stats
        embed_data["fields"].append({
            "name": "📊 Summary",
            "value": (f"• **Articles:** {stats['total_articles']}\n"
                     f"• **Active Feeds:** {stats['active_feeds']}/{stats['total_feeds']}\n"
                     f"• **Reading Time:** {stats['total_reading_time']} min\n"
                     f"• **Words:** {stats['total_words']:,}"),
            "inline": False
        })
        
        # Add articles by feed (limit to avoid Discord embed limits)
        feed_count = 0
        for feed_name, articles in articles_by_feed.items():
            if feed_count >= 3:  # Limit to 3 feeds to avoid embed limits
                break
            
            if articles:
                articles_text = ""
                for i, article in enumerate(articles[:3], 1):  # Limit to 3 articles per feed
                    priority_emoji = {
                        "urgent": "🔴",
                        "high": "🟠", 
                        "medium": "🟡",
                        "low": "🟢"
                    }.get(article.priority.value, "⚪")
                    
                    articles_text += f"{priority_emoji} **{article.title[:50]}{'...' if len(article.title) > 50 else ''}**\n"
                    if article.author:
                        articles_text += f"   *By {article.author}*\n"
                    articles_text += f"   📖 {article.reading_time or 0} min • 📅 {article.created_at.strftime('%b %d')}\n\n"
                
                if len(articles) > 3:
                    articles_text += f"*... and {len(articles) - 3} more articles*\n"
                
                embed_data["fields"].append({
                    "name": f"📰 {feed_name} ({len(articles)} articles)",
                    "value": articles_text,
                    "inline": False
                })
                
                feed_count += 1
        
        if not any(articles_by_feed.values()):
            embed_data["fields"].append({
                "name": "📰 Articles",
                "value": "*No recent articles found.*",
                "inline": False
            })
        
        return embed_data
    
    @staticmethod
    def format_text_summary(briefing_data: Dict[str, Any]) -> str:
        """Format briefing data as plain text summary."""
        stats = briefing_data["stats"]
        articles_by_feed = briefing_data["articles_by_feed"]
        
        text = f"📡 RSS Briefing - {stats['date_range']}\n"
        text += f"Generated on {stats['generated_at'].strftime('%B %d, %Y at %I:%M %p')}\n\n"
        
        text += f"📊 Summary:\n"
        text += f"• Articles: {stats['total_articles']}\n"
        text += f"• Active Feeds: {stats['active_feeds']}/{stats['total_feeds']}\n"
        text += f"• Reading Time: {stats['total_reading_time']} min\n"
        text += f"• Words: {stats['total_words']:,}\n\n"
        
        for feed_name, articles in articles_by_feed.items():
            if articles:
                text += f"📰 {feed_name} ({len(articles)} articles):\n"
                for article in articles[:5]:  # Limit to 5 articles per feed
                    priority_emoji = {
                        "urgent": "🔴",
                        "high": "🟠", 
                        "medium": "🟡",
                        "low": "🟢"
                    }.get(article.priority.value, "⚪")
                    
                    text += f"  {priority_emoji} {article.title}\n"
                    if article.author:
                        text += f"     By {article.author}\n"
                    text += f"     📖 {article.reading_time or 0} min • 📅 {article.created_at.strftime('%b %d')}\n"
                    text += f"     🔗 {article.url}\n\n"
                
                if len(articles) > 5:
                    text += f"     ... and {len(articles) - 5} more articles\n\n"
        
        return text