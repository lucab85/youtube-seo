# YouTube Monetization Guide

## TL;DR - Automated Monetization

**Unfortunately, full monetization automation is NOT possible via YouTube Data API v3.** However, there are workarounds:

### ✅ Best Solution: Set Channel-Level Defaults (One-Time Setup)

This will automatically monetize ALL future uploads:

1. **Go to YouTube Studio**: https://studio.youtube.com
2. **Click Settings** (bottom left) → **Upload defaults**
3. **Go to "Advanced settings" tab**:
   - Set "Standard YouTube License"
   - Set "Not made for kids"
4. **Go to "Monetization" in left menu**:
   - Click "ON" to enable monetization
   - Select your default ad types:
     - ✅ Display ads
     - ✅ Overlay ads
     - ✅ Skippable video ads
     - ✅ Non-skippable video ads
5. **Save settings**

**Result**: All new video uploads will automatically inherit these monetization settings!

---

## What This Tool Can Do

### ✅ This tool CAN:
- Set video as **"not made for kids"** (required for monetization)
- Set proper **license type** ("Standard YouTube License")
- Set video to **public** (required for monetization)
- Check monetization **eligibility**

### ❌ This tool CANNOT (API limitation):
- Enable monetization directly
- Select ad types (skippable, non-skippable, etc.)
- Set ad placement (pre-roll, mid-roll, post-roll)
- Configure content suitability settings

---

## Usage

### Enable Monetization Prerequisites

When processing a video, add the `--enable-monetization` flag:

```bash
# Process video + set monetization eligibility
python main.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --mode auto --enable-monetization

# With keywords
python main.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --mode auto --enable-monetization --keywords "tech,tutorial"
```

### Check Monetization Status

```bash
python main.py --check-monetization VIDEO_ID
```

**Output example:**
```
================================================================================
MONETIZATION STATUS
================================================================================
Video ID: TYEG3rH2t4E
Eligible for monetization: ✅ Yes
Made for kids: No
License: youtube
Privacy: public

Note: Actual monetization status (ads enabled) cannot be read via API v3
================================================================================
```

---

## Manual Monetization Steps

After running the tool with `--enable-monetization`, you still need to:

1. **Go to YouTube Studio**: https://studio.youtube.com/video/VIDEO_ID/monetization
2. **Click "ON"** to enable monetization
3. **Select ad types**:
   - Display ads
   - Overlay ads
   - Skippable video ads
   - Non-skippable video ads
   - Bumper ads
4. **Click "SAVE"**

---

## Why These Limitations Exist

YouTube restricts monetization controls for several reasons:

1. **Policy Compliance**: YouTube needs to ensure videos meet advertiser-friendly guidelines
2. **Manual Review**: Some videos require human review before monetization
3. **Revenue Protection**: Prevents automated abuse of monetization features
4. **Legal Requirements**: Certain content requires manual certification (e.g., COPPA compliance)

---

## Alternative Solutions

### Option 1: YouTube Content Manager API (Partners Only)
If you're a YouTube Partner with a Content Manager account, you may have access to more advanced APIs:
- YouTube Content ID API
- YouTube Partner API

These APIs provide more control but require special partnership status.

### Option 2: Browser Automation (Not Recommended)
You could use tools like Selenium/Puppeteer to automate the YouTube Studio interface, but:
- ❌ Violates YouTube Terms of Service
- ❌ Fragile (breaks when UI changes)
- ❌ Risk of account suspension
- ❌ Not officially supported

### Option 3: Bulk Actions in YouTube Studio
For multiple videos:
1. Go to YouTube Studio → Content
2. Select multiple videos (checkboxes)
3. Click "Edit" → "Monetization"
4. Enable monetization for all selected videos at once

---

## Requirements

For any monetization (automated or manual), your channel must:

✅ Be part of the **YouTube Partner Program** (YPP):
- 1,000+ subscribers
- 4,000+ watch hours (or 10M Shorts views) in past 12 months
- Follow YouTube monetization policies
- Have linked AdSense account

✅ Videos must meet **advertiser-friendly content guidelines**:
- No inappropriate language
- No controversial/sensitive topics
- No violence or dangerous content
- Follow YouTube Community Guidelines

---

## Troubleshooting

### "Permission denied - channel may not be in YouTube Partner Program"
**Solution**: Your channel needs to be accepted into YPP. Check at: https://studio.youtube.com/channel/UC/monetization

### "The request metadata specifies invalid video metadata"
**Solution**: Video may already be set correctly. Check with:
```bash
python main.py --check-monetization VIDEO_ID
```

### Monetization still shows "OFF" in Studio
**Solution**: The API only sets eligibility. You must manually enable monetization in YouTube Studio.

---

## Summary

**For Automated Monetization**:
1. ✅ Set channel-level monetization defaults (one-time, in YouTube Studio)
2. ✅ Use this tool to ensure videos are eligible (`--enable-monetization`)
3. ✅ New uploads will automatically be monetized

**For Existing Videos**:
1. ✅ Run tool with `--enable-monetization` to set eligibility
2. ⚠️ Manually enable in YouTube Studio (or use bulk edit for multiple videos)

**This is a YouTube API limitation, not a tool limitation.**
