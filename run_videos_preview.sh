#!/usr/bin/env bash
# Preview run for multiple YouTube videos (no API writes)

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
LOG_FILE="$LOG_DIR/preview_run_$TIMESTAMP.log"

echo "Preview run started at $(date -u)" | tee "$LOG_FILE"

env_python=".venv/bin/python"
if [ ! -x "$env_python" ]; then
  env_python="$(which python3 || which python)"
  echo "Using system python: $env_python" | tee -a "$LOG_FILE"
fi

for id in "${VIDEO_IDS[@]}"; do
  echo "\n==== Processing video: $id ====" | tee -a "$LOG_FILE"
  # Run main.py in preview mode (no YouTube updates)
  "$env_python" main.py --url "https://youtu.be/$id" --mode preview 2>&1 | tee -a "$LOG_FILE"
  echo "==== Done: $id ====" | tee -a "$LOG_FILE"
  # small pause to avoid rate spikes
  sleep 1
done

echo "Preview run finished at $(date -u)" | tee -a "$LOG_FILE"

# Print summary header
echo "Logs saved to: $LOG_FILE"
