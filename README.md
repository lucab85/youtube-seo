# YouTube SEO Metadata Generator & Auto-Updater

Automatically optimize YouTube video metadata using AI and current SEO best practices.

## Features

- 🤖 **AI-Powered Generation**: Uses LLMs (OpenAI, Anthropic, or **Google AI - FREE!**) to create optimized titles, descriptions, and tags
- 💰 **FREE Option Available**: Google AI (Gemini) offers generous free tier - no credit card needed!
- 📊 **SEO Best Practices**: Follows YouTube's latest search optimization guidelines
- 🔄 **Auto-Update**: Directly updates video metadata via YouTube API
- 📈 **Performance Monitoring**: Tracks CTR, views, and other metrics
- ↩️ **Auto-Rollback**: Reverts changes if performance drops
- 🔁 **Scheduled Re-optimization**: Keeps content fresh with periodic updates
- 📦 **Batch Processing**: Handle multiple videos at once
- 🔔 **Notifications**: Slack and email alerts for key events

## Installation

### 1. Clone the repository
```bash
git clone <repository-url>
cd youtube-video
```

### 2. Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Download spaCy model
```bash
python -m spacy download en_core_web_sm
```

### 5. Set up configuration
```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

### 6. Get AI API Key (Choose One)

**Recommended: Google AI (FREE!)** 🆓
1. Visit: https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API key"
4. Copy key and add to `.env` as `GOOGLE_AI_API_KEY`
5. See [GOOGLE_AI_SETUP.md](GOOGLE_AI_SETUP.md) for details

**Alternatives:**
- OpenAI: https://platform.openai.com/api-keys (requires credit card)
- Anthropic: https://console.anthropic.com/ (requires credit card)

### 7. Set up YouTube OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable YouTube Data API v3 and YouTube Analytics API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download the JSON file and save as `config/client_secrets.json`

### 8. Initialize database
```bash
python src/utils/db_setup.py
```

## Quick Start

### Single Video Optimization
```bash
python main.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --mode auto
```

### Preview Before Publishing
```bash
python main.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --mode preview
```

### Batch Processing
```bash
python main.py --batch videos.csv --mode auto
```

### Scheduled Re-optimization
```bash
python main.py --reoptimize --schedule weekly
```

## Configuration

### Character Limits
- **Title**: Maximum 100 characters
- **Description**: Maximum 5,000 characters
- **Tags**: Maximum 500 characters (comma-separated, NO hashtags)

### Performance Guardrails
- Monitors CTR, impressions, and view duration
- Auto-rollback if CTR drops > 15% over 3 days
- Configurable thresholds in `.env`

## Architecture

```
src/
├── models/          # Database models (SQLAlchemy)
├── services/        # Business logic
│   ├── youtube_api.py       # YouTube API client
│   ├── transcript.py        # Transcript extraction
│   ├── seo_generator.py     # AI-powered SEO generation
│   ├── publisher.py         # Video metadata updates
│   ├── analytics.py         # Performance monitoring
│   └── notifier.py          # Notifications (Slack/Email)
├── utils/           # Helper functions
│   ├── config.py            # Configuration management
│   ├── logger.py            # Logging setup
│   └── validators.py        # Input validation
└── main.py          # CLI entry point
```

## API Quotas

YouTube Data API v3 has daily quota limits:
- Default: 10,000 units/day
- Video update: ~300 units per video
- Maximum ~30 videos/day with default quota

Request quota increase for higher volume.

## Development

### Run tests
```bash
pytest
```

### Format code
```bash
black src/
```

### Lint
```bash
flake8 src/
```

## Troubleshooting

### OAuth Authentication Issues
- Ensure `client_secrets.json` is in `config/` directory
- Delete `config/youtube_token.json` and re-authenticate
- Check OAuth scopes are enabled in Google Cloud Console

### Quota Exceeded
- Monitor daily API usage
- Request quota increase from Google
- Use caching to reduce API calls

### No Transcript Available
- Ensure video has captions enabled
- Try ASR fallback (if enabled in `.env`)
- Manually provide transcript via `--transcript` flag

## License

MIT License - See LICENSE file for details

## Support

For issues and questions, please open a GitHub issue.
