"""Discord bot for bucket system."""

import asyncio
import re
from datetime import datetime
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
        
        def __init__(self, command_prefix: str = "!", intents: Optional[discord.Intents] = None):
            if intents is None:
                intents = discord.Intents.default()
                intents.message_content = True
            
            super().__init__(command_prefix=command_prefix, intents=intents)
else:
    class BucketBot:
        """Discord bot for bucket system (not available)."""
        
        def __init__(self, command_prefix: str = "!", intents=None):
            raise RuntimeError("Discord.py not available")
    
    def add_commands(self):
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
                
                # Add to queue for processing
                await self.article_queue.put(article)
                
                # Update embed
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
            
            # Check for URLs in message
            urls = self._extract_urls(message.content)
            
            if urls and not message.content.startswith(self.command_prefix):
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
    
    def __init__(self, token: str, command_prefix: str = "!"):
        self.token = token
        self.command_prefix = command_prefix
        self.bot = None
    
    async def start_bot(self):
        """Start the Discord bot."""
        self.bot = BucketBot(command_prefix=self.command_prefix)
        
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
    
    def get_bot(self) -> Optional[BucketBot]:
        """Get the bot instance."""
        return self.bot