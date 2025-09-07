#!/usr/bin/env python3
"""Example script to set up daily duplicate cleanup at 14:00 UTC."""

import asyncio
from bucket.database import Database
from bucket.rss_scheduler import DiscordRSSScheduler


async def setup_daily_cleanup():
    """Set up daily duplicate cleanup schedule."""
    print("🚀 Setting up daily duplicate cleanup...")
    
    # Initialize database
    db = Database("bucket.db")
    db.initialize(async_mode=True)
    await db.create_tables()
    
    # Initialize scheduler
    scheduler = DiscordRSSScheduler(db)
    
    # Add daily cleanup schedule at 14:00 UTC
    schedule_name = scheduler.add_daily_cleanup_schedule(hour=14, minute=0, days_back=30)
    
    print(f"✅ Daily cleanup schedule added: {schedule_name}")
    print("🕐 Cleanup will run daily at 14:00 UTC")
    print("📅 Will check for duplicates in articles from the last 30 days")
    
    # Start the scheduler
    await scheduler.start()
    print("🔄 Scheduler started! Press Ctrl+C to stop.")
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        print("\n🛑 Stopping scheduler...")
        await scheduler.stop()
        await db.close()
        print("✅ Scheduler stopped.")


if __name__ == "__main__":
    asyncio.run(setup_daily_cleanup())
