"""RSS feed scheduler for automatic updates at arbitrary intervals."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict

try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False
    schedule = None

from .rss_manager import RSSManager, RSSBriefingConfig
from .database import Database


@dataclass
class ScheduleConfig:
    """Configuration for RSS feed scheduling."""
    feed_id: Optional[int] = None  # None means all feeds
    interval_minutes: int = 60  # Default 1 hour
    max_articles: int = 10
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    callback_url: Optional[str] = None  # Discord webhook or API endpoint
    callback_data: Dict[str, Any] = None


class RSSScheduler:
    """Modular RSS scheduler for dynamic feed updates."""
    
    def __init__(self, database: Database):
        """Initialize RSS scheduler."""
        self.db = database
        self.rss_manager = RSSManager(database)
        self.schedules: Dict[str, ScheduleConfig] = {}
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.callbacks: Dict[str, Callable] = {}
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
    
    def add_schedule(self, name: str, config: ScheduleConfig) -> str:
        """Add a new schedule configuration."""
        self.schedules[name] = config
        config.next_run = self._calculate_next_run(config)
        self.logger.info(f"Added schedule '{name}': {config}")
        return name
    
    def remove_schedule(self, name: str) -> bool:
        """Remove a schedule configuration."""
        if name in self.schedules:
            del self.schedules[name]
            self.logger.info(f"Removed schedule '{name}'")
            return True
        return False
    
    def update_schedule(self, name: str, **kwargs) -> bool:
        """Update an existing schedule configuration."""
        if name not in self.schedules:
            return False
        
        config = self.schedules[name]
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        # Recalculate next run time
        config.next_run = self._calculate_next_run(config)
        self.logger.info(f"Updated schedule '{name}': {config}")
        return True
    
    def get_schedule(self, name: str) -> Optional[ScheduleConfig]:
        """Get a schedule configuration."""
        return self.schedules.get(name)
    
    def list_schedules(self) -> Dict[str, ScheduleConfig]:
        """List all schedule configurations."""
        return self.schedules.copy()
    
    def register_callback(self, name: str, callback: Callable):
        """Register a callback function for notifications."""
        self.callbacks[name] = callback
        self.logger.info(f"Registered callback '{name}'")
    
    def _calculate_next_run(self, config: ScheduleConfig) -> datetime:
        """Calculate the next run time for a schedule."""
        if config.last_run:
            return config.last_run + timedelta(minutes=config.interval_minutes)
        else:
            return datetime.utcnow() + timedelta(minutes=config.interval_minutes)
    
    async def start(self):
        """Start the scheduler."""
        if self.running:
            self.logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._scheduler_loop())
        self.logger.info("RSS scheduler started")
    
    async def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.logger.info("RSS scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self.running:
            try:
                current_time = datetime.utcnow()
                
                # Check each schedule
                for name, config in self.schedules.items():
                    if not config.enabled:
                        continue
                    
                    if config.next_run and current_time >= config.next_run:
                        await self._execute_schedule(name, config)
                
                # Sleep for 1 minute before checking again
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Continue running even if there's an error
    
    async def _execute_schedule(self, name: str, config: ScheduleConfig):
        """Execute a scheduled RSS update."""
        try:
            self.logger.info(f"Executing schedule '{name}'")
            
            if config.feed_id:
                # Update specific feed
                result = await self.rss_manager.refresh_feed(config.feed_id, config.max_articles)
                
                if "error" in result:
                    self.logger.error(f"Error updating feed {config.feed_id}: {result['error']}")
                    return
                
                update_result = {
                    "schedule_name": name,
                    "feed_id": config.feed_id,
                    "feed_name": result["feed"].name,
                    "new_articles": result["new_articles"],
                    "articles": result["articles"]
                }
            else:
                # Update all feeds
                results = await self.rss_manager.fetch_all_feeds(config.max_articles)
                total_new = sum(len(articles) for articles in results.values())
                
                update_result = {
                    "schedule_name": name,
                    "feed_id": None,
                    "feeds_processed": len(results),
                    "new_articles": total_new,
                    "results": results
                }
            
            # Update schedule timing
            config.last_run = datetime.utcnow()
            config.next_run = self._calculate_next_run(config)
            
            # Execute callbacks
            await self._execute_callbacks(name, update_result)
            
            self.logger.info(f"Schedule '{name}' executed successfully")
            
        except Exception as e:
            self.logger.error(f"Error executing schedule '{name}': {e}")
    
    async def _execute_callbacks(self, schedule_name: str, result: Dict[str, Any]):
        """Execute registered callbacks for a schedule."""
        config = self.schedules[schedule_name]
        
        # Execute registered function callbacks
        for callback_name, callback in self.callbacks.items():
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(schedule_name, result)
                else:
                    callback(schedule_name, result)
            except Exception as e:
                self.logger.error(f"Error executing callback '{callback_name}': {e}")
        
        # Execute HTTP callback if configured
        if config.callback_url:
            await self._execute_http_callback(config, result)
    
    async def _execute_http_callback(self, config: ScheduleConfig, result: Dict[str, Any]):
        """Execute HTTP callback (webhook) for notifications."""
        try:
            import aiohttp
            
            payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "result": result,
                "config": asdict(config)
            }
            
            if config.callback_data:
                payload.update(config.callback_data)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(config.callback_url, json=payload) as response:
                    if response.status >= 400:
                        self.logger.error(f"HTTP callback failed: {response.status}")
                    else:
                        self.logger.info(f"HTTP callback executed successfully")
                        
        except Exception as e:
            self.logger.error(f"Error executing HTTP callback: {e}")
    
    async def run_schedule_now(self, name: str) -> Dict[str, Any]:
        """Manually trigger a schedule immediately."""
        if name not in self.schedules:
            return {"error": "Schedule not found"}
        
        config = self.schedules[name]
        await self._execute_schedule(name, config)
        
        return {
            "message": f"Schedule '{name}' executed successfully",
            "last_run": config.last_run.isoformat() if config.last_run else None,
            "next_run": config.next_run.isoformat() if config.next_run else None
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status and statistics."""
        schedule_status = []
        
        for name, config in self.schedules.items():
            schedule_status.append({
                "name": name,
                "enabled": config.enabled,
                "interval_minutes": config.interval_minutes,
                "feed_id": config.feed_id,
                "last_run": config.last_run.isoformat() if config.last_run else None,
                "next_run": config.next_run.isoformat() if config.next_run else None,
                "has_callback": bool(config.callback_url)
            })
        
        return {
            "running": self.running,
            "total_schedules": len(self.schedules),
            "enabled_schedules": len([s for s in self.schedules.values() if s.enabled]),
            "registered_callbacks": list(self.callbacks.keys()),
            "schedules": schedule_status
        }


# Convenience functions for Discord bot integration
class DiscordRSSScheduler:
    """Discord-specific RSS scheduler wrapper."""
    
    def __init__(self, database: Database, discord_bot=None):
        """Initialize Discord RSS scheduler."""
        self.scheduler = RSSScheduler(database)
        self.discord_bot = discord_bot
        
        # Register Discord notification callback
        if discord_bot:
            self.scheduler.register_callback("discord_notify", self._discord_notification)
    
    async def _discord_notification(self, schedule_name: str, result: Dict[str, Any]):
        """Send Discord notification for RSS updates."""
        if not self.discord_bot:
            return
        
        try:
            # Import here to avoid circular imports
            import discord
            from .rss_manager import RSSBriefingFormatter
            
            # Create a simple embed for new articles
            if result.get("new_articles", 0) > 0:
                embed = discord.Embed(
                    title="📡 RSS Feed Updated",
                    description=f"Schedule '{schedule_name}' found new articles",
                    color=0x00ff00,
                    timestamp=datetime.utcnow()
                )
                
                if result.get("feed_name"):
                    embed.add_field(
                        name="Feed",
                        value=result["feed_name"],
                        inline=True
                    )
                
                embed.add_field(
                    name="New Articles",
                    value=str(result["new_articles"]),
                    inline=True
                )
                
                embed.set_footer(text="🪣 Use !rss to see the full briefing")
                
                # Send to a specific channel (you'd configure this)
                # For now, just log it
                print(f"Discord notification: {embed.to_dict()}")
        
        except Exception as e:
            print(f"Error sending Discord notification: {e}")
    
    def add_feed_schedule(
        self, 
        feed_id: int, 
        interval_minutes: int = 60, 
        max_articles: int = 10,
        webhook_url: str = None
    ) -> str:
        """Add a schedule for a specific feed."""
        name = f"feed_{feed_id}"
        config = ScheduleConfig(
            feed_id=feed_id,
            interval_minutes=interval_minutes,
            max_articles=max_articles,
            callback_url=webhook_url
        )
        return self.scheduler.add_schedule(name, config)
    
    def add_global_schedule(
        self, 
        interval_minutes: int = 240,  # 4 hours default
        max_articles: int = 5,
        webhook_url: str = None
    ) -> str:
        """Add a schedule for all feeds."""
        name = "global_rss_update"
        config = ScheduleConfig(
            feed_id=None,
            interval_minutes=interval_minutes,
            max_articles=max_articles,
            callback_url=webhook_url
        )
        return self.scheduler.add_schedule(name, config)
    
    async def start(self):
        """Start the Discord RSS scheduler."""
        await self.scheduler.start()
    
    async def stop(self):
        """Stop the Discord RSS scheduler."""
        await self.scheduler.stop()
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return self.scheduler.get_status()