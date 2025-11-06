# Monetization Feature

Enable and configure monetization for YouTube videos via CLI.

## Overview

The `--enable-monetization` flag activates a best-effort monetization flow that:

1. **Applies programmatic settings** via YouTube Data API (made-for-kids, age restriction)
2. **Records your monetization intent** (ad formats, suitability, paid promotion)
3. **Generates a Studio deeplink** for manual completion of settings that can't be automated
4. **Sends notifications** with a summary and checklist

## Quick Start

### Minimal Example

```bash
python main.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --mode auto \
  --enable-monetization
```

### Full Example with All Options

```bash
python main.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --mode auto \
  --enable-monetization \
  --made-for-kids false \
  --paid-promotion none \
  --ad-suitability standard \
  --ad-formats "skippable,overlay,display" \
  --age-restriction none \
  --monetization-notes "Standard ad config for tech tutorial"
```

## CLI Flags

### Core Monetization Flag

- `--enable-monetization` - Activates the monetization flow

### Optional Settings

- `--made-for-kids {true|false}` - Sets "made for kids" status (**API supported**)
- `--paid-promotion {none|includes|not_sure}` - Paid promotion disclosure (**Studio required**)
- `--ad-suitability {standard|limited|mature|not_sure}` - Ad suitability (**Studio required**)
- `--ad-formats "format1,format2"` - Desired ad formats (skippable, overlay, display, etc.) (**Studio required**)
- `--age-restriction {none|18+}` - Age restriction (**Partial API support**)
- `--monetization-notes "text"` - Free-text notes (stored in database)

### Advanced Flags

- `--assume-ypp-eligible` - Skip YPP eligibility checks
- `--no-deeplink` - Suppress Studio deeplink generation
- `--fail-on-incomplete` - Exit non-zero if Studio completion needed

## What Can Be Automated?

### ✅ Applied via API

1. **Made for Kids** - Fully automated via `selfDeclaredMadeForKids`
2. **Age Restriction** - Partially automated (some restrictions need Studio)

### ⚠️ Requires Studio Completion

**YouTube Data API v3 limitations** - These require manual Studio completion:

1. **Enable Ads Toggle** - Cannot be automated
2. **Ad Formats Selection** - Cannot be automated
3. **Ad Suitability Questionnaire** - Cannot be automated
4. **Paid Promotion Disclosure** - Cannot be automated

## Output

### CLI Summary Table

```
================================================================================
MONETIZATION: ENABLED (intent)
================================================================================

Setting                        Action              Notes
--------------------------------------------------------------------------------
Made for kids                  APPLIED             set to false
Age restriction                APPLIED             none
Ad formats                     NEEDS STUDIO        skippable, overlay
Ad suitability                 NEEDS STUDIO        standard
Monetization toggle            NEEDS STUDIO        enable ads
--------------------------------------------------------------------------------
Completion state: PARTIAL

📺 Studio link: https://studio.youtube.com/video/VIDEO_ID/monetization
================================================================================
```

## Examples

### Tech Tutorial (Standard Ads)

```bash
python main.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --mode auto \
  --enable-monetization \
  --made-for-kids false \
  --ad-suitability standard \
  --ad-formats "skippable,overlay" \
  --paid-promotion none
```

### Sponsored Content

```bash
python main.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --mode auto \
  --enable-monetization \
  --made-for-kids false \
  --paid-promotion includes \
  --monetization-notes "Sponsored by TechCorp"
```

## Best Practice: Channel-Level Defaults

For automatic monetization of ALL videos, configure channel defaults once:

1. Go to YouTube Studio → Settings → Upload defaults
2. Enable monetization in the Upload defaults section
3. Select default ad types
4. All future uploads will inherit these settings

This is more efficient than per-video monetization setup.

## See Also

- [QUICKSTART.md](QUICKSTART.md) - Getting started
- [README.md](README.md) - Main documentation
