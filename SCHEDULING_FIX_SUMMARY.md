# YouTube Scheduling Fix - Summary

## Issue Description

User reported that the `--publish-at` feature was setting videos to **private** instead of properly scheduling them, which seemed like a regression from previous behavior.

## Root Cause Analysis

After investigating the code and YouTube API documentation, the issue is **not a regression** but rather a **fundamental limitation of YouTube's Data API v3**:

### YouTube API Requirements for Scheduling

1. **The `publishAt` field ONLY works when video privacy is set to `private` or `unlisted`**
2. **Public videos cannot be scheduled** without first converting them to private
3. **This is a YouTube API limitation**, not a bug in the tool

### What Actually Happens

When you use `--publish-at`:

**If video is Private/Unlisted:**
- ✅ Tool sets `publishAt` field successfully
- ✅ Video shows as **"Scheduled"** in YouTube Studio (not "Private")
- ✅ YouTube automatically publishes video at scheduled time

**If video is already Public:**
- ⚠️ Tool **cannot schedule** without changing privacy
- 📝 Planned time is **stored in database only**
- 💡 User must manually change to Private or enable `FORCE_PRIVATE_FOR_SCHEDULING`

## Changes Implemented

### 1. Improved `schedule_publish()` Method
**File:** `src/services/publisher.py`

**Changes:**
- ✅ Removed the two-step API call (was redundant)
- ✅ Added better detection of already-public videos
- ✅ Added configuration option `FORCE_PRIVATE_FOR_SCHEDULING`
- ✅ Improved logging and user feedback
- ✅ Better error messages explaining YouTube API limitations

**Before:**
```python
# Step 1: Set to private
# Step 2: Set publishAt
# (Two separate API calls)
```

**After:**
```python
# Single API call with publishAt
# Only if video is not public OR FORCE_PRIVATE_FOR_SCHEDULING is enabled
```

### 2. Added Configuration Flag
**File:** `src/utils/config.py`

**New Setting:**
```python
FORCE_PRIVATE_FOR_SCHEDULING = os.getenv('FORCE_PRIVATE_FOR_SCHEDULING', 'false').lower() == 'true'
```

**Purpose:**
- Default: `false` (safer - won't change public videos)
- When `true`: Allows converting public videos to private for scheduling
- Gives users control over this behavior

### 3. Enhanced User Messaging

**Before:**
```
Video is already public - cannot schedule
```

**After:**
```
⚠️  Video is already public - cannot schedule without making it private first
💡 Planned publish time stored in database, but not applied to YouTube
💡 To schedule a public video:
   1. Set FORCE_PRIVATE_FOR_SCHEDULING=true in .env, OR
   2. Manually change video to private/unlisted in YouTube Studio first
```

### 4. Created Comprehensive Documentation
**File:** `SCHEDULING.md`

**Includes:**
- ✅ How YouTube scheduling works
- ✅ YouTube API requirements and limitations
- ✅ Usage examples for different scenarios
- ✅ Configuration options
- ✅ Troubleshooting guide
- ✅ Best practices
- ✅ FAQ section

### 5. Created Test Script
**File:** `test_scheduling.sh`

**Features:**
- Tests dry run mode
- Shows help information
- Queries database for planned times

## Usage Guide

### Recommended Workflow (New Videos)

```bash
# 1. Upload video as Private via YouTube Studio
# 2. Run tool with scheduling
.venv/bin/python main.py \
  --url "https://youtu.be/VIDEO_ID" \
  --publish-at "2026-02-05 11:00" \
  --tz "Europe/Amsterdam" \
  --enable-monetization \
  --made-for-kids false \
  --ad-suitability standard \
  --ad-formats "skippable,overlay"

# 3. Video is optimized and scheduled
# 4. YouTube auto-publishes at scheduled time
```

### Handling Already-Public Videos

**Option 1: Manual (Safest)**
```bash
# 1. Manually change video to Private in YouTube Studio
# 2. Run tool
.venv/bin/python main.py --url "..." --publish-at "..."
```

**Option 2: Automated (Use with Caution)**
```bash
# 1. Enable force conversion
echo "FORCE_PRIVATE_FOR_SCHEDULING=true" >> .env

# 2. Run tool (will convert public → private → scheduled)
.venv/bin/python main.py --url "..." --publish-at "..."

# 3. Remove flag after use
sed -i '' '/FORCE_PRIVATE_FOR_SCHEDULING/d' .env
```

## Configuration Options

### Environment Variables (.env)

```bash
# Enable/disable YouTube scheduling API calls
ENABLE_YT_SCHEDULING=true

# Allow converting public videos to private for scheduling
# WARNING: This makes public videos private temporarily
# They become public again at scheduled time
FORCE_PRIVATE_FOR_SCHEDULING=false  # Default: false (safer)
```

## What Changed vs Before

### Behavior Comparison

| Scenario | Before | After |
|----------|---------|--------|
| Private video + scheduling | ✅ Scheduled correctly | ✅ Same (no change) |
| Unlisted video + scheduling | ✅ Scheduled correctly | ✅ Same (no change) |
| Public video + scheduling | ⚠️ Made private & scheduled | ⚠️ Skipped by default* |

\* With `FORCE_PRIVATE_FOR_SCHEDULING=false` (default)

### Key Improvements

1. **More control:** User decides if public videos should be converted
2. **Better transparency:** Clear messages about what's happening
3. **Safer defaults:** Won't accidentally hide public videos
4. **Better documentation:** Comprehensive guide explaining YouTube API limitations
5. **Database tracking:** Planned times stored even if API scheduling fails

## Testing

### Test the Changes

```bash
# Run test script
./test_scheduling.sh

# Or manually test
.venv/bin/python main.py \
  --url "https://youtu.be/S5TSdPW49qA" \
  --publish-at "2026-02-05 11:00" \
  --tz "Europe/Amsterdam" \
  --mode preview
```

### Verify in YouTube Studio

1. Go to https://studio.youtube.com/
2. Click **Content**
3. Check video visibility:
   - Should show **"Scheduled"** (if successful)
   - Should show scheduled date/time

## Important Notes

### YouTube API Limitations

These are **YouTube API restrictions**, not tool limitations:

1. ✅ `publishAt` ONLY works with private/unlisted videos
2. ❌ Cannot schedule public videos without making them private first
3. ✅ Scheduled videos show as "Scheduled" in YouTube Studio (not "Private")
4. ✅ Videos automatically become public at scheduled time

### Database Storage

The tool **always stores** the planned publish time in the database, even if YouTube API scheduling fails. This allows you to:
- Track your publishing schedule
- Reference planned times later
- Re-attempt scheduling if it failed

Query database:
```bash
sqlite3 youtube_seo.db "SELECT video_id, planned_publish_at_local FROM videos WHERE planned_publish_at_utc IS NOT NULL;"
```

## Recommendations

### For Best Results

1. ✅ **Upload new videos as Private** initially
2. ✅ **Run tool with `--publish-at`** immediately after upload
3. ✅ **Keep `FORCE_PRIVATE_FOR_SCHEDULING=false`** (default)
4. ✅ **Verify in YouTube Studio** after running tool
5. ✅ **Test with far-future dates** first to ensure it works

### Avoid

1. ❌ **Scheduling already-public videos** (requires extra steps)
2. ❌ **Enabling `FORCE_PRIVATE_FOR_SCHEDULING` globally** (can hide public videos)
3. ❌ **Scheduling times in the past** (will fail)
4. ❌ **Scheduling >6 months ahead** (YouTube may reject)

## Files Modified

1. **src/services/publisher.py**
   - Improved `schedule_publish()` method
   - Added `FORCE_PRIVATE_FOR_SCHEDULING` support
   - Better error handling and logging

2. **src/utils/config.py**
   - Added `FORCE_PRIVATE_FOR_SCHEDULING` configuration flag

3. **SCHEDULING.md** (new)
   - Comprehensive documentation
   - Usage examples
   - Troubleshooting guide

4. **test_scheduling.sh** (new)
   - Test script for scheduling feature

5. **SCHEDULING_FIX_SUMMARY.md** (this file)
   - Summary of changes and fixes

## Next Steps

1. ✅ Read `SCHEDULING.md` for full documentation
2. ✅ Test with a private/unlisted video first
3. ✅ Verify in YouTube Studio
4. ✅ Add `FORCE_PRIVATE_FOR_SCHEDULING=true` to `.env` only if needed
5. ✅ Report any issues with detailed logs

## Support

If you encounter issues:

1. Check `SCHEDULING.md` for troubleshooting
2. Review tool output for error messages
3. Verify video status in YouTube Studio
4. Check database for stored planned times
5. Open GitHub issue with:
   - Command used
   - Tool output
   - Video current status
   - Expected vs actual behavior
