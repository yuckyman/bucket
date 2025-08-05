"""Command-line interface for bucket system."""

import asyncio
import os
from pathlib import Path
from typing import Optional, List
import typer

# Optional rich imports
try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None
    Table = None
    Progress = None
    SpinnerColumn = None
    TextColumn = None
    Panel = None
    Text = None

# Optional dotenv import
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    load_dotenv = lambda: None

from .core import BucketCore, create_bucket
from .models import ArticlePriority, ArticleStatus

# Load environment variables
load_dotenv()

app = typer.Typer(
    name="bucket",
    help="A modular Python system for capturing, summarizing, and delivering web content",
    add_completion=False
)

console = Console() if RICH_AVAILABLE else None


@app.command()
def add(
    url: str = typer.Argument(..., help="URL to add to bucket"),
    priority: ArticlePriority = typer.Option(ArticlePriority.MEDIUM, "--priority", "-p", help="Article priority"),
    tags: Optional[List[str]] = typer.Option(None, "--tag", "-t", help="Tags for the article"),
    db_path: str = typer.Option("bucket.db", "--db", help="Database path"),
):
    """Add a URL to the bucket."""
    
    async def _add_url():
        bucket = await create_bucket(db_path=db_path)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Adding URL to bucket...", total=None)
            
            article = await bucket.add_url(url, priority, tags)
            
            if article:
                progress.update(task, description="✅ URL added successfully!")
                
                # Display article info
                table = Table(title="Article Added")
                table.add_column("Field", style="cyan")
                table.add_column("Value", style="white")
                
                table.add_row("Title", article.title)
                table.add_row("Author", article.author or "Unknown")
                table.add_row("Reading Time", f"{article.reading_time} minutes")
                table.add_row("Word Count", str(article.word_count or 0))
                table.add_row("Priority", article.priority.value)
                table.add_row("Tags", ", ".join(article.tags) if article.tags else "None")
                
                console.print(table)
            else:
                progress.update(task, description="❌ Failed to add URL")
                raise typer.Exit(1)
        
        await bucket.close()
    
    asyncio.run(_add_url())


@app.command()
def feed(
    name: str = typer.Argument(..., help="Feed name"),
    url: str = typer.Argument(..., help="RSS feed URL"),
    tags: Optional[List[str]] = typer.Option(None, "--tag", "-t", help="Tags for the feed"),
    db_path: str = typer.Option("bucket.db", "--db", help="Database path"),
):
    """Add an RSS feed to the bucket."""
    
    async def _add_feed():
        bucket = await create_bucket(db_path=db_path)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Adding RSS feed...", total=None)
            
            success = await bucket.add_feed(name, url, tags)
            
            if success:
                progress.update(task, description="✅ RSS feed added successfully!")
                console.print(f"Feed '{name}' added to bucket")
            else:
                progress.update(task, description="❌ Failed to add RSS feed")
                raise typer.Exit(1)
        
        await bucket.close()
    
    asyncio.run(_add_feed())


@app.command()
def fetch(
    db_path: str = typer.Option("bucket.db", "--db", help="Database path"),
):
    """Fetch articles from RSS feeds."""
    
    async def _fetch_feeds():
        bucket = await create_bucket(db_path=db_path)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Fetching RSS feeds...", total=None)
            
            await bucket.fetch_feeds()
            
            progress.update(task, description="✅ RSS feeds fetched!")
        
        await bucket.close()
    
    asyncio.run(_fetch_feeds())


@app.command()
def briefing(
    title: str = typer.Option("Daily Briefing", "--title", "-t", help="Briefing title"),
    days_back: int = typer.Option(7, "--days", "-d", help="Number of days to look back"),
    tags: Optional[List[str]] = typer.Option(None, "--tag", help="Filter by tags"),
    priority: Optional[ArticlePriority] = typer.Option(None, "--priority", "-p", help="Filter by priority"),
    output_dir: str = typer.Option("output", "--output", "-o", help="Output directory"),
    db_path: str = typer.Option("bucket.db", "--db", help="Database path"),
):
    """Generate a PDF briefing."""
    
    async def _generate_briefing():
        bucket = await create_bucket(db_path=db_path, output_dir=output_dir)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating briefing...", total=None)
            
            pdf_path = await bucket.generate_briefing(
                title=title,
                days_back=days_back,
                tags=tags,
                priority=priority
            )
            
            if pdf_path:
                progress.update(task, description="✅ Briefing generated!")
                console.print(f"📄 Briefing saved to: {pdf_path}")
            else:
                progress.update(task, description="❌ Failed to generate briefing")
                raise typer.Exit(1)
        
        await bucket.close()
    
    asyncio.run(_generate_briefing())


@app.command()
def list(
    status: Optional[ArticleStatus] = typer.Option(None, "--status", "-s", help="Filter by status"),
    priority: Optional[ArticlePriority] = typer.Option(None, "--priority", "-p", help="Filter by priority"),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of articles to show"),
    db_path: str = typer.Option("bucket.db", "--db", help="Database path"),
):
    """List articles in the bucket."""
    
    async def _list_articles():
        bucket = await create_bucket(db_path=db_path)
        
        # Query the database
        articles = await bucket.db.get_articles(status=status, priority=priority, limit=limit)
        
        if articles:
            table = Table(title="Articles in Bucket")
            table.add_column("ID", style="cyan")
            table.add_column("Title", style="white")
            table.add_column("Author", style="green")
            table.add_column("Status", style="yellow")
            table.add_column("Priority", style="magenta")
            table.add_column("Reading Time", style="blue")
            
            for article in articles[:limit]:
                table.add_row(
                    str(article.id),
                    article.title[:50] + "..." if len(article.title) > 50 else article.title,
                    article.author or "Unknown",
                    article.status.value,
                    article.priority.value,
                    f"{article.reading_time} min"
                )
            
            console.print(table)
        else:
            console.print("No articles found in bucket")
        
        await bucket.close()
    
    asyncio.run(_list_articles())


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    db_path: str = typer.Option("bucket.db", "--db", help="Database path"),
    discord_token: Optional[str] = typer.Option(None, "--discord", help="Discord bot token"),
):
    """Start the bucket API server."""
    
    async def _serve():
        bucket = await create_bucket(
            db_path=db_path,
            discord_token=discord_token or os.getenv("DISCORD_TOKEN")
        )
        
        console.print(Panel(
            Text("🚀 Starting Bucket API Server", style="bold green"),
            Text(f"Host: {host}\nPort: {port}\nDatabase: {db_path}"),
            title="Bucket System"
        ))
        
        try:
            await bucket.start_api_server(host=host, port=port)
        except KeyboardInterrupt:
            console.print("\n🛑 Shutting down server...")
        finally:
            await bucket.close()
    
    asyncio.run(_serve())


@app.command()
def run(
    db_path: str = typer.Option("bucket.db", "--db", help="Database path"),
    output_dir: str = typer.Option("output", "--output", "-o", help="Output directory"),
    obsidian_vault: Optional[str] = typer.Option(None, "--obsidian", help="Obsidian vault path"),
    discord_token: Optional[str] = typer.Option(None, "--discord", help="Discord bot token"),
    summarizer_type: str = typer.Option("ollama", "--summarizer", help="Summarizer type (ollama/openai/mock)"),
):
    """Run the full bucket system."""
    
    async def _run():
        bucket = await create_bucket(
            db_path=db_path,
            output_dir=output_dir,
            obsidian_vault=obsidian_vault,
            discord_token=discord_token or os.getenv("DISCORD_TOKEN"),
            summarizer_type=summarizer_type
        )
        
        console.print(Panel(
            Text("🪣 Bucket System", style="bold blue"),
            Text("Starting all services...\n" + 
                 f"Database: {db_path}\n" +
                 f"Output: {output_dir}\n" +
                 f"Discord: {'✅' if discord_token else '❌'}\n" +
                 f"Obsidian: {'✅' if obsidian_vault else '❌'}\n" +
                 f"Summarizer: {summarizer_type}"),
            title="System Status"
        ))
        
        try:
            await bucket.run()
        except KeyboardInterrupt:
            console.print("\n🛑 Shutting down bucket system...")
        finally:
            await bucket.close()
    
    asyncio.run(_run())


@app.command()
def init(
    db_path: str = typer.Option("bucket.db", "--db", help="Database path"),
    output_dir: str = typer.Option("output", "--output", "-o", help="Output directory"),
):
    """Initialize the bucket system."""
    
    async def _init():
        bucket = await create_bucket(db_path=db_path, output_dir=output_dir)
        
        console.print("✅ Bucket system initialized!")
        console.print(f"Database: {db_path}")
        console.print(f"Output directory: {output_dir}")
        
        await bucket.close()
    
    asyncio.run(_init())


if __name__ == "__main__":
    app()