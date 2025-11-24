#!/usr/bin/env bash
# Live run for multiple YouTube videos (will update YouTube metadata)

set -euo pipefail

VIDEO_IDS=(
  Q87YTfiq8X8
  1xT-jmFfHFY
  3XWNE1ZK6aQ
  dagVneESLao
  5451dNVbKWM
  NyCi8gJfF2k
  fa7DMvPaqUQ
  _7Kyzv6hp84
  LRwKxIXKMhw
  tFsdIHRrNxY
  uA4-ZcfB5ow
  VtrakOmje88
  k3dfOh82WUw
  xDfhZe1BB3c
  sg9gd7p14LI
  eEMXTx592_s
  E2AuWFYt4RI
  97gCvlOjPeA
  NS3jm7qLKek
  huapC6spZ6o
  ra4s9MKLlVQ
  hgTZHNwCgjA
  gmRHjJrpYOE
  5RnLNhzwOZI
  Ex_Fk_M5iFM
  BEUV4xiMcxg
  DigPlb5TCLA
)

TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/live_run_$TIMESTAMP.log"

echo "Live run started at $(date -u)" | tee "$LOG_FILE"

env_python=".venv/bin/python"
if [ ! -x "$env_python" ]; then
  env_python="$(which python3 || which python)"
  echo "Using system python: $env_python" | tee -a "$LOG_FILE"
fi

# Safety reminder
echo "WARNING: This script will perform LIVE updates on YouTube. Ensure you have valid OAuth credentials and understand the changes." | tee -a "$LOG_FILE"

for id in "${VIDEO_IDS[@]}"; do
  echo "\n==== Processing video: $id ====" | tee -a "$LOG_FILE"
  # Run main.py in auto mode (apply metadata)
  # If you want to enable monetization or publish-at, edit this command accordingly
  "$env_python" main.py --url "https://youtu.be/$id" --mode auto 2>&1 | tee -a "$LOG_FILE" || echo "ERROR processing $id" | tee -a "$LOG_FILE"
  echo "==== Done: $id ====" | tee -a "$LOG_FILE"
  # small pause to respect API rate limits
  sleep 2
done

echo "Live run finished at $(date -u)" | tee -a "$LOG_FILE"

echo "Logs saved to: $LOG_FILE"
