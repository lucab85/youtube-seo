#!/usr/bin/env bash
# Retry live updates for videos listed in logs/failed_videos_20251119T234540Z.txt

set -euo pipefail

FAILED_FILE="logs/failed_videos_20251119T234540Z.txt"
if [ ! -f "$FAILED_FILE" ]; then
  echo "Failed IDs file not found: $FAILED_FILE"
  exit 1
fi

TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/live_retry_$TIMESTAMP.log"

# Seconds to sleep between requests (tune if you hit quota). Can be overridden:
SLEEP_SECONDS=${SLEEP_SECONDS:-4}

echo "Live retry started at $(date -u)" | tee "$LOG_FILE"

env_python=".venv/bin/python"
if [ ! -x "$env_python" ]; then
  env_python="$(which python3 || which python)"
  echo "Using system python: $env_python" | tee -a "$LOG_FILE"
fi

echo "WARNING: This will perform LIVE updates on YouTube. Ensure OAuth credentials are correct." | tee -a "$LOG_FILE"

# Read unique, non-empty lines from the failed IDs file (portable to macOS bash)
# Sanitize entries: remove non-ID chars and keep only valid 11-char YouTube IDs
TMPFILE=$(mktemp)
awk 'NF {print $1}' "$FAILED_FILE" | sort -u > "$TMPFILE"
IDS=()
while IFS= read -r line; do
  # strip surrounding quotes/braces and any trailing punctuation
  cleaned=$(echo "$line" | sed -E 's/[^A-Za-z0-9_-]//g')
  # keep only 11-char candidate IDs (common YouTube ID length)
  if [[ "$cleaned" =~ ^[-_A-Za-z0-9]{11}$ ]]; then
    IDS+=("$cleaned")
  else
    echo "Skipping invalid/unclean ID entry: '$line' -> '$cleaned'" | tee -a "$LOG_FILE"
  fi
done < "$TMPFILE"
rm -f "$TMPFILE"
if [ ${#IDS[@]} -eq 0 ]; then
  echo "No failed IDs found in $FAILED_FILE" | tee -a "$LOG_FILE"
  exit 0
fi

for id in "${IDS[@]}"; do
  echo "\n==== Processing video: $id ====" | tee -a "$LOG_FILE"
  # Use same invocation as run_videos_live.sh
  "$env_python" main.py --url "https://youtu.be/$id" --mode auto 2>&1 | tee -a "$LOG_FILE" || echo "ERROR processing $id" | tee -a "$LOG_FILE"
  echo "==== Done: $id ====" | tee -a "$LOG_FILE"
  sleep "$SLEEP_SECONDS"
done

echo "Live retry finished at $(date -u)" | tee -a "$LOG_FILE"

echo "Logs saved to: $LOG_FILE"
