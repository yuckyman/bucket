#!/usr/bin/env python3
"""Simple test script for bucket system."""

import asyncio
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from bucket.core import create_bucket
from bucket.fetcher import ContentFetcher
from bucket.summarizer import SummarizerFactory
from bucket.pdf_generator import PDFGenerator


async def test_fetcher():
    """Test the content fetcher."""
    print("🧪 Testing content fetcher...")
    
    fetcher = ContentFetcher()
    test_url = "https://httpbin.org/html"
    
    try:
        async with fetcher:
            article = await fetcher.fetch_article(test_url)
        
        if article:
            print(f"✅ Fetched article: {article.title}")
            print(f"   Author: {article.author}")
            print(f"   Word count: {article.word_count}")
            print(f"   Reading time: {article.reading_time} minutes")
            return article
        else:
            print("❌ Failed to fetch article")
            return None
            
    except Exception as e:
        print(f"❌ Error testing fetcher: {e}")
        return None


async def test_summarizer():
    """Test the summarizer."""
    print("\n🧪 Testing summarizer...")
    
    try:
        # Test with mock summarizer
        summarizer = SummarizerFactory.create_summarizer("mock")
        
        # Create a test article
        from bucket.models import Article
        test_article = Article(
            url="https://example.com/test",
            title="Test Article",
            cleaned_content="This is a test article with some content to summarize. It contains multiple sentences to test the summarization functionality.",
            word_count=20,
            reading_time=1
        )
        
        async with summarizer:
            summary = await summarizer.summarize(test_article)
        
        if summary:
            print(f"✅ Generated summary: {summary.content}")
            print(f"   Model used: {summary.model_used}")
            return summary
        else:
            print("❌ Failed to generate summary")
            return None
            
    except Exception as e:
        print(f"❌ Error testing summarizer: {e}")
        return None


async def test_pdf_generator():
    """Test the PDF generator."""
    print("\n🧪 Testing PDF generator...")
    
    try:
        generator = PDFGenerator()
        
        # Create test articles
        from bucket.models import Article
        test_articles = [
            Article(
                url="https://example.com/article1",
                title="First Test Article",
                author="Test Author",
                cleaned_content="This is the first test article with some content.",
                word_count=50,
                reading_time=2,
                tags=["test", "demo"]
            ),
            Article(
                url="https://example.com/article2",
                title="Second Test Article",
                author="Another Author",
                cleaned_content="This is the second test article with different content.",
                word_count=75,
                reading_time=3,
                tags=["test", "example"]
            )
        ]
        
        pdf_path = await generator.generate_briefing(
            articles=test_articles,
            title="Test Briefing",
            date=None
        )
        
        if pdf_path and Path(pdf_path).exists():
            print(f"✅ Generated PDF: {pdf_path}")
            print(f"   File size: {Path(pdf_path).stat().st_size} bytes")
            return pdf_path
        else:
            print("❌ Failed to generate PDF")
            return None
            
    except Exception as e:
        print(f"❌ Error testing PDF generator: {e}")
        return None


async def test_bucket_core():
    """Test the core bucket system."""
    print("\n🧪 Testing bucket core...")
    
    try:
        bucket = await create_bucket(
            db_path="test_bucket.db",
            output_dir="test_output",
            summarizer_type="mock"
        )
        
        print("✅ Bucket core initialized successfully")
        
        # Test adding a URL
        test_url = "https://httpbin.org/html"
        article = await bucket.add_url(test_url)
        
        if article:
            print(f"✅ Added article: {article.title}")
        else:
            print("❌ Failed to add article")
        
        await bucket.close()
        return True
        
    except Exception as e:
        print(f"❌ Error testing bucket core: {e}")
        return False


async def main():
    """Run all tests."""
    print("🚀 Starting bucket system tests...\n")
    
    results = []
    
    # Test fetcher
    fetcher_result = await test_fetcher()
    results.append(("Fetcher", fetcher_result is not None))
    
    # Test summarizer
    summarizer_result = await test_summarizer()
    results.append(("Summarizer", summarizer_result is not None))
    
    # Test PDF generator
    pdf_result = await test_pdf_generator()
    results.append(("PDF Generator", pdf_result is not None))
    
    # Test bucket core
    core_result = await test_bucket_core()
    results.append(("Bucket Core", core_result))
    
    # Print results
    print("\n📊 Test Results:")
    print("=" * 40)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:<15} {status}")
        if success:
            passed += 1
    
    print("=" * 40)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Bucket system is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)