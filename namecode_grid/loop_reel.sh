#!/usr/bin/env bash
# Loop a short Krea reel seed into a finished IG reel (1080x1920, 30fps, silent).
#
# Default mode "boomerang" plays the seed forward then reversed before looping.
# Krea seeds aren't seamless (start frame != end frame, directional motion), so a
# plain end-to-start loop shows a hard-cut jump. Boomerang makes both joins
# frame-matched -> no seam (and reads as "emerge then recede", on-theme).
#
# Usage: loop_reel.sh <seed.mp4> [out.mp4] [seconds] [mode: boomerang|plain]
# Honors $FFMPEG (path to an ffmpeg binary); falls back to `ffmpeg` on PATH.
set -euo pipefail
IN="${1:?seed mp4 required}"
OUT="${2:-reel_30s.mp4}"
SECS="${3:-30}"
MODE="${4:-boomerang}"
FF="${FFMPEG:-ffmpeg}"

TMP="$(mktemp -d)"; CYCLE="$TMP/cycle.mp4"; trap 'rm -rf "$TMP"' EXIT
VF="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30"

if [ "$MODE" = "boomerang" ]; then
  # forward + reversed -> one seamless cycle
  "$FF" -y -i "$IN" \
    -filter_complex "[0]reverse[r];[0][r]concat=n=2:v=1:a=0,$VF[v]" \
    -map "[v]" -c:v libx264 -preset medium -pix_fmt yuv420p "$CYCLE"
else
  "$FF" -y -i "$IN" -vf "$VF" -c:v libx264 -preset medium -pix_fmt yuv420p "$CYCLE"
fi

# loop the seamless cycle up to the target duration
"$FF" -y -stream_loop -1 -i "$CYCLE" -t "$SECS" \
  -c:v libx264 -preset medium -pix_fmt yuv420p -movflags +faststart -an "$OUT"

echo "wrote $OUT (${SECS}s, 1080x1920, mode=$MODE)"
