# Rendered Video Publish Pipeline

`video_pipeline/remotion/`에서 로컬 Remotion 영상을 렌더링하고, `.github/workflows/video-publish.yml`을 수동 실행해 YouTube, Instagram, Facebook Page, TikTok에 게시합니다.

## 실행 순서

1. 로컬에서 Remotion 렌더링
2. `dispatch-local.mjs`가 MP4를 임시 GitHub Release asset으로 업로드
3. GitHub Actions의 `Rendered video publish` 자동 실행
4. 기본값은 `dry_run=true`
5. 확인 후 `--live`로 실제 게시

직접 실행:

```powershell
node video_pipeline/dispatch-local.mjs --file outputs\sample-001-vertical.mp4 --title "VARIS 프로젝트" --description "프로젝트 영상" --channels youtube,instagram,facebook,tiktok
node video_pipeline/dispatch-local.mjs --file outputs\sample-001-vertical.mp4 --title "VARIS 프로젝트" --live
```

GitHub Actions는 Release asset URL을 그대로 사용하므로 별도 파일 서버가 필요하지 않습니다.

## 기존 Secrets 연결

이미 저장소에 있는 이름을 그대로 사용합니다.

- Instagram: `IG_USER_ID`, `IG_ACCESS_TOKEN`
- Facebook Page: `FB_PAGE_ID`, `FB_PAGE_TOKEN`

추가해야 하는 Secrets:

- YouTube: `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`
- TikTok: `TIKTOK_ACCESS_TOKEN`

TikTok은 기본적으로 `FILE_UPLOAD` 방식으로 로컬 렌더 파일을 직접 전송하므로 GitHub Release 도메인 검증이 필요하지 않습니다. `PULL_FROM_URL`로 바꾸려면 TikTok Developer에서 해당 도메인 또는 URL prefix를 먼저 검증해야 합니다.

선택 Repository Variables:

- `YOUTUBE_PRIVACY`: `private` 권장, 검증 후 `unlisted` 또는 `public`
- `TIKTOK_PRIVACY_LEVEL`: 기본 `SELF_ONLY`

YouTube refresh token은 `youtube.upload` 권한으로 발급해야 하며, TikTok token은 Content Posting API 권한이 필요합니다. 토큰 값은 채팅에 보내지 말고 GitHub Settings의 Repository secrets에 직접 저장합니다.
