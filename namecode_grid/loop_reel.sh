#!/usr/bin/env bash
# Loop a short Krea reel seed into a finished IG reel.
# Usage: loop_reel.sh <seed.mp4> [out.mp4] [seconds]
# Output: 1080x1920 (9:16), 30fps, h264/yuv420p, silent, faststart.
set -euo pipefail
IN="${1:?seed mp4 required}"
OUT="${2:-reel_30s.mp4}"
SECS="${3:-30}"

ffmpeg -y -stream_loop -1 -i "$IN" -t "$SECS" \
  -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30" \
  -c:v libx264 -preset medium -pix_fmt yuv420p -movflags +faststart -an "$OUT"

echo "wrote $OUT (${SECS}s, 1080x1920)"
