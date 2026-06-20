# Krea MCP server (patched fork)

Local fork of [`@vmosaic/krea-mcp-server`](https://www.npmjs.com/package/@vmosaic/krea-mcp-server)
`1.0.1` with corrected Krea API endpoint paths.

## Why this fork exists

The upstream package hardcodes a model-name → API-path table, but most of the
paths use **made-up version slugs** that do not exist on `https://api.krea.ai`,
so every model except `flux`, `nano-banana`, and `hailuo` returned:

```
Krea API error: 404 - {"message":"Endpoint not found"}
```

`@latest` does not help — `1.0.1` is the newest published version and the bug is
in its source. The paths were verified and corrected against the official API
reference at <https://docs.krea.ai/api-reference> (OpenAPI), which uses the form
`provider/model-version`.

## What was fixed

**Image model paths** (`src/index.js` → `IMAGE_MODELS`)

| model | upstream (404) | corrected (200) |
|-------|----------------|-----------------|
| krea-1 | `krea/k1` | `krea/krea-2/large` (krea-1 retired → Krea 2 flagship) |
| imagen-4 | `google/imagen/v4` | `google/imagen-4` |
| ideogram | `ideogram/v2` | `ideogram/ideogram-3` |
| seedream | `bytedance/seedream/v4` | `bytedance/seedream-4` |
| chatgpt-image | `openai/gpt-image/v1` | `openai/gpt-image` |
| flux-pro | `bfl/flux-1-pro` | `bfl/flux-1.1-pro` |

**Video model paths** (`VIDEO_MODELS`)

| model | upstream (404) | corrected |
|-------|----------------|-----------|
| kling | `kuaishou/kling/v1.6` | `kling/kling-1.6` |
| runway | `runway/gen4` | `runway/gen-4.5` |
| veo-3 | `google/veo/v3` | `google/veo-3` |
| wan | `alibaba/wan/v2.5` | `alibaba/wan-2.5` |
| luma | `luma/ray/v2` | `luma/ray-2` |

`pika` and `sora` were removed — they are not exposed by the Krea API.

**Per-model request bodies**

Each endpoint has its own schema with `additionalProperties: false`, so:

- standard image models require `width` + `height` (now defaulted to 1024);
- the Krea 2 family requires `aspect_ratio` + `resolution` (enum `1K`/`2K`/…)
  instead of `width`/`height`;
- video endpoints take `start_image` (not `image_url`) and reject
  `duration`/`aspect_ratio`, which previously caused `422` errors.

## Verified working models (this API key)

Images: flux, flux-pro, ideogram, imagen-4, chatgpt-image, nano-banana,
seedream, krea-2 (krea-1 alias). Video: hailuo, plus the corrected
kling/runway/veo-3/wan/luma paths.

## Install / run

```bash
cd vendor/krea-mcp-server && npm install --omit=dev
KREA_API_KEY=... node src/index.js
```

`node_modules/` is gitignored; a SessionStart hook
(`.claude/hooks/setup-krea-mcp.sh`) installs the single dependency
(`@modelcontextprotocol/sdk`) automatically. `.mcp.json` runs the server via
`node vendor/krea-mcp-server/src/index.js`.
