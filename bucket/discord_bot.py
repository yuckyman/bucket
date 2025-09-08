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
            async def add_url(ctx, *args):
                # Check if command is in allowed channel
                if self.allowed_channel_id and ctx.channel.id != self.allowed_channel_id:
                    return
                """Add a URL to the bucket or add an RSS feed."""
                
                # Handle !add feed "Name" URL case
                if len(args) >= 3 and args[0].lower() == "feed":
                    feed_name = args[1]
                    feed_url = args[2]
                    
                    # Create initial embed
                    embed = discord.Embed(
                        title="📡 Adding RSS Feed",
                        description=f"Adding feed: **{feed_name}**",
                        color=discord.Color.blue(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="URL", value=feed_url, inline=False)
                    embed.add_field(name="Status", value="⏳ Triggering GitHub Action...", inline=False)
                    
                    message = await ctx.send(embed=embed)
                    
                    # Trigger GitHub Action for feed adding
                    try:
                        import requests
                        import os
                        
                        # Get GitHub token and repo info
                        github_token = os.getenv("GITHUB_TOKEN")
                        github_repo = os.getenv("GITHUB_REPO", "yourusername/bucket")  # Update this
                        
                        if not github_token:
                            raise Exception("GitHub token not configured")
                        
                        # Prepare payload for GitHub Actions
                        payload = {
                            "event_type": "discord_command",
                            "client_payload": {
                                "command": "feeds",
                                "args": ["add", feed_name, feed_url],
                                "user": ctx.author.display_name,
                                "channel": ctx.channel.name,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        }
                        
                        # Send to GitHub Actions
                        url = f"https://api.github.com/repos/{github_repo}/dispatches"
                        headers = {
                            "Authorization": f"token {github_token}",
                            "Accept": "application/vnd.github.v3+json"
                        }
                        
                        response = requests.post(url, headers=headers, json=payload)
                        response.raise_for_status()
                        
                        embed.color = discord.Color.green()
                        embed.set_field_at(1, name="Status", value="✅ Feed addition triggered!", inline=False)
                        embed.add_field(name="Method", value="GitHub Actions", inline=True)
                        embed.add_field(name="Processing", value="In Progress", inline=True)
                        embed.set_footer(text="🪣 Feed will be added to data/feeds.json • Use !feeds list to verify")
                        
                        await message.edit(embed=embed)
                        
                    except Exception as e:
                        embed.color = discord.Color.red()
                        embed.set_field_at(1, name="Status", value=f"❌ Error: {str(e)}", inline=False)
                        await message.edit(embed=embed)
                    return
                
                # Handle regular !add URL case
                if len(args) != 1:
                    await ctx.send("❌ Usage: `!add <url>` or `!add feed \"Name\" <url>`")
                    return
                
                url = args[0]
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
            
            
            @self.command(name="feeds")
            async def manage_feeds(ctx, action: str = "list", name_or_id: str = None, url: str = None):
                # Check if command is in allowed channel
                if self.allowed_channel_id and ctx.channel.id != self.allowed_channel_id:
                    return
                """Unified feed management command."""
                
                try:
                    if action.lower() == "add":
                        # Add a new feed via GitHub Actions
                        if not name_or_id or not url:
                            await ctx.send("❌ Usage: `!feeds add \"Feed Name\" https://example.com/rss`")
                            return
                        
                        # Create initial embed
                        embed = discord.Embed(
                            title="📡 Adding RSS Feed",
                            description=f"Adding feed: **{name_or_id}**",
                            color=discord.Color.blue(),
                            timestamp=datetime.utcnow()
                        )
                        embed.add_field(name="URL", value=url, inline=False)
                        embed.add_field(name="Status", value="⏳ Triggering GitHub Action...", inline=False)
                        
                        message = await ctx.send(embed=embed)
                        
                        # Trigger GitHub Action for feed adding
                        try:
                            import requests
                            import os
                            
                            # Get GitHub token and repo info
                            github_token = os.getenv("GH_PAT")  # Personal Access Token
                            github_repo = os.getenv("GH_REPO", "ian/bucket")  # Update this
                            
                            if not github_token:
                                raise Exception("GitHub token not configured")
                            
                            # Prepare payload for GitHub Actions
                            payload = {
                                "event_type": "discord_command",
                                "client_payload": {
                                    "command": "feeds",
                                    "args": ["add", name_or_id, url],
                                    "user": ctx.author.display_name,
                                    "channel": ctx.channel.name,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            }
                            
                            # Send to GitHub Actions
                            url = f"https://api.github.com/repos/{github_repo}/dispatches"
                            headers = {
                                "Authorization": f"token {github_token}",
                                "Accept": "application/vnd.github.v3+json"
                            }
                            
                            response = requests.post(url, headers=headers, json=payload)
                            response.raise_for_status()
                            
                            embed.color = discord.Color.green()
                            embed.set_field_at(1, name="Status", value="✅ Feed addition triggered!", inline=False)
                            embed.add_field(name="Method", value="GitHub Actions", inline=True)
                            embed.add_field(name="Processing", value="In Progress", inline=True)
                            embed.set_footer(text="🪣 Feed will be added to data/feeds.json • Use !feeds list to verify")
                            
                            await message.edit(embed=embed)
                            
                        except Exception as e:
                            embed.color = discord.Color.red()
                            embed.set_field_at(1, name="Status", value=f"❌ Error: {str(e)}", inline=False)
                            await message.edit(embed=embed)
                    
                    elif action.lower() == "remove":
                        # Remove a feed
                        if not name_or_id or not name_or_id.isdigit():
                            await ctx.send("❌ Usage: `!feeds remove <feed_id>`\nUse `!feeds list` to see feed IDs.")
                            return
                        
                        feed_id = int(name_or_id)
                        success = await self.db.delete_feed(feed_id)
                        
                        if success:
                            embed = discord.Embed(
                                title="🗑️ Feed Removed",
                                description=f"Successfully removed feed with ID {feed_id}",
                                color=discord.Color.green(),
                                timestamp=datetime.utcnow()
                            )
                        else:
                            embed = discord.Embed(
                                title="❌ Feed Not Found",
                                description=f"No feed found with ID {feed_id}",
                                color=discord.Color.red(),
                                timestamp=datetime.utcnow()
                            )
                        
                        await ctx.send(embed=embed)
                    
                    elif action.lower() == "toggle":
                        # Toggle a feed
                        if not name_or_id or not name_or_id.isdigit():
                            await ctx.send("❌ Usage: `!feeds toggle <feed_id>`\nUse `!feeds list` to see feed IDs.")
                            return
                        
                        feed_id = int(name_or_id)
                        feed = await self.db.get_feed(feed_id)
                        
                        if not feed:
                            await ctx.send(f"❌ No feed found with ID {feed_id}")
                            return
                        
                        new_status = not feed.is_active
                        updated_feed = await self.db.update_feed(feed_id, is_active=new_status)
                        
                        status_text = "enabled" if new_status else "disabled"
                        status_emoji = "🟢" if new_status else "🔴"
                        
                        embed = discord.Embed(
                            title=f"{status_emoji} Feed {status_text.title()}",
                            description=f"Feed **{feed.name}** has been {status_text}",
                            color=discord.Color.green() if new_status else discord.Color.orange(),
                            timestamp=datetime.utcnow()
                        )
                        
                        await ctx.send(embed=embed)
                    
                    elif action.lower() == "list":
                        # List all feeds (default behavior)
                        feeds = await self.db.get_feeds(active_only=False)
                        
                        if not feeds:
                            embed = discord.Embed(
                                title="📡 RSS Feeds",
                                description="No RSS feeds found in database.",
                                color=discord.Color.yellow(),
                                timestamp=datetime.utcnow()
                            )
                            embed.add_field(
                                name="💡 Tip",
                                value="Use `!feeds add \"Feed Name\" https://example.com/rss` to add your first RSS feed!",
                                inline=False
                            )
                            await ctx.send(embed=embed)
                            return
                        
                        embed = discord.Embed(
                            title="📡 RSS Feeds",
                            description=f"Found {len(feeds)} RSS feed(s):",
                            color=discord.Color.blue(),
                            timestamp=datetime.utcnow()
                        )
                        
                        for feed in feeds:
                            status_emoji = "🟢" if feed.is_active else "🔴"
                            last_fetch = feed.last_fetched.strftime('%b %d, %H:%M') if feed.last_fetched else "Never"
                            
                            value = f"**URL:** {feed.url}\n"
                            value += f"**Status:** {status_emoji} {'Active' if feed.is_active else 'Inactive'}\n"
                            value += f"**Last Fetch:** {last_fetch}\n"
                            if feed.description:
                                value += f"**Description:** {feed.description[:100]}{'...' if len(feed.description) > 100 else ''}"
                            
                            embed.add_field(
                                name=f"{status_emoji} {feed.name} (ID: {feed.id})",
                                value=value,
                                inline=False
                            )
                        
                        embed.set_footer(text="🪣 Use !feeds add/remove/toggle • !rss refresh to update")
                        await ctx.send(embed=embed)
                    
                    else:
                        await ctx.send("❌ Invalid action. Use: `add`, `remove`, `toggle`, or `list`\n"
                                      "Examples:\n"
                                      "• `!feeds` or `!feeds list` - List all feeds\n"
                                      "• `!feeds add \"Hacker News\" https://news.ycombinator.com/rss` - Add feed\n"
                                      "• `!feeds toggle 1` - Enable/disable feed\n"
                                      "• `!feeds remove 1` - Delete feed")
                    
                except Exception as e:
                    embed = discord.Embed(
                        title="❌ Error",
                        description=f"Error managing feeds: {str(e)}",
                        color=discord.Color.red(),
                        timestamp=datetime.utcnow()
                    )
                    await ctx.send(embed=embed)
            
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
                    name="📡 !add feed \"Name\" <url>",
                    value="Quick shortcut to add a new RSS feed\n**Usage:** `!add feed \"Nature Neuroscience\" https://feeds.nature.com/neuro/rss/current`\n**What it does:** Adds a new RSS feed with auto-detected tags",
                    inline=False
                )
                embed.add_field(
                    name="📰 !feeds [add|remove|toggle|list]",
                    value="Unified RSS feed management\n**Usage:** `!feeds add \"Feed Name\" https://example.com/rss` or `!feeds list`\n**What it does:** Add, remove, toggle, or list RSS feeds in one command",
                    inline=False
                )
                embed.add_field(
                    name="📡 !rss [show|refresh|briefing|stats] [count|days]",
                    value="Unified RSS command for all RSS operations\n**Usage:** `!rss` (show 3), `!rss refresh`, `!rss briefing 7`\n**What it does:** Shows recent unseen RSS items, updates feeds, generates briefings, or shows statistics",
                    inline=False
                )
                embed.add_field(
                    name="📋 !brief [days] [format]",
                    value="Generate a quick briefing of recent articles and RSS feeds\n**Usage:** `!brief 7 discord` (default: 7 days, discord format)\n**Formats:** `discord` (embed), `pdf` (downloadable PDF)\n**What it shows:** Recent articles, active RSS feeds, and reading stats",
                    inline=False
                )
                embed.add_field(
                    name="🧹 !cleanup [days]",
                    value="Clean up duplicate articles from the database\n**Usage:** `!cleanup` (default: 30 days) or `!cleanup 7`\n**What it does:** Removes duplicate articles based on URL, title similarity, and content hash",
                    inline=False
                )
                embed.add_field(
                    name="📊 !status",
                    value="Show current bucket system status\n**Usage:** `!status`\n**What it shows:** Queue size, bot status, and system health",
                    inline=False
                )
                embed.add_field(
                    name="❓ !help",
                    value="Show this detailed help message\n**Usage:** `!help`\n**What it shows:** All available commands with examples",
                    inline=False
                )
                
                embed.add_field(
                    name="💡 Tips & Features",
                    value="• **Auto-detection:** Just paste a URL in chat and I'll suggest adding it\n• **RSS feeds:** Use `!feeds` to manage RSS feeds for automatic updates\n• **Auto-summarization:** Articles are automatically summarized using AI\n• **Channel-restricted:** I only respond in this specific channel\n• **Persistent:** Runs 24/7 and survives reboots\n• **Web interface:** Use the web API for advanced features",
                    inline=False
                )
                
                embed.set_footer(text="🪣 Bucket Bot v2.0 • Simplified commands • Channel-restricted")
                
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
            
            @self.command(name="cleanup")
            async def cleanup_duplicates(ctx, days_back: int = 30):
                # Check if command is in allowed channel
                if self.allowed_channel_id and ctx.channel.id != self.allowed_channel_id:
                    return
                """Clean up duplicate articles from the database."""
                
                # Create initial embed
                embed = discord.Embed(
                    title="🧹 Duplicate Cleanup",
                    description=f"Starting duplicate cleanup for articles from the last {days_back} days...",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Status", value="⏳ Analyzing articles...", inline=False)
                
                message = await ctx.send(embed=embed)
                
                try:
                    # Import RSS manager
                    from .rss_manager import RSSManager
                    
                    # Initialize RSS manager
                    rss_manager = RSSManager(self.db)
                    
                    # Run cleanup
                    result = await rss_manager.cleanup_duplicates(days_back)
                    
                    if result["success"]:
                        embed.color = discord.Color.green()
                        embed.description = f"✅ Duplicate cleanup completed!"
                        embed.set_field_at(0, name="Status", value="✅ Completed", inline=False)
                        
                        embed.add_field(
                            name="📊 Results",
                            value=(f"• **Total Articles:** {result['total_articles']}\n"
                                  f"• **Duplicates Found:** {result['duplicates_found']}\n"
                                  f"• **Duplicates Removed:** {result['duplicates_removed']}\n"
                                  f"• **Sources Checked:** {result['sources_checked']}"),
                            inline=False
                        )
                        
                        embed.add_field(
                            name="💡 Message",
                            value=result["message"],
                            inline=False
                        )
                    else:
                        embed.color = discord.Color.red()
                        embed.description = f"❌ Duplicate cleanup failed!"
                        embed.set_field_at(0, name="Status", value="❌ Failed", inline=False)
                        embed.add_field(
                            name="Error",
                            value=result.get("error", "Unknown error"),
                            inline=False
                        )
                    
                    embed.set_footer(text="🪣 Use !cleanup [days] to specify how many days back to check")
                    await message.edit(embed=embed)
                    
                except Exception as e:
                    embed.description = f"❌ Error during cleanup: {str(e)}"
                    embed.color = discord.Color.red()
                    embed.set_field_at(0, name="Status", value="❌ Error", inline=False)
                    await message.edit(embed=embed)
            
            @self.command(name="rss")
            async def rss_command(ctx, action: str = "show", days_or_arg: str = "3", format_type: str = "discord"):
                # Check if command is in allowed channel
                if self.allowed_channel_id and ctx.channel.id != self.allowed_channel_id:
                    return
                """Unified RSS command for all RSS operations."""
                
                # Import RSS manager here to avoid circular imports
                from .rss_manager import RSSManager, RSSBriefingConfig, RSSBriefingFormatter
                from .models import ArticleStatus
                
                # Initialize RSS manager
                rss_manager = RSSManager(self.db)
                
                try:
                    if action.lower() == "show":
                        # Show recent unseen RSS items (default behavior)
                        num_items = int(days_or_arg) if days_or_arg.isdigit() else 3
                        
                        # Get all recent articles and filter for RSS ones that haven't been delivered
                        all_articles = await self.db.get_recent_articles(days_back=30, limit=100)
                        
                        # Filter for RSS articles that haven't been delivered
                        unseen_rss = [
                            article for article in all_articles
                            if article.source and article.status != ArticleStatus.DELIVERED
                        ]
                        
                        # Sort by creation date (newest first) and take requested number
                        unseen_rss.sort(key=lambda x: x.created_at, reverse=True)
                        recent_unseen = unseen_rss[:num_items]
                        
                        if not recent_unseen:
                            embed = discord.Embed(
                                title="📡 RSS Update",
                                description="No new RSS items to show! 🎉",
                                color=discord.Color.green(),
                                timestamp=datetime.utcnow()
                            )
                            embed.add_field(
                                name="💡 Tip",
                                value="Use `!rss refresh` to fetch new articles from your RSS feeds.",
                                inline=False
                            )
                            await ctx.send(embed=embed)
                            return
                        
                        # Create embed for the items
                        embed = discord.Embed(
                            title="📡 Latest RSS Items",
                            description=f"Here are your {len(recent_unseen)} most recent unseen RSS items:",
                            color=discord.Color.blue(),
                            timestamp=datetime.utcnow()
                        )
                        
                        for i, article in enumerate(recent_unseen, 1):
                            # Calculate reading time display
                            reading_time = f"{article.reading_time} min" if article.reading_time else "? min"
                            
                            # Create article summary
                            value = f"📰 **Source:** {article.source or 'Unknown'}\n"
                            value += f"📅 **Published:** {article.published_date.strftime('%b %d, %Y') if article.published_date else 'Unknown'}\n"
                            value += f"⏱️ **Reading time:** {reading_time}\n"
                            value += f"🔗 [Read article]({article.url})"
                            
                            embed.add_field(
                                name=f"{i}. {article.title[:60]}{'...' if len(article.title) > 60 else ''}",
                                value=value,
                                inline=False
                            )
                        
                        embed.set_footer(text="🪣 Articles marked as read • Use !rss briefing for full briefing")
                        
                        # Send the embed
                        await ctx.send(embed=embed)
                        
                        # Mark these articles as delivered/seen
                        for article in recent_unseen:
                            await self.db.update_article_status(article.id, ArticleStatus.DELIVERED)
                    
                    elif action.lower() == "refresh":
                        # Refresh all feeds and show results
                        embed = discord.Embed(
                            title="📡 RSS Feeds",
                            description="🔄 Refreshing all feeds...",
                            color=discord.Color.blue(),
                            timestamp=datetime.utcnow()
                        )
                        message = await ctx.send(embed=embed)
                        
                        results = await rss_manager.fetch_all_feeds(max_articles_per_feed=10)
                        
                        # Create results embed
                        embed = discord.Embed(
                            title="📡 RSS Feeds Refreshed",
                            description=f"*Updated on {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')}*",
                            color=discord.Color.green(),
                            timestamp=datetime.utcnow()
                        )
                        
                        total_new = sum(len(articles) for articles in results.values())
                        embed.add_field(
                            name="📊 Summary",
                            value=f"• **Feeds Processed:** {len(results)}\n• **New Articles:** {total_new}",
                            inline=False
                        )
                        
                        # Show results per feed (limit to 5 feeds)
                        for i, (feed_name, articles) in enumerate(list(results.items())[:5]):
                            status_emoji = "✅" if articles else "⚪"
                            embed.add_field(
                                name=f"{status_emoji} {feed_name}",
                                value=f"{len(articles)} new articles",
                                inline=True
                            )
                        
                        if len(results) > 5:
                            embed.add_field(
                                name="Note",
                                value=f"... and {len(results) - 5} more feeds",
                                inline=False
                            )
                        
                        embed.set_footer(text="🪣 Use !rss show to see new articles")
                        await message.edit(embed=embed)
                    
                    elif action.lower() == "briefing":
                        # Generate comprehensive briefing
                        days_back = int(days_or_arg) if days_or_arg.isdigit() else 7
                        
                        embed = discord.Embed(
                            title="📡 RSS Briefing",
                            description=f"Generating RSS briefing from the last {days_back} days...",
                            color=discord.Color.blue(),
                            timestamp=datetime.utcnow()
                        )
                        message = await ctx.send(embed=embed)
                        
                        config = RSSBriefingConfig(
                            days_back=days_back,
                            max_articles_per_feed=5,
                            max_total_articles=20,
                            group_by_feed=True,
                            sort_by_priority=True
                        )
                        
                        briefing_data = await rss_manager.generate_rss_briefing(config)
                        
                        if format_type.lower() == "text":
                            text_summary = RSSBriefingFormatter.format_text_summary(briefing_data)
                            await ctx.send(f"```\n{text_summary}\n```")
                            await message.delete()
                        else:
                            embed_data = RSSBriefingFormatter.format_discord_embed(briefing_data)
                            
                            # Create embed with proper discord.py parameters
                            embed = discord.Embed(
                                title=embed_data["title"],
                                description=embed_data["description"],
                                color=embed_data["color"],
                                timestamp=datetime.utcnow()
                            )
                            
                            # Add fields
                            for field in embed_data["fields"]:
                                embed.add_field(**field)
                            
                            embed.set_footer(text="🪣 Use !rss refresh to update feeds")
                            await message.edit(embed=embed)
                    
                    elif action.lower() == "stats":
                        # Show RSS feed statistics
                        embed = discord.Embed(
                            title="📊 RSS Statistics",
                            description="📊 Gathering statistics...",
                            color=discord.Color.blue(),
                            timestamp=datetime.utcnow()
                        )
                        message = await ctx.send(embed=embed)
                        
                        stats = await rss_manager.get_feed_stats()
                        
                        embed = discord.Embed(
                            title="📊 RSS Feed Statistics",
                            description=f"*Generated on {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')}*",
                            color=discord.Color.blue(),
                            timestamp=datetime.utcnow()
                        )
                        
                        embed.add_field(
                            name="📡 Overview",
                            value=(f"• **Total Feeds:** {stats['total_feeds']}\n"
                                  f"• **Active Feeds:** {stats['active_feeds']}\n"
                                  f"• **Total Articles:** {stats['total_articles']}"),
                            inline=False
                        )
                        
                        if stats.get('recent_stats'):
                            embed.add_field(
                                name="📈 Recent Activity",
                                value=stats['recent_stats'],
                                inline=False
                            )
                        
                        embed.set_footer(text="🪣 Use !feeds to manage individual feeds")
                        await message.edit(embed=embed)
                    
                    else:
                        await ctx.send("❌ Invalid action. Use: `show`, `refresh`, `briefing`, or `stats`\n"
                                      "Examples:\n"
                                      "• `!rss` or `!rss show 5` - Show recent items\n"
                                      "• `!rss refresh` - Update all feeds\n"
                                      "• `!rss briefing 7` - Generate briefing\n"
                                      "• `!rss stats` - Show statistics")
                
                except Exception as e:
                    embed = discord.Embed(
                        title="❌ RSS Error",
                        description=f"Error: {str(e)}",
                        color=discord.Color.red(),
                        timestamp=datetime.utcnow()
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