#!/usr/bin/env python3
"""
Example usage of the modular RSS system for quick briefings and dynamic updates.

This demonstrates how to:
1. Use the !rss Discord command
2. Set up automatic RSS feed updates
3. Use the API for dynamic management
4. Integrate with discord-buddy for arbitrary interval updates
"""

import asyncio
import aiohttp
from datetime import datetime


async def example_api_usage():
    """Example of using the RSS API endpoints."""
    base_url = "http://localhost:8000"
    
    print("🚀 RSS API Example Usage")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        
        # 1. Add some RSS feeds (if not already added)
        print("\n📡 Adding RSS feeds...")
        feeds_to_add = [
            {"name": "Hacker News", "url": "https://news.ycombinator.com/rss", "tags": ["tech", "news"]},
            {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "tags": ["tech", "startup"]},
            {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "tags": ["tech", "consumer"]}
        ]
        
        for feed_data in feeds_to_add:
            try:
                async with session.post(f"{base_url}/feeds", json=feed_data) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        print(f"  ✅ Added feed: {feed_data['name']}")
                    else:
                        print(f"  ⚠️ Feed might already exist: {feed_data['name']}")
            except Exception as e:
                print(f"  ❌ Error adding {feed_data['name']}: {e}")
        
        # 2. Refresh RSS feeds
        print("\n🔄 Refreshing RSS feeds...")
        try:
            async with session.post(f"{base_url}/rss/refresh", params={"max_articles_per_feed": 5}) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"  ✅ Processed {result['feeds_processed']} feeds")
                    print(f"  📰 Found {result['new_articles']} new articles")
                    for feed_name, count in result['results'].items():
                        print(f"    - {feed_name}: {count} articles")
        except Exception as e:
            print(f"  ❌ Error refreshing feeds: {e}")
        
        # 3. Generate RSS briefing
        print("\n📋 Generating RSS briefing...")
        try:
            params = {
                "days_back": 7,
                "max_articles_per_feed": 3,
                "format": "json"
            }
            async with session.get(f"{base_url}/rss/briefing", params=params) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    briefing = result['data']
                    stats = briefing['stats']
                    
                    print(f"  📊 Briefing Summary:")
                    print(f"    - Articles: {stats['total_articles']}")
                    print(f"    - Active Feeds: {stats['active_feeds']}")
                    print(f"    - Reading Time: {stats['total_reading_time']} minutes")
                    print(f"    - Total Words: {stats['total_words']:,}")
                    
                    print(f"\n  📰 Articles by Feed:")
                    for feed_name, articles in briefing['articles_by_feed'].items():
                        if articles:
                            print(f"    🔸 {feed_name} ({len(articles)} articles):")
                            for article in articles[:2]:  # Show first 2
                                print(f"      • {article['title'][:60]}...")
        except Exception as e:
            print(f"  ❌ Error generating briefing: {e}")
        
        # 4. Get RSS stats
        print("\n📊 Getting RSS feed statistics...")
        try:
            async with session.get(f"{base_url}/rss/stats") as resp:
                if resp.status == 200:
                    stats = await resp.json()
                    print(f"  📈 RSS Statistics:")
                    print(f"    - Total Feeds: {stats['total_feeds']}")
                    print(f"    - Active Feeds: {stats['active_feeds']}")
                    print(f"    - Total Articles: {stats['total_articles']}")
                    
                    if 'feeds' in stats:
                        print(f"\n  📡 Feed Details:")
                        for feed_stat in stats['feeds'][:3]:  # Show first 3
                            feed = feed_stat['feed']
                            last_fetch = feed_stat['last_fetched']
                            last_fetch_str = datetime.fromisoformat(last_fetch.replace('Z', '+00:00')).strftime('%b %d, %H:%M') if last_fetch else "Never"
                            
                            status = "🟢 Active" if feed['is_active'] else "🔴 Inactive"
                            print(f"    {status} {feed['name']}: {feed_stat['article_count']} articles (Last: {last_fetch_str})")
        except Exception as e:
            print(f"  ❌ Error getting stats: {e}")
        
        # 5. Set up automated scheduling
        print("\n⏰ Setting up RSS scheduler...")
        try:
            # Start the scheduler
            async with session.post(f"{base_url}/rss/scheduler/start") as resp:
                if resp.status == 200:
                    print("  ✅ RSS scheduler started")
            
            # Add a global schedule (all feeds every 4 hours)
            schedule_data = {
                "name": "global_rss_update",
                "config": {
                    "feed_id": None,  # All feeds
                    "interval_minutes": 240,  # 4 hours
                    "max_articles": 5,
                    "enabled": True
                }
            }
            
            async with session.post(f"{base_url}/rss/scheduler/schedules", json=schedule_data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"  ✅ Added schedule: {result['schedule_name']}")
            
            # Check scheduler status
            async with session.get(f"{base_url}/rss/scheduler/status") as resp:
                if resp.status == 200:
                    status = await resp.json()
                    print(f"  📊 Scheduler Status:")
                    print(f"    - Running: {status['running']}")
                    print(f"    - Total Schedules: {status['total_schedules']}")
                    print(f"    - Enabled Schedules: {status['enabled_schedules']}")
                    
        except Exception as e:
            print(f"  ❌ Error with scheduler: {e}")


def discord_usage_examples():
    """Examples of Discord bot commands."""
    print("\n🤖 Discord Bot Usage Examples")
    print("=" * 50)
    
    examples = [
        {
            "command": "!rss",
            "description": "Generate RSS briefing from last 7 days (default)",
            "example": "!rss"
        },
        {
            "command": "!rss 3",
            "description": "Generate RSS briefing from last 3 days",
            "example": "!rss 3"
        },
        {
            "command": "!rss 7 text",
            "description": "Generate RSS briefing as plain text",
            "example": "!rss 7 text"
        },
        {
            "command": "!rss refresh",
            "description": "Refresh all RSS feeds and show results",
            "example": "!rss refresh"
        },
        {
            "command": "!rss stats",
            "description": "Show RSS feed statistics",
            "example": "!rss stats"
        },
        {
            "command": "!feeds add",
            "description": "Add a new RSS feed",
            "example": '!feeds add "Tech News" https://example.com/feed.xml'
        },
        {
            "command": "!brief",
            "description": "Generate briefing from all sources (RSS + manual articles)",
            "example": "!brief 7 discord"
        }
    ]
    
    for example in examples:
        print(f"\n📝 {example['command']}")
        print(f"   Description: {example['description']}")
        print(f"   Usage: {example['example']}")


async def discord_buddy_integration_example():
    """Example of how discord-buddy can use the API for arbitrary interval updates."""
    print("\n🤝 Discord-Buddy Integration Example")
    print("=" * 50)
    
    print("""
Discord-buddy can ping these API endpoints at arbitrary intervals:

1. **Automatic RSS Updates:**
   POST http://localhost:8000/rss/refresh
   - Refreshes all RSS feeds
   - Returns count of new articles found
   - Can be called every 30 minutes, 2 hours, etc.

2. **Generate Quick Briefing:**
   GET http://localhost:8000/rss/briefing?format=discord&days_back=1
   - Gets RSS briefing for last 1 day in Discord format
   - Perfect for daily automated summaries

3. **Individual Feed Updates:**
   POST http://localhost:8000/rss/refresh/{feed_id}
   - Update specific feeds at different intervals
   - High-priority feeds every hour, others every 4 hours

4. **Schedule Management:**
   POST http://localhost:8000/rss/scheduler/schedules
   - Add new scheduled updates dynamically
   - Modify intervals based on activity patterns

Example discord-buddy script:
```python
import aiohttp
import asyncio

async def auto_rss_update():
    async with aiohttp.ClientSession() as session:
        # Refresh feeds
        async with session.post('http://localhost:8000/rss/refresh') as resp:
            result = await resp.json()
            
        # If new articles found, generate briefing
        if result['new_articles'] > 0:
            async with session.get(
                'http://localhost:8000/rss/briefing',
                params={'format': 'discord', 'days_back': 1}
            ) as resp:
                briefing = await resp.json()
                # Send briefing to Discord channel
                await send_discord_embed(briefing['embed'])

# Run every 30 minutes
asyncio.create_task(auto_rss_update())
```
""")


def main():
    """Main example runner."""
    print("🪣 Bucket RSS System - Example Usage")
    print("=" * 60)
    print("This example demonstrates the new modular RSS functionality:")
    print("• !rss Discord command for quick briefings")
    print("• Dynamic RSS feed management")
    print("• API endpoints for automation")
    print("• Scheduler for arbitrary interval updates")
    print("• Integration with discord-buddy")
    print("=" * 60)
    
    # Show Discord usage examples
    discord_usage_examples()
    
    # Show discord-buddy integration
    asyncio.run(discord_buddy_integration_example())
    
    # Show API usage (requires running server)
    print("\n🚀 To test API functionality, start the server with:")
    print("   python -m bucket.cli serve")
    print("\nThen run the API examples:")
    
    try:
        asyncio.run(example_api_usage())
    except Exception as e:
        print(f"\n⚠️  Could not connect to API server: {e}")
        print("Make sure the bucket API is running on http://localhost:8000")
        print("Start it with: python -m bucket.cli serve")


if __name__ == "__main__":
    main()