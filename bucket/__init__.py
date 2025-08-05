"""Bucket - A modular Python system for capturing, summarizing, and delivering web content."""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .core import BucketCore
from .models import Article, Feed, Summary
from .database import Database

__all__ = ["BucketCore", "Article", "Feed", "Summary", "Database"]