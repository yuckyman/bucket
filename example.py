#!/usr/bin/env python3
"""Example usage of the bucket system."""

import asyncio
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from bucket.core import create_bucket
from bucket.models import ArticlePriority


async def main():
    """Example usage of the bucket system."""
    print("🪣 Bucket System Example")
    print("=" * 40)
    
    # Create bucket instance
    bucket = await create_bucket(
        db_path="example_bucket.db",
        output_dir="example_output",
        summarizer_type="mock"  # Use mock for testing
    )
    
    try:
        # Add some example URLs
        urls = [
            "https://httpbin.org/html",
            "https://example.com",
        ]
        
        print("\n📥 Adding URLs to bucket...")
        for url in urls:
            article = await bucket.add_url(
                url=url,
                priority=ArticlePriority.MEDIUM,
                tags=["example", "demo"]
            )
            
            if article:
                print(f"✅ Added: {article.title}")
                print(f"   Reading time: {article.reading_time} minutes")
                print(f"   Word count: {article.word_count}")
            else:
                print(f"❌ Failed to add: {url}")
        
        # Add an RSS feed
        print("\n📡 Adding RSS feed...")
        success = await bucket.add_feed(
            name="Example Feed",
            url="https://httpbin.org/xml",
            tags=["rss", "example"]
        )
        
        if success:
            print("✅ RSS feed added")
        else:
            print("❌ Failed to add RSS feed")
        
        # Generate a briefing
        print("\n📄 Generating briefing...")
        pdf_path = await bucket.generate_briefing(
            title="Example Briefing",
            days_back=7,
            tags=["example"]
        )
        
        if pdf_path:
            print(f"✅ Briefing generated: {pdf_path}")
        else:
            print("❌ Failed to generate briefing")
        
        # Show system status
        print("\n📊 System Status:")
        print(f"   Database: {bucket.db_path}")
        print(f"   Output directory: {bucket.output_dir}")
        print(f"   Summarizer: {bucket.summarizer.model_name}")
        
        print("\n🎉 Example completed successfully!")
        
    except Exception as e:
        print(f"❌ Error in example: {e}")
    
    finally:
        await bucket.close()


if __name__ == "__main__":
    asyncio.run(main())