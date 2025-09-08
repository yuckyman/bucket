#!/usr/bin/env python3
"""Run duplicate cleanup once. Designed for CI (GitHub Actions)."""

import asyncio
import os
import sys

# Ensure project root is on path when executed from CI
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from bucket.database import Database  # lightweight import
from bucket.rss_manager import RSSManager  # contains cleanup logic


async def main() -> int:
    db_path = os.getenv("BUCKET_DB_PATH", "bucket.db")
    days_back = int(os.getenv("BUCKET_CLEANUP_DAYS", "30"))

    db = Database(db_path)
    db.initialize(async_mode=True)
    await db.create_tables()

    manager = RSSManager(db)
    result = await manager.cleanup_duplicates(days_back=days_back)
    print(result)

    await db.close()

    # Treat failure as non-zero for CI visibility
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))


