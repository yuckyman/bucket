#!/usr/bin/env python3
"""
PDF Newsletter Generator for Bucket
Generates beautiful PDF newsletters from RSS article data.
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any

# Try to import required dependencies
try:
    import jinja2
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    print("❌ Jinja2 not available. Install with: pip install jinja2")
    sys.exit(1)

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    print("❌ WeasyPrint not available. Install with: pip install weasyprint")
    sys.exit(1)


class PDFNewsletterGenerator:
    """Generates PDF newsletters from article data."""
    
    def __init__(self, template_dir: str = "templates", output_dir: str = "outputs/newsletters"):
        self.template_dir = Path(template_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup Jinja2 environment
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_dir),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
    
    def load_articles(self, articles_file: str = "data/articles.json", days_back: int = 7) -> List[Dict[str, Any]]:
        """Load and filter articles from JSON file."""
        if not os.path.exists(articles_file):
            print(f"❌ Articles file not found: {articles_file}")
            return []
        
        with open(articles_file, 'r') as f:
            articles = json.load(f)
        
        # Filter articles by date
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        recent_articles = []
        
        for article in articles:
            try:
                article_date = datetime.fromisoformat(article['created_at'].replace('Z', '+00:00'))
                if article_date >= cutoff_date:
                    recent_articles.append(article)
            except Exception as e:
                # If date parsing fails, include the article
                print(f"⚠️  Date parsing failed for article: {article.get('title', 'Unknown')} - {e}")
                recent_articles.append(article)
        
        # Sort by date (newest first)
        recent_articles.sort(key=lambda x: x['created_at'], reverse=True)
        
        return recent_articles
    
    def load_feeds(self, feeds_file: str = "data/feeds.json") -> List[Dict[str, Any]]:
        """Load feeds data."""
        if not os.path.exists(feeds_file):
            return []
        
        with open(feeds_file, 'r') as f:
            return json.load(f)
    
    def generate_pdf_newsletter(
        self, 
        articles: List[Dict[str, Any]], 
        title: str = None,
        days_back: int = 7
    ) -> str:
        """Generate a PDF newsletter from articles."""
        if not articles:
            raise ValueError("No articles provided for newsletter")
        
        # Generate title if not provided
        if not title:
            date_str = datetime.now(timezone.utc).strftime('%B %d, %Y')
            title = f"Daily Briefing - {date_str}"
        
        # Calculate stats
        total_words = sum(article.get('word_count', 0) for article in articles)
        total_time = sum(article.get('reading_time', 0) for article in articles)
        unique_sources = list(set(article.get('source', 'Unknown') for article in articles))
        
        # Prepare template data
        template_data = {
            "title": title,
            "date": datetime.now(timezone.utc),
            "articles": articles,
            "total_words": total_words,
            "total_time": total_time,
            "unique_sources": unique_sources,
            "days_back": days_back
        }
        
        # Render template
        template = self.jinja_env.get_template("newsletter.html")
        html_content = template.render(**template_data)
        
        # Generate PDF filename
        date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        filename = f"newsletter-{date_str}.pdf"
        output_path = self.output_dir / filename
        
        # Create PDF from HTML
        print(f"🔄 Generating PDF: {filename}")
        html_doc = HTML(string=html_content)
        html_doc.write_pdf(output_path)
        
        print(f"✅ PDF generated successfully: {output_path}")
        return str(output_path)
    
    def generate_newsletter_data(
        self, 
        articles: List[Dict[str, Any]], 
        feeds: List[Dict[str, Any]] = None,
        days_back: int = 7
    ) -> Dict[str, Any]:
        """Generate newsletter data structure (for API compatibility)."""
        total_words = sum(article.get('word_count', 0) for article in articles)
        total_time = sum(article.get('reading_time', 0) for article in articles)
        unique_sources = list(set(article.get('source', 'Unknown') for article in articles))
        
        newsletter_data = {
            "date": datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            "title": f"Daily Briefing - {datetime.now(timezone.utc).strftime('%B %d, %Y')}",
            "days_back": days_back,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "stats": {
                "total_articles": len(articles),
                "total_feeds": len(feeds) if feeds else 0,
                "active_feeds": len([f for f in feeds if f.get('is_active', True)]) if feeds else 0,
                "total_reading_time": total_time,
                "total_words": total_words,
                "unique_sources": len(unique_sources)
            },
            "articles": articles,
            "feeds": feeds or [],
            "unique_sources": unique_sources
        }
        
        return newsletter_data


def main():
    """Main function to generate PDF newsletter."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate PDF newsletter from RSS articles')
    parser.add_argument('--days-back', type=int, default=7, help='Number of days to include (default: 7)')
    parser.add_argument('--articles-file', default='data/articles.json', help='Path to articles JSON file')
    parser.add_argument('--feeds-file', default='data/feeds.json', help='Path to feeds JSON file')
    parser.add_argument('--output-dir', default='outputs/newsletters', help='Output directory for PDFs')
    parser.add_argument('--template-dir', default='templates', help='Template directory')
    parser.add_argument('--title', help='Custom newsletter title')
    parser.add_argument('--save-json', action='store_true', help='Also save newsletter data as JSON')
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = PDFNewsletterGenerator(
        template_dir=args.template_dir,
        output_dir=args.output_dir
    )
    
    # Load data
    print(f"📖 Loading articles from {args.articles_file}...")
    articles = generator.load_articles(args.articles_file, args.days_back)
    
    if not articles:
        print("❌ No articles found!")
        return 1
    
    print(f"📡 Loading feeds from {args.feeds_file}...")
    feeds = generator.load_feeds(args.feeds_file)
    
    print(f"📊 Found {len(articles)} articles from {len(feeds)} feeds")
    
    # Generate newsletter data
    newsletter_data = generator.generate_newsletter_data(articles, feeds, args.days_back)
    
    # Save JSON if requested
    if args.save_json:
        json_filename = f"newsletter-{newsletter_data['date']}.json"
        json_path = Path(args.output_dir) / json_filename
        with open(json_path, 'w') as f:
            json.dump(newsletter_data, f, indent=2)
        print(f"💾 Newsletter data saved: {json_path}")
    
    # Generate PDF
    try:
        pdf_path = generator.generate_pdf_newsletter(
            articles, 
            title=args.title,
            days_back=args.days_back
        )
        
        # Print summary
        stats = newsletter_data['stats']
        print(f"\n🎉 Newsletter generated successfully!")
        print(f"📄 PDF: {pdf_path}")
        print(f"📊 Stats: {stats['total_articles']} articles, {stats['total_words']} words, {stats['total_reading_time']} min read")
        print(f"📡 Sources: {stats['unique_sources']} unique feeds")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
