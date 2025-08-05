"""Web content fetcher for bucket system."""

import asyncio
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
# Optional imports
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    BeautifulSoup = None

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    feedparser = None
from .models import Article, ArticleStatus


class ContentFetcher:
    """Fetches and processes web content."""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        if not HTTPX_AVAILABLE:
            raise RuntimeError("httpx not available")
            
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; BucketBot/1.0; +https://github.com/yourusername/bucket)"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    async def fetch_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch content from a URL with retry logic."""
        if not HTTPX_AVAILABLE:
            return None
            
        for attempt in range(self.max_retries):
            try:
                response = await self.client.get(url)
                response.raise_for_status()
                
                content_type = response.headers.get("content-type", "").lower()
                
                if "application/rss+xml" in content_type or "application/atom+xml" in content_type:
                    return await self._parse_rss_feed(response.text, url)
                elif "text/html" in content_type:
                    return await self._parse_html_content(response.text, url)
                else:
                    return {
                        "url": url,
                        "title": f"Unknown content type: {content_type}",
                        "content": response.text[:1000] + "..." if len(response.text) > 1000 else response.text,
                        "cleaned_content": None,
                        "author": None,
                        "published_date": None,
                        "word_count": len(response.text.split()),
                        "reading_time": max(1, len(response.text.split()) // 200),
                        "metadata": {"content_type": content_type}
                    }
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        
        return None
    
    async def _parse_html_content(self, html: str, url: str) -> Dict[str, Any]:
        """Parse HTML content and extract relevant information."""
        if not BS4_AVAILABLE:
            return {
                "url": url,
                "title": "HTML Content",
                "content": html[:1000],
                "cleaned_content": html[:500],
                "author": None,
                "published_date": None,
                "word_count": len(html.split()),
                "reading_time": max(1, len(html.split()) // 200),
                "metadata": {"error": "BeautifulSoup not available"}
            }
            
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Extract title
        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text().strip()
        
        # Extract meta description
        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            description = meta_desc.get("content", "").strip()
        
        # Extract author
        author = ""
        author_meta = soup.find("meta", attrs={"name": "author"})
        if author_meta:
            author = author_meta.get("content", "").strip()
        
        # Extract published date
        published_date = None
        date_meta = soup.find("meta", attrs={"property": "article:published_time"})
        if date_meta:
            try:
                published_date = datetime.fromisoformat(date_meta.get("content").replace("Z", "+00:00"))
            except:
                pass
        
        # Extract main content
        content = ""
        main_content = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile(r"content|post|article"))
        if main_content:
            content = main_content.get_text(separator="\n", strip=True)
        else:
            # Fallback to body content
            body = soup.find("body")
            if body:
                content = body.get_text(separator="\n", strip=True)
        
        # Clean content
        cleaned_content = self._clean_content(content)
        
        # Calculate reading time (average 200 words per minute)
        word_count = len(cleaned_content.split())
        reading_time = max(1, word_count // 200)
        
        return {
            "url": url,
            "title": title,
            "content": content,
            "cleaned_content": cleaned_content,
            "author": author,
            "published_date": published_date,
            "word_count": word_count,
            "reading_time": reading_time,
            "metadata": {
                "description": description,
                "domain": urlparse(url).netloc
            }
        }
    
    async def _parse_rss_feed(self, feed_content: str, url: str) -> Dict[str, Any]:
        """Parse RSS feed content."""
        if not FEEDPARSER_AVAILABLE:
            return {
                "url": url,
                "title": "RSS Feed",
                "content": feed_content[:1000],
                "cleaned_content": feed_content[:500],
                "author": None,
                "published_date": None,
                "word_count": len(feed_content.split()),
                "reading_time": max(1, len(feed_content.split()) // 200),
                "metadata": {"error": "feedparser not available"}
            }
            
        feed = feedparser.parse(feed_content)
        
        if not feed.entries:
            return None
        
        # Get the most recent entry
        entry = feed.entries[0]
        
        # Extract published date
        published_date = None
        if hasattr(entry, "published_parsed"):
            published_date = datetime(*entry.published_parsed[:6])
        elif hasattr(entry, "updated_parsed"):
            published_date = datetime(*entry.updated_parsed[:6])
        
        # Extract author
        author = ""
        if hasattr(entry, "author"):
            author = entry.author
        
        # Extract content
        content = ""
        if hasattr(entry, "content"):
            content = entry.content[0].value
        elif hasattr(entry, "summary"):
            content = entry.summary
        
        # Clean content
        cleaned_content = self._clean_content(content)
        
        # Calculate reading time
        word_count = len(cleaned_content.split())
        reading_time = max(1, word_count // 200)
        
        return {
            "url": entry.link if hasattr(entry, "link") else url,
            "title": entry.title if hasattr(entry, "title") else "RSS Entry",
            "content": content,
            "cleaned_content": cleaned_content,
            "author": author,
            "published_date": published_date,
            "word_count": word_count,
            "reading_time": reading_time,
            "metadata": {
                "feed_title": feed.feed.title if hasattr(feed.feed, "title") else "",
                "feed_description": feed.feed.description if hasattr(feed.feed, "description") else "",
                "domain": urlparse(url).netloc
            }
        }
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content."""
        if not content:
            return ""
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove common web artifacts
        content = re.sub(r'Share this|Tweet this|Follow us|Subscribe|Newsletter', '', content, flags=re.IGNORECASE)
        
        # Remove URLs
        content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', content)
        
        # Remove email addresses
        content = re.sub(r'\S+@\S+', '', content)
        
        # Remove common social media handles
        content = re.sub(r'@\w+', '', content)
        
        # Clean up punctuation
        content = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)]', '', content)
        
        return content.strip()
    
    async def fetch_article(self, url: str) -> Optional[Article]:
        """Fetch and create an Article object from a URL."""
        async with self:
            result = await self.fetch_url(url)
            if not result:
                return None
            
            return Article(
                url=result["url"],
                title=result["title"],
                content=result["content"],
                cleaned_content=result["cleaned_content"],
                author=result["author"],
                published_date=result["published_date"],
                fetched_date=datetime.utcnow(),
                status=ArticleStatus.FETCHED,
                word_count=result["word_count"],
                reading_time=result["reading_time"],
                metadata=result["metadata"]
            )


class RSSFetcher:
    """Fetches content from RSS feeds."""
    
    def __init__(self, fetcher: ContentFetcher):
        self.fetcher = fetcher
    
    async def fetch_feed(self, feed_url: str) -> List[Article]:
        """Fetch all articles from an RSS feed."""
        async with self.fetcher:
            result = await self.fetcher.fetch_url(feed_url)
            if not result:
                return []
            
            # For RSS feeds, we need to fetch each individual article
            articles = []
            feed = feedparser.parse(result["content"])
            
            for entry in feed.entries[:10]:  # Limit to 10 most recent
                if hasattr(entry, "link"):
                    article = await self.fetcher.fetch_article(entry.link)
                    if article:
                        articles.append(article)
            
            return articles