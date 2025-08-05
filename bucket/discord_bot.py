"""Discord bot for bucket system."""

import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Optional
# Optional discord imports
try:
    import discord
    from discord.ext import commands
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    discord = None
    commands = None
from .models import Article, ArticleStatus, ArticlePriority
from .fetcher import ContentFetcher


if DISCORD_AVAILABLE:
    class BucketBot(commands.Bot):
        """Discord bot for bucket system."""
        
        def __init__(self, command_prefix: str = "!", intents: Optional[discord.Intents] = None, 
                     bucket_core=None, dedicated_channel_id: Optional[int] = None):
            if intents is None:
                intents = discord.Intents.default()
                intents.message_content = True
            
            super().__init__(command_prefix=command_prefix, intents=intents)
            self.bucket_core = bucket_core
            self.dedicated_channel_id = dedicated_channel_id
            self.fetcher = ContentFetcher()
            self.article_queue = asyncio.Queue()
            
        async def setup_hook(self):
            """Setup bot commands."""
            await self.add_commands()
        
        async def add_commands(self):
            """Add bot commands."""
            
            @self.command(name="add")
            async def add_url(ctx, url: str):
                """Add a URL to the bucket."""
                if not self._is_valid_url(url):
                    await ctx.send("❌ Invalid URL provided.")
                    return
                
                # Create embed for feedback
                embed = discord.Embed(
                    title="🪣 Adding to Bucket",
                    description=f"Processing: {url}",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Status", value="⏳ Fetching content...", inline=False)
                
                message = await ctx.send(embed=embed)
                
                try:
                    # Fetch the article
                    async with self.fetcher:
                        article = await self.fetcher.fetch_article(url)
                    
                    if not article:
                        embed.description = f"❌ Failed to fetch: {url}"
                        embed.color = discord.Color.red()
                        embed.set_field_at(0, name="Status", value="❌ Failed", inline=False)
                        await message.edit(embed=embed)
                        return
                    
                    # Add to bucket core if available
                    if self.bucket_core:
                        await self.bucket_core.add_url(str(article.url))
                        embed.description = f"✅ Added to bucket: {article.title}"
                        embed.color = discord.Color.green()
                        embed.set_field_at(0, name="Status", value="✅ Added to bucket", inline=False)
                    else:
                        # Add to queue for processing
                        await self.article_queue.put(article)
                        embed.description = f"✅ Added to bucket: {article.title}"
                        embed.color = discord.Color.green()
                        embed.set_field_at(0, name="Status", value="✅ Queued for processing", inline=False)
                    
                    embed.add_field(name="Title", value=article.title[:100], inline=False)
                    embed.add_field(name="Author", value=article.author or "Unknown", inline=True)
                    embed.add_field(name="Reading Time", value=f"{article.reading_time} min", inline=True)
                    
                    await message.edit(embed=embed)
                    
                except Exception as e:
                    embed.description = f"❌ Error processing: {url}"
                    embed.color = discord.Color.red()
                    embed.set_field_at(0, name="Status", value=f"❌ Error: {str(e)}", inline=False)
                    await message.edit(embed=embed)
            
            @self.command(name="compile")
            async def compile_briefing(ctx):
                """Generate today's briefing."""
                embed = discord.Embed(
                    title="📋 Generating Briefing",
                    description="Creating today's briefing...",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Status", value="⏳ Processing...", inline=False)
                
                message = await ctx.send(embed=embed)
                
                try:
                    if not self.bucket_core:
                        embed.description = "❌ Bucket core not available"
                        embed.color = discord.Color.red()
                        embed.set_field_at(0, name="Status", value="❌ Not configured", inline=False)
                        await message.edit(embed=embed)
                        return
                    
                    # Generate briefing for today
                    briefing_path = await self.bucket_core.generate_briefing(
                        title="Daily Briefing",
                        days_back=1,
                        tags=None,
                        priority=None
                    )
                    
                    if briefing_path:
                        embed.description = "✅ Briefing generated successfully!"
                        embed.color = discord.Color.green()
                        embed.set_field_at(0, name="Status", value="✅ Complete", inline=False)
                        embed.add_field(name="File", value=f"`{briefing_path}`", inline=False)
                        
                        # Try to send the file
                        try:
                            await ctx.send(file=discord.File(briefing_path))
                        except Exception as e:
                            embed.add_field(name="Note", value=f"File saved to: {briefing_path}", inline=False)
                    else:
                        embed.description = "❌ No articles found for briefing"
                        embed.color = discord.Color.yellow()
                        embed.set_field_at(0, name="Status", value="⚠️ No content", inline=False)
                    
                    await message.edit(embed=embed)
                    
                except Exception as e:
                    embed.description = f"❌ Error generating briefing"
                    embed.color = discord.Color.red()
                    embed.set_field_at(0, name="Status", value=f"❌ Error: {str(e)}", inline=False)
                    await message.edit(embed=embed)
            
            @self.command(name="rss")
            async def show_rss(ctx):
                """Show RSS entries since last compile."""
                embed = discord.Embed(
                    title="📰 RSS Entries",
                    description="Fetching recent RSS entries...",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                
                message = await ctx.send(embed=embed)
                
                try:
                    if not self.bucket_core:
                        embed.description = "❌ Bucket core not available"
                        embed.color = discord.Color.red()
                        await message.edit(embed=embed)
                        return
                    
                    # Get articles from today (since last compile)
                    today = datetime.utcnow().date()
                    articles = await self.bucket_core.get_articles_since(today)
                    
                    if not articles:
                        embed.description = "📭 No new RSS entries found today"
                        embed.color = discord.Color.yellow()
                        await message.edit(embed=embed)
                        return
                    
                    embed.description = f"📰 Found {len(articles)} new entries"
                    embed.color = discord.Color.green()
                    
                    # Show first 5 articles
                    for i, article in enumerate(articles[:5]):
                        embed.add_field(
                            name=f"📄 {article.title[:50]}...",
                            value=f"**Author:** {article.author or 'Unknown'}\n"
                                  f"**Reading Time:** {article.reading_time} min\n"
                                  f"**URL:** {article.url}",
                            inline=False
                        )
                    
                    if len(articles) > 5:
                        embed.add_field(
                            name="More entries",
                            value=f"And {len(articles) - 5} more entries...",
                            inline=False
                        )
                    
                    await message.edit(embed=embed)
                    
                except Exception as e:
                    embed.description = f"❌ Error fetching RSS entries"
                    embed.color = discord.Color.red()
                    embed.add_field(name="Error", value=str(e), inline=False)
                    await message.edit(embed=embed)
            
            @self.command(name="status")
            async def status(ctx):
                """Show bucket status."""
                queue_size = self.article_queue.qsize()
                
                embed = discord.Embed(
                    title="🪣 Bucket Status",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Queue Size", value=str(queue_size), inline=True)
                embed.add_field(name="Status", value="🟢 Active", inline=True)
                
                if self.bucket_core:
                    embed.add_field(name="Core", value="✅ Connected", inline=True)
                else:
                    embed.add_field(name="Core", value="❌ Not connected", inline=True)
                
                await ctx.send(embed=embed)
            
            @self.command(name="help")
            async def help_command(ctx):
                """Show help information."""
                embed = discord.Embed(
                    title="🪣 Bucket Bot Help",
                    description="Commands for managing your reading bucket",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="!add <url>",
                    value="Add a URL to your reading bucket",
                    inline=False
                )
                embed.add_field(
                    name="!compile",
                    value="Generate today's briefing",
                    inline=False
                )
                embed.add_field(
                    name="!rss",
                    value="Show RSS entries since last compile",
                    inline=False
                )
                embed.add_field(
                    name="!status",
                    value="Show current bucket status",
                    inline=False
                )
                embed.add_field(
                    name="!help",
                    value="Show this help message",
                    inline=False
                )
                
                await ctx.send(embed=embed)
            
            @self.event
            async def on_message(message):
                """Handle messages with URLs."""
                if message.author.bot:
                    return
                
                # Check if this is the dedicated channel
                if self.dedicated_channel_id and message.channel.id == self.dedicated_channel_id:
                    # Auto-process URLs in dedicated channel
                    urls = self._extract_urls(message.content)
                    
                    if urls:
                        embed = discord.Embed(
                            title="🔗 Auto-Processing URLs",
                            description="Processing URLs from dedicated channel...",
                            color=discord.Color.green(),
                            timestamp=datetime.utcnow()
                        )
                        
                        status_message = await message.channel.send(embed=embed)
                        
                        processed_count = 0
                        for url in urls:
                            try:
                                if self.bucket_core:
                                    await self.bucket_core.add_url(url)
                                    processed_count += 1
                                else:
                                    # Add to queue
                                    async with self.fetcher:
                                        article = await self.fetcher.fetch_article(url)
                                    if article:
                                        await self.article_queue.put(article)
                                        processed_count += 1
                            except Exception as e:
                                print(f"Error processing {url}: {e}")
                        
                        embed.description = f"✅ Processed {processed_count}/{len(urls)} URLs"
                        embed.add_field(name="Processed", value=str(processed_count), inline=True)
                        embed.add_field(name="Total", value=str(len(urls)), inline=True)
                        
                        await status_message.edit(embed=embed)
                        
                        # Add reaction to original message
                        await message.add_reaction("✅")
                    
                    # Also check for RSS feed URLs
                    rss_urls = self._extract_rss_urls(message.content)
                    if rss_urls:
                        embed = discord.Embed(
                            title="📰 RSS Feed Detected",
                            description="Adding RSS feed to bucket...",
                            color=discord.Color.blue(),
                            timestamp=datetime.utcnow()
                        )
                        
                        status_message = await message.channel.send(embed=embed)
                        
                        for rss_url in rss_urls:
                            try:
                                if self.bucket_core:
                                    # Extract feed name from URL
                                    feed_name = rss_url.split('/')[-1].replace('.xml', '').replace('rss', '').title()
                                    await self.bucket_core.add_feed(feed_name, rss_url)
                                    
                                    embed.description = f"✅ Added RSS feed: {feed_name}"
                                    embed.color = discord.Color.green()
                                    await status_message.edit(embed=embed)
                            except Exception as e:
                                embed.description = f"❌ Error adding RSS feed: {str(e)}"
                                embed.color = discord.Color.red()
                                await status_message.edit(embed=embed)
                        
                        await message.add_reaction("📰")
                
                # Regular URL detection for non-dedicated channels
                elif not message.content.startswith(self.command_prefix):
                    urls = self._extract_urls(message.content)
                    
                    if urls:
                        # Create embed for auto-detected URLs
                        embed = discord.Embed(
                            title="🔗 URLs Detected",
                            description="I found URLs in your message. Use `!add <url>` to add them to your bucket.",
                            color=discord.Color.yellow(),
                            timestamp=datetime.utcnow()
                        )
                        
                        for i, url in enumerate(urls[:3], 1):  # Limit to 3 URLs
                            embed.add_field(
                                name=f"URL {i}",
                                value=f"`{url}`",
                                inline=False
                            )
                        
                        if len(urls) > 3:
                            embed.add_field(
                                name="Note",
                                value=f"And {len(urls) - 3} more URLs...",
                                inline=False
                            )
                        
                        await message.channel.send(embed=embed)
                
                await self.process_commands(message)
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(url_pattern.match(url))
    
    def _extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text."""
        url_pattern = re.compile(
            r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?',
            re.IGNORECASE
        )
        return url_pattern.findall(text)
    
    def _extract_rss_urls(self, text: str) -> List[str]:
        """Extract RSS feed URLs from text."""
        rss_patterns = [
            r'https?://[^\s]+\.xml',
            r'https?://[^\s]+/rss',
            r'https?://[^\s]+/feed',
            r'https?://[^\s]+/atom',
        ]
        
        rss_urls = []
        for pattern in rss_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            rss_urls.extend(matches)
        
        return list(set(rss_urls))  # Remove duplicates
    
    async def get_queued_articles(self) -> List[Article]:
        """Get all articles from the queue."""
        articles = []
        while not self.article_queue.empty():
            try:
                article = self.article_queue.get_nowait()
                articles.append(article)
            except asyncio.QueueEmpty:
                break
        return articles


class DiscordManager:
    """Manages Discord bot integration."""
    
    def __init__(self, token: str, command_prefix: str = "!", bucket_core=None, dedicated_channel_id: Optional[int] = None):
        self.token = token
        self.command_prefix = command_prefix
        self.bucket_core = bucket_core
        self.dedicated_channel_id = dedicated_channel_id
        self.bot = None
    
    async def start_bot(self):
        """Start the Discord bot."""
        if not DISCORD_AVAILABLE:
            raise RuntimeError("Discord.py not available")
            
        self.bot = BucketBot(
            command_prefix=self.command_prefix,
            bucket_core=self.bucket_core,
            dedicated_channel_id=self.dedicated_channel_id
        )
        
        try:
            await self.bot.start(self.token)
        except discord.LoginFailure:
            print("❌ Invalid Discord token")
            raise
        except Exception as e:
            print(f"❌ Error starting Discord bot: {e}")
            raise
    
    async def stop_bot(self):
        """Stop the Discord bot."""
        if self.bot:
            await self.bot.close()
    
    def get_bot(self):
        """Get the bot instance."""
        return self.bot