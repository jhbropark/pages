#!/usr/bin/env bash
# Ensures the vendored Krea MCP server (a patched fork of @vmosaic/krea-mcp-server
# with corrected API endpoint paths) has its single dependency installed.
# Runs at SessionStart so `node vendor/krea-mcp-server/src/index.js` can boot.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/vendor/krea-mcp-server"
if [ -d "$DIR/node_modules/@modelcontextprotocol/sdk" ]; then
  exit 0
fi
echo "[setup-krea-mcp] installing dependencies for vendored Krea MCP server..." >&2
( cd "$DIR" && npm install --omit=dev --no-audit --no-fund --silent ) >&2 || {
  echo "[setup-krea-mcp] npm install failed" >&2; exit 0; }
echo "[setup-krea-mcp] done" >&2
