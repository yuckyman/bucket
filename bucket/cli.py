#!/usr/bin/env python3
"""Command-line interface for bucket system."""

import sys
import argparse
import asyncio
from pathlib import Path

from .config import config
from .api import run_api_server
from .hugo_integration import HugoContentGenerator


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Bucket RSS to Hugo integration system")
    
    # Global options
    parser.add_argument("--hugo-site", help="Path to Hugo site directory")
    parser.add_argument("--db-path", help="Path to database file")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # API server command
    api_parser = subparsers.add_parser("serve", help="Start the API server")
    api_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    api_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    api_parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    # Process feeds command
    process_parser = subparsers.add_parser("process", help="Process RSS feeds and generate reports")
    process_parser.add_argument("--max-articles", type=int, default=5, help="Max articles per feed")
    process_parser.add_argument("--build", action="store_true", help="Build Hugo site after processing")
    
    # Build Hugo site command
    build_parser = subparsers.add_parser("build", help="Build the Hugo site")
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Show configuration")
    
    args = parser.parse_args()
    
    # Update config with CLI arguments
    if args.hugo_site:
        import os
        os.environ["BUCKET_HUGO_SITE_PATH"] = str(Path(args.hugo_site).resolve())
        # Reload config
        from . import config as config_module
        config_module.config = config_module.Config()
    
    if args.db_path:
        import os
        os.environ["BUCKET_DB_PATH"] = str(Path(args.db_path).resolve())
        # Reload config
        from . import config as config_module
        config_module.config = config_module.Config()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == "serve":
            print(f"🚀 Starting bucket API server...")
            print(f"   Host: {args.host}")
            print(f"   Port: {args.port}")
            print(f"   Database: {config.db_path}")
            if config.get_hugo_site_path():
                print(f"   Hugo site: {config.get_hugo_site_path()}")
            
            run_api_server(host=args.host, port=args.port, reload=args.reload)
            
        elif args.command == "process":
            print(f"📡 Processing RSS feeds...")
            asyncio.run(process_feeds_command(args))
            
        elif args.command == "build":
            print(f"🏗️  Building Hugo site...")
            asyncio.run(build_site_command())
            
        elif args.command == "config":
            show_config()
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


async def process_feeds_command(args):
    """Process RSS feeds command."""
    from .database import Database
    
    try:
        # Initialize Hugo generator
        hugo_generator = HugoContentGenerator()
        
        # Initialize database
        db = Database(config.db_path)
        db.initialize(async_mode=True)
        await db.create_tables()
        
        # Process feeds
        result = await hugo_generator.process_feeds_for_read_later(
            db, max_articles_per_feed=args.max_articles
        )
        
        if result["success"]:
            print(f"✅ {result['message']}")
            
            if args.build and result["report_created"]:
                print("🏗️  Building Hugo site...")
                build_result = await hugo_generator.build_hugo_site()
                
                if build_result["success"]:
                    print(f"✅ {build_result['message']}")
                else:
                    print(f"❌ Hugo build failed: {build_result['message']}")
        else:
            print(f"❌ {result['message']}")
            
    except Exception as e:
        print(f"❌ Error processing feeds: {e}")


async def build_site_command():
    """Build Hugo site command."""
    try:
        hugo_generator = HugoContentGenerator()
        result = await hugo_generator.build_hugo_site()
        
        if result["success"]:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")
            
    except Exception as e:
        print(f"❌ Error building site: {e}")


def show_config():
    """Show current configuration."""
    print("🔧 Current Configuration:")
    print(f"   Database path: {config.db_path}")
    print(f"   API host: {config.api_host}")
    print(f"   API port: {config.api_port}")
    print(f"   Output directory: {config.output_dir}")
    
    hugo_path = config.get_hugo_site_path()
    if hugo_path:
        print(f"   Hugo site: {hugo_path}")
        print(f"   Hugo site valid: {config.validate_hugo_site(hugo_path)}")
    else:
        print("   Hugo site: Not found")
    
    print("\n🌍 Environment Variables:")
    import os
    env_vars = [
        "BUCKET_DB_PATH",
        "BUCKET_API_HOST", 
        "BUCKET_API_PORT",
        "BUCKET_HUGO_SITE_PATH",
        "BUCKET_OUTPUT_DIR"
    ]
    
    for var in env_vars:
        value = os.getenv(var, "Not set")
        print(f"   {var}: {value}")


if __name__ == "__main__":
    main()