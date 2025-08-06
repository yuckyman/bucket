"""Configuration management for bucket system."""

import os
from pathlib import Path
from typing import Optional

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, skip


class Config:
    """Configuration settings for bucket system."""
    
    def __init__(self):
        # Database configuration
        self.db_path = os.getenv("BUCKET_DB_PATH", "bucket.db")
        
        # API configuration
        self.api_host = os.getenv("BUCKET_API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("BUCKET_API_PORT", "8000"))
        
        # Hugo site configuration
        self.hugo_site_path = os.getenv("BUCKET_HUGO_SITE_PATH", None)
        
        # Output directories
        self.output_dir = os.getenv("BUCKET_OUTPUT_DIR", "output")
        
        # Ensure paths are absolute
        if self.hugo_site_path:
            self.hugo_site_path = str(Path(self.hugo_site_path).resolve())
        
        self.db_path = str(Path(self.db_path).resolve())
        self.output_dir = str(Path(self.output_dir).resolve())
    
    def get_hugo_site_path(self) -> Optional[str]:
        """Get the Hugo site path, with fallback logic."""
        if self.hugo_site_path and Path(self.hugo_site_path).exists():
            return self.hugo_site_path
        
        # Fallback: look for common hugo site locations
        current_dir = Path.cwd()
        
        # Check if we're in a hugo site directory
        if (current_dir / "config.toml").exists() or (current_dir / "hugo.toml").exists():
            return str(current_dir)
        
        # Check for subdirectories with hugo sites
        for subdir in ["blog", "site", "hugo", "spillyourgutsonline-blog"]:
            potential_path = current_dir / subdir
            if potential_path.exists() and (
                (potential_path / "config.toml").exists() or 
                (potential_path / "hugo.toml").exists()
            ):
                return str(potential_path)
        
        # Check parent directory
        parent_dir = current_dir.parent
        for subdir in ["blog", "site", "hugo", "spillyourgutsonline-blog"]:
            potential_path = parent_dir / subdir
            if potential_path.exists() and (
                (potential_path / "config.toml").exists() or 
                (potential_path / "hugo.toml").exists()
            ):
                return str(potential_path)
        
        return None
    
    def validate_hugo_site(self, path: str) -> bool:
        """Validate that a path contains a valid Hugo site."""
        hugo_path = Path(path)
        return (
            hugo_path.exists() and
            hugo_path.is_dir() and
            (
                (hugo_path / "config.toml").exists() or
                (hugo_path / "hugo.toml").exists() or
                (hugo_path / "config.yaml").exists() or
                (hugo_path / "config.yml").exists()
            )
        )


# Global config instance
config = Config()