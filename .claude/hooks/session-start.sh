#!/usr/bin/env bash
# Installs the Python dependencies the queue/namecode scripts and tests import
# (requests, Pillow, anthropic, numpy, imageio-ffmpeg, pynacl) plus pytest to
# run the test suite. Only needed in fresh Claude Code on the web containers —
# local dev machines are expected to already have these set up.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if python3 -c "import requests, PIL, anthropic, numpy, nacl, imageio_ffmpeg, pytest" >/dev/null 2>&1; then
  exit 0
fi

echo "[session-start] installing Python dependencies..." >&2
pip install --quiet requests Pillow anthropic numpy imageio-ffmpeg pynacl pytest >&2 || {
  echo "[session-start] pip install failed" >&2; exit 0; }
echo "[session-start] done" >&2

exit 0
