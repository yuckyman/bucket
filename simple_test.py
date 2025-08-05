#!/usr/bin/env python3
"""Simple test to verify bucket system structure."""

import sys
from pathlib import Path

def test_imports():
    """Test that all modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        # Test basic imports
        from bucket import __version__, __author__
        print(f"✅ Bucket package: v{__version__} by {__author__}")
        
        from bucket.models import Article, ArticleStatus, ArticlePriority
        print("✅ Models imported successfully")
        
        from bucket.database import Database
        print("✅ Database imported successfully")
        
        from bucket.fetcher import ContentFetcher
        print("✅ Fetcher imported successfully")
        
        from bucket.summarizer import SummarizerFactory
        print("✅ Summarizer imported successfully")
        
        from bucket.pdf_generator import PDFGenerator
        print("✅ PDF Generator imported successfully")
        
        from bucket.discord_bot import DiscordManager
        print("✅ Discord Bot imported successfully")
        
        from bucket.api import create_api_app
        print("✅ API imported successfully")
        
        from bucket.cli import app
        print("✅ CLI imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_file_structure():
    """Test that all required files exist."""
    print("\n🧪 Testing file structure...")
    
    required_files = [
        "bucket/__init__.py",
        "bucket/models.py",
        "bucket/database.py",
        "bucket/fetcher.py",
        "bucket/summarizer.py",
        "bucket/pdf_generator.py",
        "bucket/discord_bot.py",
        "bucket/api.py",
        "bucket/cli.py",
        "bucket/core.py",
        "pyproject.toml",
        "README.md",
        ".env.example",
        "docker-compose.yml",
        "Dockerfile"
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n⚠️  Missing files: {missing_files}")
        return False
    else:
        print("\n✅ All required files present")
        return True


def test_basic_functionality():
    """Test basic functionality without external dependencies."""
    print("\n🧪 Testing basic functionality...")
    
    try:
        # Test model creation
        from bucket.models import Article, ArticleStatus, ArticlePriority
        
        article = Article(
            url="https://example.com/test",
            title="Test Article",
            status=ArticleStatus.PENDING,
            priority=ArticlePriority.MEDIUM
        )
        
        print(f"✅ Created article: {article.title}")
        print(f"   Status: {article.status}")
        print(f"   Priority: {article.priority}")
        
        # Test database initialization
        from bucket.database import Database
        
        db = Database("test.db")
        print("✅ Database instance created")
        
        # Test summarizer factory
        from bucket.summarizer import SummarizerFactory
        
        summarizer = SummarizerFactory.create_summarizer("mock")
        print("✅ Mock summarizer created")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing functionality: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Starting bucket system structure tests...\n")
    
    tests = [
        ("Imports", test_imports),
        ("File Structure", test_file_structure),
        ("Basic Functionality", test_basic_functionality)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        success = test_func()
        results.append((test_name, success))
    
    # Print results
    print("\n📊 Test Results:")
    print("=" * 40)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:<20} {status}")
        if success:
            passed += 1
    
    print("=" * 40)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Bucket system structure is correct.")
        print("\n📝 Next steps:")
        print("1. Install dependencies: pip install -e .")
        print("2. Run full tests: python test_bucket.py")
        print("3. Try the CLI: bucket --help")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)