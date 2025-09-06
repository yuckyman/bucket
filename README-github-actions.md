# Bucket GitHub Actions Migration

This branch contains the GitHub Actions-based version of the bucket system, designed to run entirely in the cloud without requiring a persistent server.

## Architecture

### Workflows

1. **RSS Crawler** (`.github/workflows/rss-crawler.yml`)
   - Runs every 30 minutes
   - Fetches RSS feeds and saves new articles
   - Updates API endpoints
   - Can be triggered manually or via webhook

2. **Discord Webhook Handler** (`.github/workflows/discord-webhook.yml`)
   - Handles Discord commands via repository dispatch
   - Supports `!add`, `!feeds`, `!status` commands
   - Sends responses back to Discord via webhook

3. **Content Processor** (`.github/workflows/content-processor.yml`)
   - Runs every 2 hours
   - Processes pending articles
   - Updates article statuses
   - Can be enhanced with AI summarization

4. **Newsletter Generator** (`.github/workflows/newsletter-generator.yml`)
   - Runs daily at 8 AM UTC
   - Generates daily briefings
   - Creates JSON, Markdown, and HTML outputs

### Data Structure

- **`data/feeds.json`** - RSS feed configuration
- **`data/articles.json`** - Article database
- **`outputs/api/`** - API endpoints for external consumption
- **`outputs/newsletters/`** - Generated newsletters and briefings

### API Endpoints

Once deployed, these endpoints will be available via GitHub Pages:

- `https://yourusername.github.io/bucket/api/latest-newsletter.json`
- `https://yourusername.github.io/bucket/api/recent-articles.json`
- `https://yourusername.github.io/bucket/api/rss-stats.json`
- `https://yourusername.github.io/bucket/api/processing-queue.json`

## Setup Instructions

### 1. Repository Configuration

1. Fork or clone this repository
2. Update the repository name in `scripts/discord-webhook-sender.py`
3. Set up GitHub Pages for the `outputs/` directory

### 2. Environment Variables

Set these in your repository settings (Settings → Secrets and variables → Actions):

- `GITHUB_TOKEN` - Automatically provided by GitHub Actions
- `DISCORD_WEBHOOK_URL` - Discord webhook URL for responses (optional)

### 3. Discord Integration

To use Discord commands, you'll need to:

1. Create a Discord webhook in your server
2. Set the `DISCORD_WEBHOOK_URL` secret
3. Use the `scripts/discord-webhook-sender.py` script to send commands

### 4. Testing

You can test the workflows manually:

1. Go to Actions tab in your repository
2. Select a workflow
3. Click "Run workflow"
4. Monitor the execution

## Usage

### Discord Commands

- `!add <url>` - Add an article to the bucket
- `!feeds list` - List RSS feeds
- `!feeds add "Name" <url>` - Add a new RSS feed
- `!status` - Show bucket status

### Manual Triggers

- RSS Crawler: Can be run manually with test mode
- Content Processor: Can specify number of articles to process
- Newsletter Generator: Can specify days back and output format

## Migration from Local Bucket

This system is designed to work alongside your existing local bucket system:

1. **Parallel Operation**: Both systems can run simultaneously
2. **Data Sync**: Use the migration scripts to sync data between systems
3. **Gradual Transition**: Start with RSS feeds, then add other features

## Benefits

- **No Server Maintenance**: Runs entirely on GitHub Actions
- **Cost Effective**: Free within GitHub's generous limits
- **Version Controlled**: Full history of all content and changes
- **Scalable**: GitHub Actions handle the heavy lifting
- **Accessible**: API endpoints available anywhere
- **Resilient**: No single point of failure

## Next Steps

1. **Test the RSS Crawler** with a few feeds
2. **Set up Discord integration** for command handling
3. **Enable AI summarization** (OpenAI/Claude integration)
4. **Add more workflows** for advanced features
5. **Set up GitHub Pages** for API endpoints

## Troubleshooting

### Common Issues

1. **Workflow not running**: Check repository permissions and secrets
2. **Discord commands not working**: Verify webhook URL and repository dispatch setup
3. **API endpoints not updating**: Check GitHub Pages configuration
4. **Rate limiting**: GitHub Actions has usage limits, monitor your usage

### Debugging

- Check workflow logs in the Actions tab
- Monitor API endpoints for data updates
- Use manual triggers to test individual workflows
- Check repository secrets and environment variables

## Contributing

This is an experimental migration. Feel free to:

- Add new workflows
- Improve existing functionality
- Add new API endpoints
- Enhance Discord integration
- Add AI summarization features

## License

Same as the main bucket project.
