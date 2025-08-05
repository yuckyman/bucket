#!/usr/bin/env python3
"""Minimal test to verify bucket system structure."""

import sys
from pathlib import Path

def test_file_structure():
    """Test that all required files exist."""
    print("🧪 Testing file structure...")
    
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


def test_package_structure():
    """Test that the bucket package can be imported."""
    print("\n🧪 Testing package structure...")
    
    try:
        # Test basic package import
        import bucket
        print("✅ Bucket package imported successfully")
        
        # Test that __init__.py has the right exports
        if hasattr(bucket, '__version__'):
            print(f"✅ Version: {bucket.__version__}")
        else:
            print("⚠️  No version found")
        
        if hasattr(bucket, '__author__'):
            print(f"✅ Author: {bucket.__author__}")
        else:
            print("⚠️  No author found")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_file_contents():
    """Test that key files have expected content."""
    print("\n🧪 Testing file contents...")
    
    # Check pyproject.toml has bucket name
    try:
        with open("pyproject.toml", "r") as f:
            content = f.read()
            if "name = \"bucket\"" in content:
                print("✅ pyproject.toml has correct name")
            else:
                print("❌ pyproject.toml missing bucket name")
                return False
    except Exception as e:
        print(f"❌ Error reading pyproject.toml: {e}")
        return False
    
    # Check README has bucket content
    try:
        with open("README.md", "r") as f:
            content = f.read()
            if "Bucket" in content and "🪣" in content:
                print("✅ README.md has bucket content")
            else:
                print("❌ README.md missing bucket content")
                return False
    except Exception as e:
        print(f"❌ Error reading README.md: {e}")
        return False
    
    # Check bucket __init__.py has version
    try:
        with open("bucket/__init__.py", "r") as f:
            content = f.read()
            if "__version__" in content:
                print("✅ bucket/__init__.py has version")
            else:
                print("❌ bucket/__init__.py missing version")
                return False
    except Exception as e:
        print(f"❌ Error reading bucket/__init__.py: {e}")
        return False
    
    return True


def main():
    """Run all tests."""
    print("🚀 Starting minimal bucket system tests...\n")
    
    tests = [
        ("File Structure", test_file_structure),
        ("Package Structure", test_package_structure),
        ("File Contents", test_file_contents)
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
        print("4. Start the API: bucket serve")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)