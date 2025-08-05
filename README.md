# Bucket 🪣

A modular Python system for capturing, summarizing, and delivering web content in a frictionless "read-later" pipeline. Designed to support your personal knowledge workflows, bucket connects Discord, RSS feeds, and local databases to generate clean, readable briefings—ultimately served to a reMarkable tablet or accessed via API on demand.

## 🌟 Features

- **Web Content Capture**: Fetch and clean articles from URLs or RSS feeds
- **AI Summarization**: Generate concise summaries using Ollama or OpenAI
- **PDF Briefings**: Create beautiful, formatted PDF reports for offline reading
- **Discord Integration**: Add articles via Discord bot commands
- **REST API**: Full API for automation and integration
- **Obsidian Export**: Sync articles to Obsidian vault with Johnny.Decimal schema
- **CLI Interface**: Easy command-line control with rich output
- **Scheduled Tasks**: Automatic RSS fetching and briefing generation
- **reMarkable Ready**: PDFs optimized for tablet reading

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/bucket.git
cd bucket

# Install dependencies
pip install -e .

# Initialize the system
bucket init
```

### Basic Usage

```bash
# Add a URL to your bucket
bucket add "https://example.com/article"

# Add an RSS feed
bucket feed "Tech News" "https://example.com/feed.xml" --tag tech

# Generate a daily briefing
bucket briefing --title "Morning Briefing" --days 7

# Start the API server
bucket serve --port 8000

# Run the full system
bucket run --discord YOUR_TOKEN --obsidian /path/to/vault
```

## 📋 Requirements

- Python 3.9+
- SQLite (included)
- Ollama (for local LLM summarization) or OpenAI API key
- Discord bot token (optional)
- Obsidian vault (optional)

## 🏗️ Architecture

```
bucket/
├── core.py          # Main orchestrator
├── models.py        # Data models
├── database.py      # Database management
├── fetcher.py       # Web content fetching
├── summarizer.py    # AI summarization
├── pdf_generator.py # PDF generation
├── discord_bot.py   # Discord integration
├── api.py          # REST API
└── cli.py          # Command-line interface
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file:

```env
# Discord Bot (optional)
DISCORD_TOKEN=your_discord_bot_token

# OpenAI (optional, for summarization)
OPENAI_API_KEY=your_openai_api_key

# Database
BUCKET_DB_PATH=bucket.db

# Output
BUCKET_OUTPUT_DIR=output

# Obsidian
OBSIDIAN_VAULT_PATH=/path/to/obsidian/vault
```

### Discord Bot Setup

1. Create a Discord application at https://discord.com/developers/applications
2. Create a bot and copy the token
3. Invite the bot to your server with appropriate permissions
4. Use the token in your `.env` file or `--discord` flag

### Ollama Setup

For local LLM summarization:

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama2

# Start Ollama service
ollama serve
```

## 📖 Usage Examples

### Adding Content

```bash
# Add a single article
bucket add "https://example.com/article" --priority high --tag tech

# Add an RSS feed
bucket feed "Hacker News" "https://news.ycombinator.com/rss" --tag news

# Fetch from all RSS feeds
bucket fetch
```

### Generating Briefings

```bash
# Daily briefing
bucket briefing --title "Daily Briefing" --days 7

# Filtered briefing
bucket briefing --tag tech --priority high --title "Tech Briefing"

# Custom output
bucket briefing --output ./briefings --title "Weekly Summary"
```

### API Usage

```bash
# Start API server
bucket serve --port 8000

# Add article via API
curl -X POST "http://localhost:8000/articles" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article", "priority": "high"}'

# Generate briefing via API
curl -X POST "http://localhost:8000/briefings/generate" \
  -H "Content-Type: application/json" \
  -d '{"title": "Daily Briefing", "days_back": 7}'
```

### Discord Commands

```
!add https://example.com/article
!status
!help
```

## 🔌 API Endpoints

- `GET /` - API status
- `GET /health` - Health check
- `POST /articles` - Add article
- `GET /articles` - List articles
- `GET /articles/{id}` - Get article
- `POST /feeds` - Add RSS feed
- `GET /feeds` - List feeds
- `POST /briefings/generate` - Generate briefing
- `GET /briefings` - List briefings
- `GET /briefings/{filename}` - Download briefing
- `GET /stats` - System statistics

## 📊 Database Schema

The system uses SQLite with the following tables:

- `articles` - Article content and metadata
- `summaries` - AI-generated summaries
- `feeds` - RSS feed configurations
- `deliveries` - Delivery tracking

## 🎯 Advanced Features

### Custom Summarization

```python
from bucket.summarizer import SummarizerFactory

# Use OpenAI
summarizer = SummarizerFactory.create_summarizer(
    summarizer_type="openai",
    api_key="your_key",
    model_name="gpt-3.5-turbo"
)

# Use custom Ollama model
summarizer = SummarizerFactory.create_summarizer(
    summarizer_type="ollama",
    model_name="codellama",
    base_url="http://localhost:11434"
)
```

### Obsidian Integration

```bash
# Export articles to Obsidian
bucket run --obsidian /path/to/vault

# Articles are organized with Johnny.Decimal schema:
# 10.00/20231201_Article_Title.md
```

### Scheduled Tasks

The system automatically:

- Fetches RSS feeds every 4 hours
- Generates daily briefings at 8 AM
- Summarizes pending articles every hour

## 🛠️ Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black bucket/
isort bucket/

# Type checking
mypy bucket/
```

### Adding New Features

1. Create feature branch
2. Add tests in `tests/`
3. Update documentation
4. Submit pull request

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai/) for local LLM inference
- [FastAPI](https://fastapi.tiangolo.com/) for the REST API
- [WeasyPrint](https://weasyprint.org/) for PDF generation
- [Typer](https://typer.tiangolo.com/) for the CLI
- [Rich](https://rich.readthedocs.io/) for beautiful terminal output

## 🐛 Troubleshooting

### Common Issues

**Discord bot not responding**
- Check bot token and permissions
- Ensure bot is invited to server

**Ollama connection failed**
- Verify Ollama is running: `ollama serve`
- Check model is installed: `ollama list`

**PDF generation fails**
- Install system dependencies for WeasyPrint
- Check output directory permissions

**Database errors**
- Delete `bucket.db` and reinitialize
- Check SQLite installation

### Getting Help

- Check the [Issues](https://github.com/yourusername/bucket/issues) page
- Create a new issue with detailed information
- Join our [Discord server](https://discord.gg/bucket) for support

---

**Bucket** - Because knowledge should flow like water, not pile up like clutter. 🪣
