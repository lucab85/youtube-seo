#!/usr/bin/env bash
# Test scheduling feature with different scenarios

echo "=== YouTube Scheduling Feature Test ==="
echo ""

# Test 1: Dry run with scheduling
echo "Test 1: Dry run mode (no actual changes)"
.venv/bin/python main.py \
  --url "https://youtu.be/S5TSdPW49qA" \
  --publish-at "2026-02-05 11:00" \
  --tz "Europe/Amsterdam" \
  --mode preview

echo ""
echo "---"
echo ""

# Test 2: Show help for scheduling parameters
echo "Test 2: Help information"
.venv/bin/python main.py --help | grep -A 5 "publish-at"

echo ""
echo "---"
echo ""

# Test 3: Check database for stored planned times
echo "Test 3: Check database for previously stored planned times"
if [ -f "youtube_seo.db" ]; then
    echo "Videos with planned publish times:"
    sqlite3 youtube_seo.db "SELECT video_id, planned_publish_at_local, planned_publish_at_tz FROM videos WHERE planned_publish_at_utc IS NOT NULL;"
else
    echo "Database not found"
fi

echo ""
echo "=== Tests Complete ==="
