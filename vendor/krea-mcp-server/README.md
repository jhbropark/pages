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

---

## 한국어 요약

이 디렉터리는 `@vmosaic/krea-mcp-server@1.0.1`의 **수정본 fork** 입니다.

### 왜 고쳤나
원본 패키지가 모델명 → API 경로를 **존재하지 않는 가짜 버전 슬러그**로 하드코딩해
`flux`·`nano-banana`·`hailuo`를 제외한 모든 모델이 `404 Endpoint not found`를
반환했습니다. `@latest`로도 해결되지 않습니다(1.0.1이 최신이며 버그가 그 소스에 있음).
경로는 공식 API 레퍼런스(<https://docs.krea.ai/api-reference>)의
`provider/model-버전` 형식으로 교정했습니다.

### 이미지 모델 경로 교정

| 모델 | 원본 (404) | 교정 (200) |
|------|------------|------------|
| krea-1 | `krea/k1` | `krea/krea-2/large` (krea-1 폐기 → Krea 2 플래그십) |
| imagen-4 | `google/imagen/v4` | `google/imagen-4` |
| ideogram | `ideogram/v2` | `ideogram/ideogram-3` |
| seedream | `bytedance/seedream/v4` | `bytedance/seedream-4` |
| chatgpt-image | `openai/gpt-image/v1` | `openai/gpt-image` |
| flux-pro | `bfl/flux-1-pro` | `bfl/flux-1.1-pro` |

### 영상 모델 경로 교정

| 모델 | 원본 (404) | 교정 |
|------|------------|------|
| kling | `kuaishou/kling/v1.6` | `kling/kling-1.6` |
| runway | `runway/gen4` | `runway/gen-4.5` |
| veo-3 | `google/veo/v3` | `google/veo-3` |
| wan | `alibaba/wan/v2.5` | `alibaba/wan-2.5` |
| luma | `luma/ray/v2` | `luma/ray-2` |

`pika`·`sora`는 Krea API에 노출되지 않아 제거했습니다.

### 모델별 요청 본문(body) 차이
각 엔드포인트가 `additionalProperties: false` 스키마라서 파라미터가 다릅니다.

- 표준 이미지 모델: `width` + `height` 필요 (기본값 1024)
- Krea 2 계열: `width`/`height` 대신 `aspect_ratio` + `resolution`(enum `1K`/`2K`/…) 필요
- 영상 엔드포인트: `image_url`이 아니라 `start_image` 사용, `duration`/`aspect_ratio`는
  거부됨(이전에 `422` 오류 원인)

### 검증된 동작 모델 (현재 API 키 기준)
- 이미지: flux, flux-pro, ideogram, imagen-4, chatgpt-image, nano-banana,
  seedream, krea-2(krea-1 별칭)
- 영상: hailuo, 그리고 교정된 kling/runway/veo-3/wan/luma 경로

> ⚠️ 적용 시점: 교정된 매핑은 **다음 세션(또는 MCP 재시작)부터** `mcp__krea__`
> 도구에 반영됩니다. 현재 세션에 이미 로드된 옛 서버에는 적용되지 않습니다.
