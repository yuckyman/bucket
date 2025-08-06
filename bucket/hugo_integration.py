"""Hugo integration for converting RSS articles to Hugo content."""

import asyncio
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import re
import json

from .models import Article, Feed
from .database import Database
from .config import config


class HugoContentGenerator:
    """Generates Hugo content from RSS articles."""
    
    def __init__(self, hugo_site_path: Optional[str] = None):
        # Use provided path or auto-detect
        if hugo_site_path:
            self.hugo_site_path = Path(hugo_site_path).resolve()
        else:
            detected_path = config.get_hugo_site_path()
            if not detected_path:
                raise ValueError(
                    "Hugo site path not found. Please set BUCKET_HUGO_SITE_PATH environment variable "
                    "or ensure you're running from a directory with a Hugo site."
                )
            self.hugo_site_path = Path(detected_path).resolve()
        
        # Validate the Hugo site
        if not config.validate_hugo_site(str(self.hugo_site_path)):
            raise ValueError(f"Invalid Hugo site at: {self.hugo_site_path}")
        
        self.read_later_dir = self.hugo_site_path / "content" / "read_later"
        self.read_later_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Hugo site path: {self.hugo_site_path}")
        print(f"📁 Read later directory: {self.read_later_dir}")
        
    def _slugify(self, title: str) -> str:
        """Convert title to URL-friendly slug."""
        # Remove special characters and convert to lowercase
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        # Replace spaces with hyphens
        slug = re.sub(r'[-\s]+', '-', slug)
        # Remove leading/trailing hyphens
        return slug.strip('-')
    
    def _generate_read_later_front_matter(self, date: datetime, articles: List[Article], feeds: List[Feed]) -> str:
        """Generate Hugo front matter for a read_later daily report."""
        # Create tags from feed names and article tags
        all_tags = set()
        for article in articles:
            all_tags.update(article.tags or [])
        for feed in feeds:
            all_tags.update(feed.tags or [])
        
        # Add feed names as tags
        feed_names = [feed.name.lower().replace(' ', '-') for feed in feeds]
        all_tags.update(feed_names)
        
        # Add RSS and read-later tags
        all_tags.update(['rss', 'read-later', 'daily-report'])
        
        front_matter = f"""---
title: "Read Later - {date.strftime('%B %d, %Y')}"
date: {date.strftime('%Y-%m-%dT%H:%M:%S-00:00')}
draft: false
tags: {list(all_tags)}
categories: ["read-later", "rss"]
description: "Daily RSS feed digest with {len(articles)} articles from {len(feeds)} feeds"
toc: true
---

"""
        return front_matter
    
    def _clean_content_for_hugo(self, content: str) -> str:
        """Clean content for Hugo markdown."""
        if not content:
            return ""
        
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Clean up extra whitespace
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        # Remove common web artifacts
        content = re.sub(r'Share this|Tweet this|Follow us|Subscribe|Newsletter', '', content, flags=re.IGNORECASE)
        
        return content.strip()
    
    def _truncate_content(self, content: str, max_words: int = 200) -> str:
        """Truncate content to max_words."""
        words = content.split()
        if len(words) <= max_words:
            return content
        
        truncated = ' '.join(words[:max_words])
        return truncated + '...'
    
    async def create_daily_read_later_report(self, articles: List[Article], feeds: List[Feed], date: datetime = None) -> Optional[str]:
        """Create a daily read_later report from RSS articles."""
        try:
            if date is None:
                date = datetime.now()
            
            # Create filename for the day
            filename = f"{date.strftime('%Y-%m-%d')}.md"
            file_path = self.read_later_dir / filename
            
            # Generate front matter
            front_matter = self._generate_read_later_front_matter(date, articles, feeds)
            
            # Generate content
            content = f"# Read Later - {date.strftime('%B %d, %Y')}\n\n"
            content += f"*Generated on {date.strftime('%B %d, %Y at %I:%M %p')}*\n\n"
            content += f"**Summary:** {len(articles)} articles from {len(feeds)} feeds\n\n"
            
            # Group articles by feed
            articles_by_feed = {}
            for article in articles:
                feed_name = article.metadata.get('feed_title', 'Unknown Feed') if article.metadata else 'Unknown Feed'
                if feed_name not in articles_by_feed:
                    articles_by_feed[feed_name] = []
                articles_by_feed[feed_name].append(article)
            
            # Generate content for each feed
            for feed_name, feed_articles in articles_by_feed.items():
                content += f"## 📰 {feed_name}\n\n"
                
                for i, article in enumerate(feed_articles, 1):
                    content += f"### {i}. {article.title}\n\n"
                    
                    if article.author:
                        content += f"**Author:** {article.author}\n"
                    
                    if article.published_date:
                        content += f"**Published:** {article.published_date.strftime('%B %d, %Y')}\n"
                    
                    content += f"**Reading time:** {article.reading_time or 0} minutes\n"
                    content += f"**Word count:** {article.word_count or 0} words\n"
                    
                    if article.tags:
                        content += f"**Tags:** {', '.join(article.tags)}\n"
                    
                    content += f"**Source:** [{article.url}]({article.url})\n\n"
                    
                    # Add truncated content
                    cleaned_content = self._clean_content_for_hugo(article.cleaned_content or article.content)
                    truncated_content = self._truncate_content(cleaned_content, 150)
                    content += f"{truncated_content}\n\n"
                    
                    content += "---\n\n"
            
            # Add footer
            content += f"\n\n---\n\n*Generated by RSS Feed Processor on {date.strftime('%B %d, %Y at %I:%M %p')}*\n"
            
            # Write file (this will overwrite if it exists, which is what we want for daily deduplication)
            print(f"📝 Writing report to: {file_path}")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(front_matter + content)
            
            print(f"✅ Created daily read_later report: {file_path}")
            return str(file_path)
            
        except Exception as e:
            print(f"Error creating daily read_later report: {e}")
            return None
    
    async def process_feeds_for_read_later(self, db: Database, max_articles_per_feed: int = 5) -> Dict[str, Any]:
        """Process all feeds and create a daily read_later report."""
        try:
            # Get all feeds from database
            feeds = await db.get_feeds()
            
            if not feeds:
                return {
                    "success": False,
                    "message": "No feeds found",
                    "articles_processed": 0,
                    "feeds_processed": 0,
                    "report_created": False
                }
            
            all_articles = []
            feeds_processed = 0
            
            for feed in feeds:
                try:
                    print(f"📡 Processing feed: {feed.name} -> {feed.url}")
                    
                    # Fetch articles from feed
                    from .fetcher import RSSFetcher, ContentFetcher
                    
                    fetcher = ContentFetcher()
                    rss_fetcher = RSSFetcher(fetcher)
                    
                    articles = await rss_fetcher.fetch_feed(str(feed.url))
                    print(f"  📄 Found {len(articles)} articles from {feed.name}")
                    
                    # Limit articles per feed
                    articles = articles[:max_articles_per_feed]
                    print(f"  📄 Using {len(articles)} articles (limited to {max_articles_per_feed})")
                    
                    # Add feed metadata to articles
                    for article in articles:
                        if not article.metadata:
                            article.metadata = {}
                        article.metadata['feed_title'] = feed.name
                        article.metadata['feed_url'] = str(feed.url)
                    
                    all_articles.extend(articles)
                    feeds_processed += 1
                    print(f"  ✅ Successfully processed {feed.name}")
                    
                except Exception as e:
                    print(f"❌ Error processing feed {feed.name}: {e}")
                    continue
            
            if not all_articles:
                return {
                    "success": False,
                    "message": "No articles found from any feeds",
                    "articles_processed": 0,
                    "feeds_processed": feeds_processed,
                    "report_created": False
                }
            
            # Create daily report
            report_path = await self.create_daily_read_later_report(all_articles, feeds)
            
            return {
                "success": True,
                "message": f"Processed {feeds_processed} feeds, created report with {len(all_articles)} articles",
                "articles_processed": len(all_articles),
                "feeds_processed": feeds_processed,
                "report_created": bool(report_path),
                "report_path": report_path
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error processing feeds: {e}",
                "articles_processed": 0,
                "feeds_processed": 0,
                "report_created": False
            }
    
    async def build_hugo_site(self) -> Dict[str, Any]:
        """Build the Hugo site."""
        try:
            # Change to Hugo site directory
            original_cwd = os.getcwd()
            os.chdir(self.hugo_site_path)
            
            # Run Hugo build
            result = subprocess.run(
                ["hugo", "--minify"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            os.chdir(original_cwd)
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "Hugo build completed successfully",
                    "output": result.stdout
                }
            else:
                return {
                    "success": False,
                    "message": f"Hugo build failed: {result.stderr}",
                    "output": result.stderr
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "Hugo build timed out",
                "output": ""
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error building Hugo site: {e}",
                "output": ""
            } 