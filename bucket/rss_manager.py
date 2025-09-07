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
        self.content_fetcher = ContentFetcher()
        self.rss_fetcher = RSSFetcher(self.content_fetcher)
    
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
        feed_id = await self.db.save_feed(feed)
        if feed_id:
            feed.id = feed_id
        return feed
    
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
            articles = await self.rss_fetcher.fetch_feed(str(feed.url))
            
            # Process and save articles to database
            saved_articles = []
            for article in articles[:max_articles]:  # Limit to max_articles
                try:
                    # Enhanced duplicate checking
                    if await self._is_duplicate_article(article, feed):
                        print(f"🔄 Skipping duplicate article: {article.title[:50]}...")
                        continue
                    
                    # Update article with feed information
                    article.source = feed.name
                    article.tags = feed.tags.copy() if feed.tags else []
                    article.status = ArticleStatus.FETCHED
                    article.priority = ArticlePriority.MEDIUM
                    
                    article_id = await self.db.save_article(article)
                    article.id = article_id  # Update the article with its new ID
                    saved_articles.append(article)
                    
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
    
    async def _is_duplicate_article(self, article: Article, feed: Feed) -> bool:
        """Check if an article is a duplicate using multiple criteria."""
        try:
            # 1. Check by exact URL match
            existing_by_url = await self.db.get_article_by_url(str(article.url))
            if existing_by_url:
                return True
            
            # 2. Check by title similarity (for cases where URLs might vary)
            if article.title:
                # Get recent articles from the same source
                recent_articles = await self.db.get_articles_by_source(feed.name)
                
                for existing_article in recent_articles:
                    if existing_article.title and self._titles_similar(article.title, existing_article.title):
                        # Also check if published dates are close (within 24 hours)
                        if (article.published_date and existing_article.published_date and
                            abs((article.published_date - existing_article.published_date).total_seconds()) < 86400):
                            return True
            
            # 3. Check by content hash if available
            if hasattr(article, 'content') and article.content:
                content_hash = self._get_content_hash(article.content)
                if content_hash:
                    # Check if any recent article has the same content hash
                    recent_articles = await self.db.get_articles_by_source(feed.name)
                    for existing_article in recent_articles:
                        if (hasattr(existing_article, 'content') and existing_article.content and
                            self._get_content_hash(existing_article.content) == content_hash):
                            return True
            
            return False
            
        except Exception as e:
            print(f"❌ Error checking for duplicates: {e}")
            # If there's an error, err on the side of caution and don't save
            return True
    
    def _titles_similar(self, title1: str, title2: str, threshold: float = 0.8) -> bool:
        """Check if two titles are similar using simple string comparison."""
        if not title1 or not title2:
            return False
        
        # Normalize titles (lowercase, remove extra spaces)
        norm1 = ' '.join(title1.lower().split())
        norm2 = ' '.join(title2.lower().split())
        
        # If titles are identical after normalization
        if norm1 == norm2:
            return True
        
        # Check if one title contains the other (for truncated titles)
        if norm1 in norm2 or norm2 in norm1:
            return True
        
        # Simple similarity check using common words
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        if len(words1) == 0 or len(words2) == 0:
            return False
        
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        similarity = intersection / union if union > 0 else 0
        
        return similarity >= threshold
    
    def _get_content_hash(self, content: str) -> Optional[str]:
        """Generate a simple hash of the content for duplicate detection."""
        if not content:
            return None
        
        try:
            import hashlib
            # Take first 1000 characters to avoid very long content
            content_sample = content[:1000]
            return hashlib.md5(content_sample.encode('utf-8')).hexdigest()
        except Exception:
            return None
    
    async def cleanup_duplicates(self, days_back: int = 30) -> Dict[str, Any]:
        """Clean up duplicate articles from the database."""
        try:
            print(f"🧹 Starting duplicate cleanup for articles from the last {days_back} days...")
            
            # Get recent articles
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            recent_articles = await self.db.get_articles_since(cutoff_date, limit=1000)
            
            if not recent_articles:
                return {
                    "success": True,
                    "total_articles": 0,
                    "duplicates_found": 0,
                    "duplicates_removed": 0,
                    "message": "No recent articles found"
                }
            
            print(f"📊 Analyzing {len(recent_articles)} recent articles for duplicates...")
            
            # Group articles by source for more efficient duplicate detection
            articles_by_source = {}
            for article in recent_articles:
                source = article.source or "Unknown"
                if source not in articles_by_source:
                    articles_by_source[source] = []
                articles_by_source[source].append(article)
            
            duplicates_found = 0
            duplicates_removed = 0
            
            # Process each source separately
            for source, articles in articles_by_source.items():
                print(f"🔍 Checking {len(articles)} articles from {source}...")
                
                # Sort by creation date (newest first)
                articles.sort(key=lambda x: x.created_at, reverse=True)
                
                # Find duplicates within this source
                seen_urls = set()
                seen_titles = {}
                seen_content_hashes = {}
                
                for article in articles:
                    is_duplicate = False
                    duplicate_reason = ""
                    
                    # Check URL duplicates
                    if str(article.url) in seen_urls:
                        is_duplicate = True
                        duplicate_reason = "URL"
                    else:
                        seen_urls.add(str(article.url))
                    
                    # Check title duplicates
                    if not is_duplicate and article.title:
                        title_key = ' '.join(article.title.lower().split())
                        for seen_title, seen_article in seen_titles.items():
                            if self._titles_similar(title_key, seen_title):
                                # Check if published dates are close
                                if (article.published_date and seen_article.published_date and
                                    abs((article.published_date - seen_article.published_date).total_seconds()) < 86400):
                                    is_duplicate = True
                                    duplicate_reason = "Title similarity"
                                    break
                        
                        if not is_duplicate:
                            seen_titles[title_key] = article
                    
                    # Check content hash duplicates
                    if not is_duplicate and hasattr(article, 'content') and article.content:
                        content_hash = self._get_content_hash(article.content)
                        if content_hash and content_hash in seen_content_hashes:
                            is_duplicate = True
                            duplicate_reason = "Content hash"
                        elif content_hash:
                            seen_content_hashes[content_hash] = article
                    
                    if is_duplicate:
                        duplicates_found += 1
                        print(f"🗑️  Removing duplicate article: {article.title[:50]}... (Reason: {duplicate_reason})")
                        
                        # Remove from database
                        if await self._remove_article_from_db(article.id):
                            duplicates_removed += 1
            
            result = {
                "success": True,
                "total_articles": len(recent_articles),
                "duplicates_found": duplicates_found,
                "duplicates_removed": duplicates_removed,
                "sources_checked": len(articles_by_source),
                "message": f"Cleanup completed: {duplicates_removed}/{duplicates_found} duplicates removed"
            }
            
            print(f"✅ Duplicate cleanup completed: {duplicates_removed}/{duplicates_found} duplicates removed")
            return result
            
        except Exception as e:
            print(f"❌ Error during duplicate cleanup: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Duplicate cleanup failed"
            }
    
    async def _remove_article_from_db(self, article_id: int) -> bool:
        """Remove an article from the database by ID."""
        try:
            if not SQLALCHEMY_AVAILABLE:
                print("⚠️  SQLAlchemy not available, cannot remove article")
                return False
            
            async with self.db.AsyncSessionLocal() as session:
                from sqlalchemy import select, delete
                from .database import ArticleTable
                
                # First check if article exists
                stmt = select(ArticleTable).where(ArticleTable.id == article_id)
                result = await session.execute(stmt)
                article = result.scalar_one_or_none()
                
                if not article:
                    return False
                
                # Delete the article
                delete_stmt = delete(ArticleTable).where(ArticleTable.id == article_id)
                await session.execute(delete_stmt)
                await session.commit()
                
                return True
                
        except Exception as e:
            print(f"❌ Error removing article {article_id}: {e}")
            return False


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