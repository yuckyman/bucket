"""Bucket - A modular Python system for capturing, summarizing, and delivering web content."""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Delayed imports to avoid heavy optional dependencies at package import time
from .models import Article, Feed, Summary  # lightweight
from .database import Database  # lightweight

# Note: BucketCore (and thus PDF generator deps) is intentionally NOT imported at
# package import time to prevent importing optional heavy dependencies (e.g.,
# WeasyPrint) when only database/rss functionality is needed. Import from
# bucket.core directly if BucketCore is required.
__all__ = ["Article", "Feed", "Summary", "Database"]