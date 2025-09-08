"""PDF generation for bucket briefings."""

import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
# Optional imports
try:
    import jinja2
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    jinja2 = None

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    HTML = None
    CSS = None
from .models import Article, Summary, ArticleStatus


class PDFGenerator:
    """Generates PDF briefings from articles and summaries."""
    
    def __init__(self, template_dir: str = "templates", output_dir: str = "output"):
        self.template_dir = Path(template_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup Jinja2 environment
        if JINJA2_AVAILABLE:
            self.jinja_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(self.template_dir),
                autoescape=jinja2.select_autoescape(['html', 'xml'])
            )
        else:
            self.jinja_env = None
        
        # Create default template if it doesn't exist
        self._create_default_template()
    
    def _create_default_template(self):
        """Create default HTML template if it doesn't exist."""
        template_path = self.template_dir / "briefing.html"
        if not template_path.exists():
            template_path.parent.mkdir(parents=True, exist_ok=True)
            
            template_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        @page {
            size: A4;
            margin: 2cm;
            @top-center {
                content: "{{ title }}";
                font-size: 10pt;
                color: #666;
            }
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10pt;
                color: #666;
            }
        }
        
        body {
            font-family: 'Georgia', serif;
            line-height: 1.6;
            color: #333;
            max-width: 100%;
            margin: 0;
            padding: 0;
        }
        
        .header {
            text-align: center;
            margin-bottom: 2em;
            border-bottom: 2px solid #333;
            padding-bottom: 1em;
        }
        
        .header h1 {
            font-size: 24pt;
            margin: 0;
            color: #2c3e50;
        }
        
        .header .date {
            font-size: 12pt;
            color: #7f8c8d;
            margin-top: 0.5em;
        }
        
        .article {
            margin-bottom: 2em;
            page-break-inside: avoid;
            border-left: 4px solid #3498db;
            padding-left: 1em;
        }
        
        .article-header {
            margin-bottom: 1em;
        }
        
        .article-title {
            font-size: 14pt;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 0.5em;
        }
        
        .article-meta {
            font-size: 10pt;
            color: #7f8c8d;
            margin-bottom: 1em;
        }
        
        .article-summary {
            font-size: 11pt;
            line-height: 1.5;
            margin-bottom: 1em;
            background-color: #f8f9fa;
            padding: 1em;
            border-radius: 4px;
        }
        
        .article-content {
            font-size: 10pt;
            line-height: 1.4;
            color: #555;
        }
        
        .tags {
            margin-top: 1em;
        }
        
        .tag {
            display: inline-block;
            background-color: #e1f5fe;
            color: #0277bd;
            padding: 0.2em 0.6em;
            border-radius: 12px;
            font-size: 8pt;
            margin-right: 0.5em;
            margin-bottom: 0.5em;
        }
        
        .priority-high {
            border-left-color: #e74c3c;
        }
        
        .priority-medium {
            border-left-color: #f39c12;
        }
        
        .priority-low {
            border-left-color: #27ae60;
        }
        
        .stats {
            text-align: center;
            margin: 2em 0;
            padding: 1em;
            background-color: #ecf0f1;
            border-radius: 4px;
        }
        
        .stats-item {
            display: inline-block;
            margin: 0 1em;
            font-size: 10pt;
        }
        
        .stats-number {
            font-weight: bold;
            color: #2c3e50;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <div class="date">{{ date }}</div>
    </div>
    
    <div class="stats">
        <div class="stats-item">
            <span class="stats-number">{{ articles|length }}</span> articles
        </div>
        <div class="stats-item">
            <span class="stats-number">{{ total_words }}</span> words
        </div>
        <div class="stats-item">
            <span class="stats-number">{{ total_time }}</span> min read
        </div>
    </div>
    
    {% for article in articles %}
    <div class="article priority-{{ article.priority.value }}">
        <div class="article-header">
            <div class="article-title">{{ article.title }}</div>
            <div class="article-meta">
                {% if article.author %}By {{ article.author }} • {% endif %}
                {% if article.published_date %}{{ article.published_date.strftime('%B %d, %Y') }} • {% endif %}
                {{ article.word_count }} words • {{ article.reading_time }} min read
                {% if article.source %}• {{ article.source }}{% endif %}
            </div>
        </div>
        
        {% if article.summary %}
        <div class="article-summary">
            <strong>Summary:</strong> {{ article.summary.content }}
        </div>
        {% endif %}
        
        <div class="article-content">
            {{ article.cleaned_content[:1000] }}{% if article.cleaned_content|length > 1000 %}...{% endif %}
        </div>
        
        {% if article.tags %}
        <div class="tags">
            {% for tag in article.tags %}
            <span class="tag">{{ tag }}</span>
            {% endfor %}
        </div>
        {% endif %}
    </div>
    {% endfor %}
</body>
</html>"""
            
            with open(template_path, "w") as f:
                f.write(template_content)
    
    async def generate_briefing(
        self,
        articles: List[Article],
        title: str = "Daily Briefing",
        date: Optional[datetime] = None,
        include_summaries: bool = True
    ) -> str:
        """Generate a PDF briefing from articles."""
        if not articles:
            raise ValueError("No articles provided for briefing")
        
        # Process articles to ensure priority is properly set
        processed_articles = []
        for article in articles:
            # Ensure priority is properly set for template rendering
            if hasattr(article, 'priority') and article.priority:
                # If priority is a string, convert to enum
                if isinstance(article.priority, str):
                    from .models import ArticlePriority
                    try:
                        article.priority = ArticlePriority(article.priority)
                    except ValueError:
                        article.priority = ArticlePriority.MEDIUM
                # If priority is already an enum, ensure it has .value
                elif hasattr(article.priority, 'value'):
                    pass  # Already correct
                else:
                    from .models import ArticlePriority
                    article.priority = ArticlePriority.MEDIUM
            else:
                from .models import ArticlePriority
                article.priority = ArticlePriority.MEDIUM
            
            processed_articles.append(article)
        
        # Calculate stats
        total_words = sum(article.word_count or 0 for article in processed_articles)
        total_time = sum(article.reading_time or 0 for article in processed_articles)
        
        # Prepare template data
        template_data = {
            "title": title,
            "date": date or datetime.now(),
            "articles": processed_articles,
            "total_words": total_words,
            "total_time": total_time
        }
        
        # Render template
        if not JINJA2_AVAILABLE:
            raise RuntimeError("Jinja2 not available for template rendering")
            
        template = self.jinja_env.get_template("briefing.html")
        html_content = template.render(**template_data)
        
        # Generate PDF
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"briefing_{timestamp}.pdf"
        output_path = self.output_dir / filename
        
        # Create PDF from HTML
        if not WEASYPRINT_AVAILABLE:
            raise RuntimeError("WeasyPrint not available for PDF generation")
            
        html_doc = HTML(string=html_content, base_url=str(self.template_dir.resolve()))
        html_doc.write_pdf(str(output_path))
        
        return str(output_path)
    
    async def _attach_summaries(self, articles: List[Article]) -> List[Dict[str, Any]]:
        """Attach summaries to articles."""
        # This would typically query the database for summaries
        # For now, we'll return articles as-is, but ensure priority is properly formatted
        processed_articles = []
        for article in articles:
            # Ensure priority is properly set for template rendering
            if hasattr(article, 'priority') and article.priority:
                # If priority is a string, convert to enum
                if isinstance(article.priority, str):
                    from .models import ArticlePriority
                    try:
                        article.priority = ArticlePriority(article.priority)
                    except ValueError:
                        article.priority = ArticlePriority.MEDIUM
                # If priority is already an enum, ensure it has .value
                elif hasattr(article.priority, 'value'):
                    pass  # Already correct
                else:
                    from .models import ArticlePriority
                    article.priority = ArticlePriority.MEDIUM
            else:
                from .models import ArticlePriority
                article.priority = ArticlePriority.MEDIUM
            
            processed_articles.append({"article": article, "summary": None})
        
        return processed_articles
    
    def generate_markdown_briefing(
        self,
        articles: List[Article],
        title: str = "Daily Briefing",
        date: Optional[datetime] = None
    ) -> str:
        """Generate a markdown briefing."""
        if not articles:
            raise ValueError("No articles provided for briefing")
        
        date_str = (date or datetime.now()).strftime("%B %d, %Y")
        
        markdown = f"# {title}\n\n"
        markdown += f"*Generated on {date_str}*\n\n"
        
        # Stats
        total_words = sum(article.word_count or 0 for article in articles)
        total_time = sum(article.reading_time or 0 for article in articles)
        markdown += f"**Stats:** {len(articles)} articles, {total_words} words, {total_time} min read\n\n"
        
        # Articles
        for i, article in enumerate(articles, 1):
            markdown += f"## {i}. {article.title}\n\n"
            
            if article.author:
                markdown += f"**Author:** {article.author}\n"
            if article.published_date:
                markdown += f"**Published:** {article.published_date.strftime('%B %d, %Y')}\n"
            if article.source:
                markdown += f"**Source:** {article.source}\n"
            
            markdown += f"**Reading time:** {article.reading_time or 0} minutes\n\n"
            
            if article.tags:
                markdown += f"**Tags:** {', '.join(article.tags)}\n\n"
            
            if article.cleaned_content:
                # Truncate content for markdown
                content = article.cleaned_content[:500]
                if len(article.cleaned_content) > 500:
                    content += "..."
                markdown += f"{content}\n\n"
            
            markdown += f"[Read full article]({article.url})\n\n"
            markdown += "---\n\n"
        
        return markdown


class ObsidianExporter:
    """Exports articles to Obsidian vault with Johnny.Decimal schema."""
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.vault_path.mkdir(exist_ok=True)
    
    def export_article(self, article: Article, category: str = "10.00") -> str:
        """Export an article to Obsidian with Johnny.Decimal schema."""
        # Create category directory
        category_path = self.vault_path / category
        category_path.mkdir(exist_ok=True)
        
        # Create filename
        safe_title = "".join(c for c in article.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:50]  # Limit length
        filename = f"{datetime.now().strftime('%Y%m%d')}_{safe_title}.md"
        file_path = category_path / filename
        
        # Create markdown content
        content = f"# {article.title}\n\n"
        content += f"**URL:** {article.url}\n"
        content += f"**Author:** {article.author or 'Unknown'}\n"
        if article.published_date:
            content += f"**Published:** {article.published_date.strftime('%B %d, %Y')}\n"
        content += f"**Reading time:** {article.reading_time or 0} minutes\n"
        content += f"**Word count:** {article.word_count or 0}\n\n"
        
        if article.tags:
            content += f"**Tags:** {', '.join(article.tags)}\n\n"
        
        content += "## Summary\n\n"
        # Placeholder for summary
        content += "*Summary will be added here*\n\n"
        
        content += "## Content\n\n"
        if article.cleaned_content:
            content += article.cleaned_content
        else:
            content += "*Content not available*\n"
        
        # Write file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return str(file_path)