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
        
        def __init__(self, command_prefix: str = "!", intents: Optional[discord.Intents] = None, allowed_channel_id: Optional[int] = None, database=None):
            if intents is None:
                intents = discord.Intents.default()
                intents.message_content = True
            
            super().__init__(command_prefix=command_prefix, intents=intents, help_command=None)
            self.allowed_channel_id = allowed_channel_id
            
            # Initialize components
            self.fetcher = ContentFetcher()
            self.article_queue = asyncio.Queue()
            self.db = database
            
            @self.event
            async def on_ready():
                """Called when the bot is ready."""
                print(f"🎉 Bot is ready! Logged in as {self.user}")
                print(f"📺 Connected to {len(self.guilds)} guild(s)")
                if self.allowed_channel_id:
                    print(f"🎯 Restricted to channel: {self.allowed_channel_id}")
            
            @self.command(name="add")
            async def add_url(ctx, url: str):
                # Check if command is in allowed channel
                if self.allowed_channel_id and ctx.channel.id != self.allowed_channel_id:
                    return
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
            
            @self.command(name="feed")
            async def add_feed(ctx, name: str, url: str):
                # Check if command is in allowed channel
                if self.allowed_channel_id and ctx.channel.id != self.allowed_channel_id:
                    return
                """Add an RSS feed to the bucket."""
                if not self._is_valid_url(url):
                    await ctx.send("❌ Invalid RSS feed URL provided.")
                    return
                
                # Create embed for feedback
                embed = discord.Embed(
                    title="📡 Adding RSS Feed",
                    description=f"Processing: {name}",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Feed URL", value=url, inline=False)
                embed.add_field(name="Status", value="⏳ Validating feed...", inline=False)
                
                message = await ctx.send(embed=embed)
                
                try:
                    # Validate RSS feed
                    import feedparser
                    feed = feedparser.parse(url)
                    
                    if feed.bozo or not feed.entries:
                        embed.description = f"❌ Invalid RSS feed: {name}"
                        embed.color = discord.Color.red()
                        embed.set_field_at(1, name="Status", value="❌ Invalid feed", inline=False)
                        await message.edit(embed=embed)
                        return
                    
                    # Update embed with success
                    embed.description = f"✅ RSS feed added: {name}"
                    embed.color = discord.Color.green()
                    embed.set_field_at(1, name="Status", value="✅ Feed validated", inline=False)
                    embed.add_field(name="Feed Title", value=feed.feed.get('title', 'Unknown'), inline=True)
                    embed.add_field(name="Entries", value=str(len(feed.entries)), inline=True)
                    
                    await message.edit(embed=embed)
                    
                except Exception as e:
                    embed.description = f"❌ Error processing RSS feed: {name}"
                    embed.color = discord.Color.red()
                    embed.set_field_at(1, name="Status", value=f"❌ Error: {str(e)}", inline=False)
                    await message.edit(embed=embed)
            
            @self.command(name="status")
            async def status(ctx):
                # Check if command is in allowed channel
                if self.allowed_channel_id and ctx.channel.id != self.allowed_channel_id:
                    return
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
                # Check if command is in allowed channel
                if self.allowed_channel_id and ctx.channel.id != self.allowed_channel_id:
                    return
                """Show help information."""
                embed = discord.Embed(
                    title="🪣 Bucket Bot Help",
                    description="Manage your reading bucket with these commands:",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                
                embed.add_field(
                    name="📥 !add <url>",
                    value="Add an article or webpage to your reading bucket\n**Usage:** `!add https://example.com`\n**What it does:** Fetches the article, extracts content, and adds it to your reading queue",
                    inline=False
                )
                embed.add_field(
                    name="📡 !feed <name> <url>",
                    value="Add an RSS feed for automatic article updates\n**Usage:** `!feed \"Tech News\" https://example.com/feed.xml`\n**What it does:** Validates the RSS feed and adds it to your bucket for regular updates",
                    inline=False
                )
                embed.add_field(
                    name="📊 !status",
                    value="Show current bucket system status\n**Usage:** `!status`\n**What it shows:** Queue size, bot status, and system health",
                    inline=False
                )
                embed.add_field(
                    name="📋 !brief [days] [format]",
                    value="Generate a quick briefing of recent articles and RSS feeds\n**Usage:** `!brief 7 discord` (default: 7 days, discord format)\n**Formats:** `discord` (embed), `pdf` (downloadable PDF)\n**What it shows:** Recent articles, active RSS feeds, and reading stats",
                    inline=False
                )
                embed.add_field(
                    name="❓ !help",
                    value="Show this detailed help message\n**Usage:** `!help`\n**What it shows:** All available commands with examples",
                    inline=False
                )
                
                embed.add_field(
                    name="💡 Tips & Features",
                    value="• **Auto-detection:** Just paste a URL in chat and I'll suggest adding it\n• **RSS feeds:** Use `!feed` to add RSS feeds for automatic updates\n• **Auto-summarization:** Articles are automatically summarized using AI\n• **Channel-restricted:** I only respond in this specific channel\n• **Persistent:** Runs 24/7 and survives reboots\n• **Web interface:** Use the web API for advanced features",
                    inline=False
                )
                
                embed.set_footer(text="🪣 Bucket Bot v1.0 • Your personal reading assistant • Channel-restricted to this server")
                
                await ctx.send(embed=embed)
            
            @self.command(name="brief")
            async def generate_brief(ctx, days_back: int = 7, format_type: str = "discord"):
                # Check if command is in allowed channel
                if self.allowed_channel_id and ctx.channel.id != self.allowed_channel_id:
                    return
                """Generate a quick briefing of recent articles and RSS items."""
                
                # Validate format type
                if format_type.lower() not in ["discord", "pdf", "link"]:
                    await ctx.send("❌ Invalid format. Use: `discord`, `pdf`, or `link`")
                    return
                
                # Create initial embed
                embed = discord.Embed(
                    title="📋 Generating Brief",
                    description=f"Compiling recent articles and RSS items from the last {days_back} days...",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Status", value="⏳ Gathering content...", inline=False)
                
                message = await ctx.send(embed=embed)
                
                try:
                    # Get recent articles from database
                    recent_articles = await self.db.get_recent_articles(days_back=days_back, limit=20)
                    
                    # Get active RSS feeds
                    feeds = await self.db.get_feeds(active_only=True)
                    
                    # Update embed with progress
                    embed.set_field_at(0, name="Status", value="✅ Content gathered", inline=False)
                    embed.add_field(name="Articles Found", value=str(len(recent_articles)), inline=True)
                    embed.add_field(name="Active Feeds", value=str(len(feeds)), inline=True)
                    
                    await message.edit(embed=embed)
                    
                    if format_type.lower() == "discord":
                        # Direct Discord output
                        await self._send_discord_briefing(ctx, recent_articles, feeds, days_back, message)
                    else:
                        # PDF/Link output
                        await self._send_pdf_briefing(ctx, recent_articles, feeds, days_back, message)
                    
                except Exception as e:
                    embed.description = f"❌ Error generating brief: {str(e)}"
                    embed.color = discord.Color.red()
                    embed.set_field_at(0, name="Status", value="❌ Failed", inline=False)
                    await message.edit(embed=embed)
            
            async def _send_discord_briefing(self, ctx, recent_articles, feeds, days_back, original_message):
                """Send briefing as Discord embed."""
                # Create main briefing embed
                embed = discord.Embed(
                    title=f"📋 Quick Brief - Last {days_back} Days",
                    description=f"*Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}*",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                
                # Add summary stats
                total_reading_time = sum(article.reading_time or 0 for article in recent_articles)
                total_words = sum(article.word_count or 0 for article in recent_articles)
                
                embed.add_field(
                    name="📊 Summary",
                    value=f"• **Articles:** {len(recent_articles)}\n• **Feeds:** {len(feeds)}\n• **Reading time:** {total_reading_time} min\n• **Words:** {total_words:,}",
                    inline=False
                )
                
                # Add recent articles (limit to 5 for embed)
                if recent_articles:
                    articles_text = ""
                    for i, article in enumerate(recent_articles[:5], 1):
                        reading_time = article.reading_time or 0
                        priority_emoji = {
                            "high": "🔴",
                            "medium": "🟡", 
                            "low": "🟢"
                        }.get(article.priority.value, "⚪")
                        
                        articles_text += f"{priority_emoji} **{article.title}**\n"
                        if article.author:
                            articles_text += f"   *By {article.author}*\n"
                        articles_text += f"   📖 {reading_time} min • 📅 {article.created_at.strftime('%b %d')}\n"
                        articles_text += f"   🔗 {article.url}\n\n"
                    
                    if len(recent_articles) > 5:
                        articles_text += f"... and {len(recent_articles) - 5} more articles"
                    
                    embed.add_field(name=f"📰 Recent Articles ({len(recent_articles)})", value=articles_text, inline=False)
                else:
                    embed.add_field(name="📰 Recent Articles", value="*No recent articles found.*", inline=False)
                
                # Add RSS feeds info
                if feeds:
                    feeds_text = ""
                    for feed in feeds[:3]:  # Limit to 3 feeds for embed
                        feeds_text += f"**{feed.name}**\n"
                        if feed.tags:
                            feeds_text += f"   🏷️  {', '.join(feed.tags)}\n"
                        if feed.last_fetched:
                            feeds_text += f"   📅 Last: {feed.last_fetched.strftime('%b %d, %H:%M')}\n"
                        feeds_text += "\n"
                    
                    if len(feeds) > 3:
                        feeds_text += f"... and {len(feeds) - 3} more feeds"
                    
                    embed.add_field(name=f"📡 RSS Feeds ({len(feeds)} active)", value=feeds_text, inline=False)
                else:
                    embed.add_field(name="📡 RSS Feeds", value="*No active RSS feeds configured.*", inline=False)
                
                # Update original message
                embed.set_footer(text="🪣 Bucket Bot • Use !brief pdf for full PDF version")
                await original_message.edit(embed=embed)
            
            async def _send_pdf_briefing(self, ctx, recent_articles, feeds, days_back, original_message):
                """Generate PDF briefing and provide download link."""
                try:
                    # Import PDF generator
                    from .pdf_generator import PDFGenerator
                    
                    # Create PDF generator
                    pdf_gen = PDFGenerator(output_dir="output")
                    
                    # Generate PDF
                    pdf_path = await pdf_gen.generate_briefing(
                        articles=recent_articles,
                        title=f"Quick Brief - Last {days_back} Days",
                        date=datetime.now()
                    )
                    
                    # Create success embed
                    embed = discord.Embed(
                        title="📋 Briefing Generated",
                        description=f"Your briefing is ready! 📄",
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    
                    # Add stats
                    total_reading_time = sum(article.reading_time or 0 for article in recent_articles)
                    total_words = sum(article.word_count or 0 for article in recent_articles)
                    
                    embed.add_field(
                        name="📊 Summary",
                        value=f"• **Articles:** {len(recent_articles)}\n• **Feeds:** {len(feeds)}\n• **Reading time:** {total_reading_time} min\n• **Words:** {total_words:,}",
                        inline=False
                    )
                    
                    # Send file as attachment
                    filename = pdf_path.split('/')[-1]
                    embed.add_field(
                        name="📥 Download",
                        value=f"Your briefing is attached below!",
                        inline=False
                    )
                    
                    embed.set_footer(text="🪣 Bucket Bot • PDF generated successfully")
                    
                    # Send the embed and file
                    with open(pdf_path, 'rb') as f:
                        file = discord.File(f, filename=filename)
                        await original_message.edit(embed=embed)
                        await ctx.send(file=file)
                    
                except Exception as e:
                    embed = discord.Embed(
                        title="❌ PDF Generation Failed",
                        description=f"Error generating PDF: {str(e)}",
                        color=discord.Color.red(),
                        timestamp=datetime.utcnow()
                    )
                    await original_message.edit(embed=embed)
            
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

else:
    class BucketBot:
        """Discord bot for bucket system (not available)."""
        
        def __init__(self, command_prefix: str = "!", intents=None):
            raise RuntimeError("Discord.py not available")


class DiscordManager:
    """Manages Discord bot integration."""
    
    def __init__(self, token: str, command_prefix: str = "!", allowed_channel_id: Optional[int] = None, database=None):
        self.token = token
        self.command_prefix = command_prefix
        self.allowed_channel_id = allowed_channel_id
        self.database = database
        self.bot = None
    
    async def start_bot(self):
        """Start the Discord bot."""
        print(f"🤖 Starting Discord bot...")
        self.bot = BucketBot(
            command_prefix=self.command_prefix, 
            allowed_channel_id=self.allowed_channel_id,
            database=self.database
        )
        
        try:
            print(f"🔗 Connecting to Discord...")
            await self.bot.start(self.token)
            print(f"✅ Discord bot connected successfully!")
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