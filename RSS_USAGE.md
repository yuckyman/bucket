# RSS Quick Briefing System 📡

A modular and dynamic RSS system that allows you to type `!rss` for quick briefings and enables `discord-buddy` to ping the API for automatic updates at arbitrary intervals.

## 🚀 Quick Start

### Discord Commands

```bash
# Generate RSS briefing (default: last 7 days)
!rss

# Generate RSS briefing for specific time period
!rss 3              # Last 3 days
!rss 14             # Last 2 weeks

# Different output formats
!rss 7 discord      # Discord embed (default)
!rss 7 text         # Plain text format
!rss refresh        # Refresh all feeds and show results
!rss stats          # Show RSS feed statistics
```

### API Endpoints

The system provides RESTful API endpoints for dynamic RSS management:

#### RSS Management
- `POST /rss/refresh` - Refresh all RSS feeds
- `POST /rss/refresh/{feed_id}` - Refresh specific feed
- `GET /rss/briefing` - Generate RSS briefing
- `GET /rss/stats` - Get RSS feed statistics

#### Feed Management
- `GET /feeds` - List all RSS feeds
- `POST /feeds` - Add new RSS feed
- `PUT /feeds/{feed_id}` - Update RSS feed
- `DELETE /feeds/{feed_id}` - Delete RSS feed
- `POST /feeds/{feed_id}/toggle` - Toggle feed active status

#### Scheduler Management
- `POST /rss/scheduler/start` - Start RSS scheduler
- `POST /rss/scheduler/stop` - Stop RSS scheduler
- `GET /rss/scheduler/status` - Get scheduler status
- `POST /rss/scheduler/schedules` - Add new schedule
- `GET /rss/scheduler/schedules` - List all schedules
- `DELETE /rss/scheduler/schedules/{name}` - Remove schedule
- `POST /rss/scheduler/schedules/{name}/run` - Trigger schedule manually

## 🤖 Discord-Buddy Integration

The system is designed for seamless integration with discord-buddy for arbitrary interval updates:

### Basic Integration
```python
import aiohttp
import asyncio

async def auto_rss_update():
    """Auto-update RSS feeds and post briefings."""
    async with aiohttp.ClientSession() as session:
        # Refresh all feeds
        async with session.post('http://localhost:8000/rss/refresh') as resp:
            result = await resp.json()
            
        # If new articles found, generate briefing
        if result['new_articles'] > 0:
            async with session.get(
                'http://localhost:8000/rss/briefing',
                params={'format': 'discord', 'days_back': 1}
            ) as resp:
                briefing = await resp.json()
                # Send to Discord channel
                await send_discord_embed(briefing['embed'])

# Run every 30 minutes
asyncio.create_task(auto_rss_update())
```

### Advanced Scheduling
```python
# Set up different intervals for different feeds
async def setup_dynamic_schedules():
    async with aiohttp.ClientSession() as session:
        # High-priority feeds every hour
        await session.post('http://localhost:8000/rss/scheduler/schedules', json={
            "name": "high_priority_feeds",
            "config": {
                "interval_minutes": 60,
                "max_articles": 10,
                "enabled": True
            }
        })
        
        # General feeds every 4 hours
        await session.post('http://localhost:8000/rss/scheduler/schedules', json={
            "name": "general_feeds",
            "config": {
                "interval_minutes": 240,
                "max_articles": 5,
                "enabled": True
            }
        })
```

## 📋 Features

### Modular Design
- **RSSManager**: Core RSS operations and briefing generation
- **RSSScheduler**: Automatic updates at configurable intervals
- **RSSBriefingFormatter**: Multiple output formats (Discord, text, JSON)
- **DiscordRSSScheduler**: Discord-specific wrapper with notifications

### Dynamic Configuration
- Add/remove RSS feeds on the fly
- Modify update intervals dynamically
- Enable/disable specific feeds
- Priority-based article sorting

### Multiple Output Formats
- **Discord Embeds**: Rich formatted output with emojis and styling
- **Plain Text**: Simple text format for logging or other uses
- **JSON**: Structured data for programmatic consumption

### Smart Features
- Duplicate article detection
- Priority-based sorting
- Reading time estimation
- Feed grouping and statistics
- Automatic feed health monitoring

## 🛠️ Configuration

### Environment Variables
```bash
# Database
BUCKET_DB_PATH=bucket.db

# API Server
BUCKET_API_HOST=0.0.0.0
BUCKET_API_PORT=8000

# Output
BUCKET_OUTPUT_DIR=output
```

### RSS Briefing Configuration
```python
from bucket.rss_manager import RSSBriefingConfig

config = RSSBriefingConfig(
    max_articles_per_feed=5,    # Limit articles per feed
    max_total_articles=25,      # Total article limit
    days_back=7,                # Time period to consider
    include_summaries=True,     # Include AI summaries
    sort_by_priority=True,      # Sort by article priority
    group_by_feed=True          # Group articles by source feed
)
```

## 📊 Usage Examples

### Basic RSS Briefing
```bash
# In Discord
!rss

# Response: Rich embed showing:
# - Summary statistics (articles, feeds, reading time)
# - Top articles from each feed
# - Feed status and last update times
```

### Feed Statistics
```bash
# In Discord
!rss stats

# Response: Detailed statistics showing:
# - Total feeds and articles
# - Active vs inactive feeds
# - Articles per feed
# - Last fetch times
```

### Refresh Feeds
```bash
# In Discord
!rss refresh

# Response: Live update showing:
# - Feeds being processed
# - New articles found per feed
# - Total new articles discovered
```

### API Usage
```python
import aiohttp

async def get_rss_briefing():
    async with aiohttp.ClientSession() as session:
        async with session.get(
            'http://localhost:8000/rss/briefing',
            params={
                'days_back': 7,
                'max_articles_per_feed': 5,
                'format': 'json'
            }
        ) as resp:
            return await resp.json()
```

## 🔧 Advanced Features

### Custom Scheduling
```python
from bucket.rss_scheduler import ScheduleConfig, RSSScheduler

# Create custom schedule
config = ScheduleConfig(
    feed_id=1,                    # Specific feed ID (None for all)
    interval_minutes=30,          # Every 30 minutes
    max_articles=10,              # Max articles to fetch
    enabled=True,                 # Active schedule
    callback_url="https://webhook.discord.com/...",  # Discord webhook
    callback_data={"channel": "news"}  # Additional data
)

scheduler = RSSScheduler(database)
scheduler.add_schedule("custom_news", config)
await scheduler.start()
```

### Feed Management
```python
from bucket.rss_manager import RSSManager

rss_manager = RSSManager(database)

# Add feed
feed = await rss_manager.add_feed(
    name="Tech News",
    url="https://example.com/feed.xml",
    tags=["tech", "news"],
    description="Latest technology news"
)

# Update feed
await rss_manager.update_feed(feed.id, is_active=False)

# Get statistics
stats = await rss_manager.get_feed_stats()
```

## 🚀 Getting Started

1. **Start the API server:**
   ```bash
   python -m bucket.cli serve
   ```

2. **Add RSS feeds via Discord:**
   ```bash
   !feeds add "Hacker News" https://news.ycombinator.com/rss
   ```

3. **Generate your first briefing:**
   ```bash
   !rss refresh
   !rss briefing 7
   ```

4. **Set up automatic updates (optional):**
   ```python
   # Via API
   POST /rss/scheduler/start
   POST /rss/scheduler/schedules
   ```

5. **Integrate with discord-buddy:**
   ```python
   # Use the provided integration examples
   # in bucket/examples/rss_example.py
   ```

## 📈 Benefits

- **Quick Access**: Type `!rss` for instant RSS briefings
- **Dynamic Management**: Add/remove feeds without restarting
- **Flexible Scheduling**: Different intervals for different priorities
- **Multiple Formats**: Discord embeds, text, JSON outputs
- **Discord-Buddy Ready**: API endpoints for external automation
- **Modular Design**: Easy to extend and customize
- **Smart Features**: Duplicate detection, priority sorting, statistics

This system transforms RSS feed management from a static configuration into a dynamic, interactive experience perfect for Discord communities and automated workflows.