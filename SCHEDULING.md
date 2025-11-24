# YouTube Video Scheduling Guide

## Overview

This tool supports scheduling YouTube video publication using the `--publish-at` parameter. This feature uses YouTube's native scheduling API to automatically publish videos at a specified date and time.

## Important: How YouTube Scheduling Works

### YouTube API Requirements

YouTube's `publishAt` field has **strict requirements**:

1. ✅ **Video MUST be Private or Unlisted** - The API only works with non-public videos
2. ✅ **Scheduled videos show as "Scheduled" in YouTube Studio** - Not as "Private"
3. ✅ **Videos automatically become Public** at the scheduled time
4. ❌ **Cannot schedule already-public videos** without making them private first

### What Happens When You Schedule

```bash
.venv/bin/python main.py \
  --url "https://youtu.be/VIDEO_ID" \
  --publish-at "2026-02-05 11:00" \
  --tz "Europe/Amsterdam"
```

**If video is Private/Unlisted:**
- ✅ Tool sets `publishAt` field via YouTube API
- ✅ YouTube Studio shows video as **"Scheduled"** (not "Private")
- ✅ Video will automatically become **Public** at scheduled time
- ✅ No manual intervention needed

**If video is already Public:**
- ⚠️ Tool **cannot schedule** without changing privacy status
- 📝 Planned time is **stored in database** for reference
- 💡 Two options to proceed:
  1. Set `FORCE_PRIVATE_FOR_SCHEDULING=true` in `.env` (converts public → scheduled)
  2. Manually change video to Private in YouTube Studio first

## Usage Examples

### Basic Scheduling (Video is Private/Unlisted)

```bash
# Schedule a private video to publish on Feb 5, 2026 at 11:00 AM Amsterdam time
.venv/bin/python main.py \
  --url "https://youtu.be/S5TSdPW49qA" \
  --publish-at "2026-02-05 11:00" \
  --tz "Europe/Amsterdam"
```

**Expected Output:**
```
✅ Successfully scheduled video for automatic publication
📅 Publish time: 2026-02-05T10:00:00Z
📺 YouTube Studio will show this video as 'Scheduled' (not 'Private')
🚀 Video will automatically become public at the scheduled time
```

### Scheduling with Monetization

```bash
.venv/bin/python main.py \
  --url "https://youtu.be/S5TSdPW49qA" \
  --publish-at "2026-02-05 11:00" \
  --tz "Europe/Amsterdam" \
  --enable-monetization \
  --made-for-kids false \
  --ad-suitability standard \
  --ad-formats "skippable,overlay"
```

### Force Private Conversion for Already-Public Videos

**Option 1: Enable via Command (Recommended for Testing)**

```bash
# Add to .env temporarily
echo "FORCE_PRIVATE_FOR_SCHEDULING=true" >> .env

# Run scheduling
.venv/bin/python main.py \
  --url "https://youtu.be/S5TSdPW49qA" \
  --publish-at "2026-02-05 11:00" \
  --tz "Europe/Amsterdam"

# Remove from .env after testing
```

**Option 2: Permanent Configuration**

Edit `.env`:
```bash
# Force public videos to become private when scheduling
# WARNING: This will make currently-public videos private temporarily
FORCE_PRIVATE_FOR_SCHEDULING=true
```

## Configuration Options

### Environment Variables

Add to your `.env` file:

```bash
# Enable/disable YouTube scheduling feature
ENABLE_YT_SCHEDULING=true

# Force public videos to private when scheduling
# WARNING: Converts public → private → scheduled
# Video will be inaccessible until scheduled publish time
FORCE_PRIVATE_FOR_SCHEDULING=false  # Default: false (safer)
```

### Timezone Support

The tool supports all standard timezone names:

```bash
--tz "America/New_York"      # US Eastern
--tz "Europe/London"         # UK
--tz "Asia/Tokyo"            # Japan
--tz "Australia/Sydney"      # Australia
--tz "UTC"                   # Coordinated Universal Time
```

Full list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

## Common Scenarios

### Scenario 1: New Video Upload (Recommended Workflow)

1. **Upload video as Private** via YouTube Studio
2. **Run the tool** with `--publish-at`:
   ```bash
   .venv/bin/python main.py \
     --url "https://youtu.be/NEW_VIDEO" \
     --publish-at "2026-02-10 09:00" \
     --tz "America/Los_Angeles"
   ```
3. **Video is optimized and scheduled** automatically
4. **YouTube publishes it** at the scheduled time

### Scenario 2: Already-Public Video (Manual Workflow)

1. **Video is already public** on YouTube
2. **Run the tool** with `--publish-at`:
   ```bash
   .venv/bin/python main.py \
     --url "https://youtu.be/PUBLIC_VIDEO" \
     --publish-at "2026-02-15 14:00" \
     --tz "Europe/Paris"
   ```
3. **Tool cannot schedule** (video is public):
   ```
   ⚠️  Video is already public - cannot schedule without making it private first
   💡 Planned publish time stored in database, but not applied to YouTube
   ```
4. **Two options:**
   - **Option A:** Manually change video to Private in YouTube Studio, then re-run tool
   - **Option B:** Set `FORCE_PRIVATE_FOR_SCHEDULING=true` and re-run (video becomes private)

### Scenario 3: Re-optimizing Scheduled Video

If you need to update metadata of an already-scheduled video:

```bash
# Video is currently "Scheduled" in YouTube Studio
.venv/bin/python main.py \
  --url "https://youtu.be/SCHEDULED_VIDEO" \
  --publish-at "2026-02-20 10:00" \
  --tz "UTC"
```

**Result:**
- ✅ Metadata is updated
- ✅ Schedule time is updated to new value
- ✅ Video remains scheduled

## Verification

### Check in YouTube Studio

1. Go to https://studio.youtube.com/
2. Click on **Content** in left sidebar
3. Find your video
4. **Visibility column** should show:
   - **"Scheduled"** (if successfully scheduled)
   - **"Private"** (if scheduling failed or not applied)
   - **"Public"** (if video is already published)

### Check Scheduled Publish Time

1. Click on the video in YouTube Studio
2. Go to **Visibility** section
3. You should see:
   ```
   Scheduled
   Feb 5, 2026, 11:00 AM CET
   ```

## Troubleshooting

### Issue: "Video is already public - cannot schedule"

**Cause:** YouTube API doesn't allow scheduling public videos

**Solutions:**
1. **Manual approach:** Change video to Private in YouTube Studio, then re-run tool
2. **Automated approach:** Set `FORCE_PRIVATE_FOR_SCHEDULING=true` in `.env`

### Issue: "publishAt field was not set in response"

**Cause:** YouTube rejected the scheduling request

**Common reasons:**
- Scheduled time is in the past
- Scheduled time is too far in the future (>6 months)
- Video has copyright claims preventing scheduling
- Channel doesn't have permission to schedule

**Solution:** Check YouTube Studio for specific error messages

### Issue: Video shows as "Private" instead of "Scheduled"

**Cause:** The `publishAt` field was not successfully applied

**Debug steps:**
1. Check tool output for errors
2. Verify timezone and date format
3. Ensure scheduled time is in the future
4. Check YouTube Studio for restrictions

## Best Practices

### ✅ Recommended

1. **Upload videos as Private** initially
2. **Test scheduling** with a far-future date first
3. **Verify in YouTube Studio** after scheduling
4. **Keep FORCE_PRIVATE_FOR_SCHEDULING=false** unless you understand the implications
5. **Use consistent timezone** across all operations

### ❌ Not Recommended

1. **Scheduling already-public videos** (requires making them private)
2. **Enabling FORCE_PRIVATE_FOR_SCHEDULING globally** (can accidentally hide public videos)
3. **Scheduling times in the past** (will fail)
4. **Scheduling times >6 months ahead** (may be rejected by YouTube)

## Technical Details

### How It Works

1. **Tool parses** `--publish-at` and `--tz` parameters
2. **Converts to UTC** (YouTube API requires UTC)
3. **Checks video privacy status** via YouTube API
4. **If private/unlisted:** Sets `publishAt` field
5. **If public:**
   - Without `FORCE_PRIVATE_FOR_SCHEDULING`: Skips scheduling, stores in DB
   - With `FORCE_PRIVATE_FOR_SCHEDULING`: Converts to private, then schedules
6. **YouTube automatically publishes** video at scheduled time

### Database Storage

Regardless of API success, the tool stores:
- `planned_publish_at_utc`: UTC datetime
- `planned_publish_at_tz`: Original timezone
- `planned_publish_at_local`: Local datetime string (for display)

This allows you to track planned publish times even if API scheduling fails.

## FAQ

### Q: Can I change the scheduled time after setting it?

**A:** Yes, just re-run the tool with a new `--publish-at` time. It will update the schedule.

### Q: Will scheduling work with livestreams?

**A:** No, this feature is for regular video uploads only.

### Q: What happens if I manually publish a scheduled video?

**A:** The video becomes public immediately and the schedule is cancelled.

### Q: Can I schedule multiple videos at once?

**A:** Not yet implemented. Currently supports single video per execution.

### Q: What timezone is used internally?

**A:** All times are converted to UTC for YouTube API, but stored with your original timezone for reference.

### Q: Why does the video show as "Private" temporarily?

**A:** YouTube requires videos to be private to set a schedule. Once `publishAt` is set, YouTube Studio displays it as "Scheduled" instead.

## Support

If you encounter issues:

1. **Check logs** for detailed error messages
2. **Verify YouTube Studio** shows correct status
3. **Check database** for stored planned times:
   ```bash
   sqlite3 youtube_seo.db "SELECT video_id, planned_publish_at_local FROM videos WHERE planned_publish_at_utc IS NOT NULL;"
   ```
4. **Review this guide** for common scenarios
5. **Open an issue** on GitHub with:
   - Command you ran
   - Tool output/logs
   - Video current status in YouTube Studio
   - Expected vs actual behavior
