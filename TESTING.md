# Testing Guide

## Pre-Testing Checklist

Before running the application, ensure:

- [ ] Python 3.11+ installed
- [ ] Virtual environment created and activated
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] spaCy model downloaded (`python -m spacy download en_core_web_sm`)
- [ ] `.env` file configured with API keys
- [ ] `config/client_secrets.json` downloaded from Google Cloud Console
- [ ] Database initialized (`python src/utils/db_setup.py`)
- [ ] You own at least one YouTube video with captions

## Test 1: Configuration Validation

```bash
# Test configuration loading
python -c "from src.utils.config import Config; print(Config.validate())"
```

Expected output:
```json
{'valid': True, 'missing': [], 'warnings': [...]}
```

## Test 2: Database Initialization

```bash
# Initialize database
python src/utils/db_setup.py
```

Expected output:
```
✅ Database initialized successfully
```

Check that `youtube_seo.db` file is created.

## Test 3: OAuth Authentication (Dry Run)

```bash
# This will trigger OAuth flow without updating anything
python main.py --init-db
```

Expected:
1. Browser opens automatically
2. Google login page appears
3. Grant permissions
4. "Authentication successful" message
5. Token saved to `config/youtube_token.json`

## Test 4: Video Details Retrieval

Test with a public YouTube video (doesn't need to be yours):

```python
# Create test script: test_api.py
from src.services import YouTubeAPIClient

client = YouTubeAPIClient()
video = client.get_video_details("dQw4w9WgXcQ")  # Example video
print(f"Title: {video['snippet']['title']}")
print(f"Channel: {video['snippet']['channelTitle']}")
```

```bash
python test_api.py
```

## Test 5: Transcript Extraction

Test with your own video (must have captions):

```bash
# Preview mode - safe to test
python main.py \
  --url "https://www.youtube.com/watch?v=YOUR_VIDEO_ID" \
  --mode preview
```

Expected output:
```
Processing video: https://...
Fetching transcript for video YOUR_VIDEO_ID
Transcript retrieved: XXXX characters
Generating SEO metadata...

================================================================================
GENERATED METADATA
================================================================================

Title (XX chars):
  Your Optimized Title Here

Description (XXXX chars):
  Your optimized description...

Tags (XXX chars):
  keyword1, keyword2, keyword3, ...
================================================================================

Preview mode - not publishing
```

## Test 6: Dry Run (Full Flow Without Publishing)

```bash
python main.py \
  --url "https://www.youtube.com/watch?v=YOUR_VIDEO_ID" \
  --mode auto \
  --dry-run
```

Expected:
- All steps execute (transcript → generation → validation)
- Database records created
- NO actual YouTube update
- Success message shown

Check database:
```bash
sqlite3 youtube_seo.db "SELECT * FROM videos WHERE video_id='YOUR_VIDEO_ID';"
```

## Test 7: Character Limit Validation

Create a test to verify limits are enforced:

```python
# test_validators.py
from src.utils.validators import enforce_character_limits

# Test with oversized content
result = enforce_character_limits(
    title="A" * 150,  # Over 100 chars
    description="B" * 6000,  # Over 5000 chars
    tags="C" * 600,  # Over 500 chars
    strict=True
)

print(f"Title length: {len(result['title'])} (max 100)")
print(f"Description length: {len(result['description'])} (max 5000)")
print(f"Tags length: {len(result['tags'])} (max 500)")

assert len(result['title']) <= 100
assert len(result['description']) <= 5000
assert len(result['tags']) <= 500
print("✅ All limits enforced correctly")
```

```bash
python test_validators.py
```

## Test 8: Hashtag Removal

```python
# test_hashtags.py
from src.utils.validators import strip_hashtags

test_cases = [
    ("Great #video about #python", "Great video about python"),
    ("#coding #tutorial", "coding tutorial"),
    ("No hashtags here", "No hashtags here"),
]

for input_text, expected in test_cases:
    result = strip_hashtags(input_text)
    assert result == expected, f"Failed: {result} != {expected}"
    print(f"✅ {input_text} → {result}")

print("✅ All hashtag tests passed")
```

```bash
python test_hashtags.py
```

## Test 9: LLM Generation (OpenAI)

```python
# test_llm.py
from src.services import SEOGenerator

generator = SEOGenerator()

test_transcript = """
This is a tutorial about Python programming for beginners.
We cover variables, loops, functions, and basic data structures.
Perfect for anyone starting their coding journey.
"""

metadata = generator.generate_metadata(
    transcript=test_transcript,
    target_keywords=["python", "tutorial", "beginners"]
)

print(f"Title ({len(metadata['title'])}): {metadata['title']}")
print(f"Description ({len(metadata['description'])}): {metadata['description'][:200]}...")
print(f"Tags ({len(metadata['tags'])}): {metadata['tags']}")

# Verify no hashtags
assert '#' not in metadata['title']
assert '#' not in metadata['description']
assert '#' not in metadata['tags']
print("✅ LLM generation successful")
```

```bash
python test_llm.py
```

## Test 10: Batch CSV Processing (Dry Run)

Create test CSV:
```csv
# test_batch.csv
video_url,keywords,notes
https://www.youtube.com/watch?v=VIDEO_ID_1,"python,tutorial","Test 1"
https://www.youtube.com/watch?v=VIDEO_ID_2,"javascript,web","Test 2"
```

```bash
python main.py --batch test_batch.csv --mode preview
```

Expected:
- Processes multiple videos
- Shows generated metadata for each
- Doesn't publish (preview mode)

## Test 11: Analytics Baseline

Test analytics retrieval (requires video with some views):

```python
# test_analytics.py
from src.services import YouTubeAPIClient, AnalyticsService

client = YouTubeAPIClient()
analytics = AnalyticsService(client)

baseline = analytics.get_baseline_metrics("YOUR_VIDEO_ID", days=7)

if baseline:
    print(f"Total Views: {baseline['total_views']}")
    print(f"Total Impressions: {baseline['total_impressions']}")
    print(f"Average CTR: {baseline['average_ctr']:.2%}")
    print("✅ Analytics working")
else:
    print("⚠️  No analytics data (video may be too new)")
```

```bash
python test_analytics.py
```

## Test 12: Notification System

Test Slack notification (if configured):

```python
# test_notification.py
from src.services import Notifier

notifier = Notifier()

notifier.notify_success(
    video_id="TEST123",
    title="Test Video",
    message="This is a test notification"
)

print("✅ Check your Slack/Email for test notification")
```

```bash
python test_notification.py
```

## Test 13: Real Update (Cautious)

⚠️ **This will actually update your video on YouTube**

Use a test video that you don't mind modifying:

```bash
# First, backup current metadata
python main.py \
  --url "https://www.youtube.com/watch?v=TEST_VIDEO_ID" \
  --mode preview \
  > backup.txt

# Then do real update
python main.py \
  --url "https://www.youtube.com/watch?v=TEST_VIDEO_ID" \
  --mode auto
```

Verify:
1. Check YouTube Studio - video metadata should be updated
2. Check database - version history should be saved
3. Check logs - should show success

## Test 14: Rollback

After Test 13, test rollback:

```bash
# Get video ID
VIDEO_ID="TEST_VIDEO_ID"

# Check version history
sqlite3 youtube_seo.db "SELECT id, created_at, title FROM metadata_versions WHERE video_id='$VIDEO_ID' ORDER BY created_at DESC LIMIT 5;"

# Rollback to previous version (use ID from query above)
python -c "
from src.services import YouTubeAPIClient, VideoPublisher
from src.models import SessionLocal

client = YouTubeAPIClient()
db = SessionLocal()
publisher = VideoPublisher(client, db)

success = publisher.rollback_to_version('$VIDEO_ID', VERSION_ID, 'test_rollback')
print(f'Rollback: {\"✅ Success\" if success else \"❌ Failed\"}')
db.close()
"
```

## Test 15: Guardrail Check

Wait 3+ days after an update, then:

```bash
python main.py --check-guardrails VIDEO_ID
```

Expected output:
```
Checking guardrails for video: VIDEO_ID
✅ Guardrail passed: Performance within acceptable range
```

Or if performance dropped:
```
⚠️  Guardrail failed: CTR dropped 20.5% (threshold: 15%)
Initiating auto-rollback...
✅ Successfully rolled back
```

## Test 16: Error Handling

Test various error conditions:

### Invalid URL
```bash
python main.py --url "https://invalid-url.com" --mode preview
# Expected: Error message about invalid URL
```

### Non-existent Video
```bash
python main.py --url "https://www.youtube.com/watch?v=INVALID123" --mode preview
# Expected: Video not found error
```

### No Permissions
```bash
# Use someone else's video
python main.py --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --mode auto
# Expected: Permission denied error
```

## Test 17: Concurrent Processing

Test rate limiting with multiple videos:

```bash
# Create large batch
# Process and verify rate limiting kicks in
python main.py --batch large_batch.csv --mode preview
```

Monitor logs for:
- Rate limit warnings
- Exponential backoff
- Retry attempts

## Performance Benchmarks

Expected timings:

| Operation | Expected Time |
|-----------|---------------|
| Single video (preview) | 15-30 seconds |
| Single video (publish) | 20-35 seconds |
| Transcript extraction | 2-5 seconds |
| LLM generation | 5-15 seconds |
| YouTube update | 2-5 seconds |
| Analytics fetch | 1-3 seconds |
| Batch (10 videos) | 3-5 minutes |

## Troubleshooting Tests

### Test OAuth Refresh
```bash
# Delete token
rm config/youtube_token.json

# Run again - should re-authenticate
python main.py --url "..." --mode preview
```

### Test Database Recovery
```bash
# Backup database
cp youtube_seo.db youtube_seo.db.backup

# Delete and reinitialize
rm youtube_seo.db
python src/utils/db_setup.py

# Restore if needed
mv youtube_seo.db.backup youtube_seo.db
```

### Test API Quota Monitoring
```bash
# Check Google Cloud Console > APIs & Services > Dashboard
# Monitor quota usage after each test
```

## Success Criteria

All tests pass if:

- ✅ Configuration loads without errors
- ✅ Database initializes correctly
- ✅ OAuth authentication completes
- ✅ Transcript extraction works (Captions API or fallback)
- ✅ LLM generates valid metadata (no hashtags, within limits)
- ✅ Character limits enforced correctly
- ✅ Preview mode shows metadata without publishing
- ✅ Dry run executes full flow without YouTube update
- ✅ Real update modifies YouTube video metadata
- ✅ Version history saved correctly
- ✅ Rollback restores previous version
- ✅ Analytics retrieval works
- ✅ Guardrail checks execute
- ✅ Notifications sent successfully
- ✅ Batch processing completes
- ✅ Error handling works as expected

## Continuous Testing

Set up regular tests:

```bash
# Create test script: daily_test.sh
#!/bin/bash

echo "Running daily tests..."

# Test 1: Config validation
python -c "from src.utils.config import Config; assert Config.validate()['valid']"

# Test 2: Database access
sqlite3 youtube_seo.db "SELECT COUNT(*) FROM videos;"

# Test 3: API connectivity
python -c "from src.services import YouTubeAPIClient; YouTubeAPIClient()"

echo "✅ All daily tests passed"
```

```bash
chmod +x daily_test.sh
./daily_test.sh
```

## Test Coverage

Aim for:
- 80%+ code coverage
- All critical paths tested
- Error conditions handled
- Edge cases covered

Run tests with:
```bash
# Install pytest and coverage
pip install pytest pytest-cov

# Run tests with coverage
pytest --cov=src tests/

# Generate HTML report
pytest --cov=src --cov-report=html tests/
open htmlcov/index.html
```

---

**Happy Testing!** 🧪
