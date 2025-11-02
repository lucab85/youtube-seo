# YouTube SEO Quick Start Guide

## Prerequisites

1. **YouTube Channel**: You need a YouTube channel with videos
2. **Google Cloud Project**: Required for YouTube API access
3. **LLM API Key**: OpenAI or Anthropic API key

## Step 1: Google Cloud Console Setup

### Enable YouTube APIs
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Navigate to "APIs & Services" → "Library"
4. Enable these APIs:
   - YouTube Data API v3
   - YouTube Analytics API
   - YouTube Reporting API (optional)

### Create OAuth 2.0 Credentials
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Choose "Desktop application" as application type
4. Name it "YouTube SEO Tool"
5. Click "Create"
6. Download the JSON file
7. Save it as `config/client_secrets.json` in the project directory

### Configure OAuth Consent Screen
1. Go to "APIs & Services" → "OAuth consent screen"
2. Choose "External" user type
3. Fill in app name, user support email, and developer contact
4. Add scopes:
   - `https://www.googleapis.com/auth/youtube`
   - `https://www.googleapis.com/auth/youtube.force-ssl`
   - `https://www.googleapis.com/auth/yt-analytics.readonly`
5. Add your email as a test user (if in testing mode)
6. Save and continue

## Step 2: Get OpenAI or Anthropic API Key

### OpenAI (Recommended)
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Navigate to API keys
4. Create a new secret key
5. Copy and save it securely

### Anthropic (Alternative)
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Sign up or log in
3. Navigate to API keys
4. Create a new key
5. Copy and save it securely

## Step 3: Installation

### Run Setup Script
```bash
# Make setup script executable
chmod +x setup.sh

# Run setup
./setup.sh
```

### Manual Setup (Alternative)
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Initialize database
python src/utils/db_setup.py
```

## Step 4: Configuration

### Edit .env File
```bash
# Open .env in your favorite editor
nano .env  # or: vim .env, code .env, etc.
```

### Required Settings
```env
# YouTube OAuth (from Google Cloud Console)
YOUTUBE_CLIENT_ID=your_client_id.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=your_client_secret

# LLM API (choose one)
OPENAI_API_KEY=sk-...your-key...
# OR
ANTHROPIC_API_KEY=sk-ant-...your-key...

# Optional: Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
EMAIL_FROM=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_TO=recipient@example.com
```

## Step 5: First Run (OAuth Authentication)

```bash
# Preview mode (doesn't publish)
python main.py --url "https://www.youtube.com/watch?v=YOUR_VIDEO_ID" --mode preview
```

### OAuth Flow
1. A browser window will open automatically
2. Log in with your YouTube account
3. Grant permissions to the application
4. Browser will show "Authentication successful"
5. Return to terminal - the script will continue

The OAuth token is saved in `config/youtube_token.json` for future use.

## Step 6: Usage Examples

### Single Video - Preview Only
```bash
python main.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --mode preview
```

### Single Video - Auto-Publish
```bash
python main.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --mode auto
```

### With Custom Keywords
```bash
python main.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --keywords "python,tutorial,beginners,programming" \
  --mode auto
```

### Batch Processing
```bash
# Create CSV file
cp videos.csv.example videos.csv

# Edit videos.csv with your video URLs

# Process batch
python main.py --batch videos.csv --mode auto
```

### Check Performance Guardrails
```bash
python main.py --check-guardrails VIDEO_ID
```

### Dry Run (Test Without Publishing)
```bash
python main.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --mode auto \
  --dry-run
```

## Step 7: CSV Batch File Format

Create `videos.csv` with this format:

```csv
video_url,keywords,notes
https://www.youtube.com/watch?v=VIDEO_ID_1,"keyword1,keyword2,keyword3","Optional note"
https://www.youtube.com/watch?v=VIDEO_ID_2,"keyword4,keyword5","Another video"
```

## Troubleshooting

### "OAuth credentials file not found"
- Download client_secrets.json from Google Cloud Console
- Save it in the `config/` directory

### "Import could not be resolved"
- Ensure virtual environment is activated: `source venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

### "Video not found" or "Permission denied"
- Ensure you're authenticated with the correct YouTube account
- Verify you own the video
- Delete `config/youtube_token.json` and re-authenticate

### "API quota exceeded"
- YouTube Data API has daily quota limits (default: 10,000 units)
- Each video update costs ~300 units
- Request quota increase from Google Cloud Console
- Or wait until next day (quota resets at midnight Pacific Time)

### "No transcript available"
- Enable captions on your video in YouTube Studio
- Wait a few minutes for auto-generated captions
- Or upload manual captions

### "OpenAI API error"
- Check your API key is correct
- Verify you have credits/billing enabled
- Check OpenAI status page for outages

## Best Practices

1. **Start with Preview Mode**: Always test with `--mode preview` first
2. **Use Dry Run**: Test the full flow with `--dry-run` flag
3. **Monitor Performance**: Check analytics after updates
4. **Enable Guardrails**: Keep `ENABLE_AUTO_ROLLBACK=true` in .env
5. **Batch Process Carefully**: Start with small batches (5-10 videos)
6. **Rate Limiting**: Add delays between batch operations

## Support

For issues and questions:
- Check the logs (structured JSON output)
- Review error messages in terminal
- Check YouTube Studio for video status
- Verify API quotas in Google Cloud Console

## Next Steps

- Set up scheduled re-optimization (cron job)
- Configure Slack/Email notifications
- Customize brand voice in database configs
- Fine-tune LLM prompts for your channel style
