# Remotion Video Pipeline

로컬 원본 영상을 Remotion으로 세로형 영상으로 렌더링하고, GitHub Actions에서 채널별 업로드 단계로 넘기는 골격입니다.

## 흐름

1. `E:\00_Project_Videos`에서 영상 카탈로그 생성
2. `jobs/*.json`에서 원본과 게시 메타데이터 선택
3. 로컬에서 Remotion MP4 렌더링
4. 렌더링 결과를 공개/서명 URL 또는 저장소에 업로드
5. GitHub Actions `Upload rendered video` 실행
6. YouTube, Instagram, Facebook, TikTok 어댑터로 게시

GitHub Actions는 로컬 PC의 `E:` 드라이브를 볼 수 없으므로, 렌더링 파일을 Actions가 접근할 수 있는 위치로 전달해야 합니다.

## 시작

```powershell
cd C:\Users\im\.aside\u\0\remotion-video-pipeline
npm install
npm run discover
```

지원 프리셋은 `vertical`(릴스/쇼츠, 1080×1920), `landscape`(강의/유튜브, 1920×1080), `square`(피드/광고, 1080×1080)입니다. `jobs/example.json`의 `preset`과 `sourceAbsolutePath`를 실제 값으로 바꾼 뒤:

```powershell
npm run render -- --job jobs/example.json
```

결과는 `outputs/`에 생성됩니다.

## 업로드 검증

실제 게시 전 반드시 드라이런으로 확인합니다.

```powershell
npm run upload -- --file outputs/sample-001-vertical.mp4 --metadata jobs/example.json --dry-run
```

## GitHub Actions

`.github/workflows/upload.yml`은 `workflow_dispatch`로 실행합니다.

필수 입력:
- `media_url`: 렌더링 MP4의 공개 또는 서명 URL
- `metadata_json`: 제목, 설명, 태그, 채널 목록 JSON
- `dry_run`: 기본값 `true`

필요한 Repository Secrets:
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`
- `META_ACCESS_TOKEN`
- `INSTAGRAM_USER_ID`
- `FACEBOOK_PAGE_ID`
- `TIKTOK_ACCESS_TOKEN`

현재 업로드 스크립트는 인증 누락을 차단하고 드라이런 검증까지 제공합니다. 실제 게시 어댑터는 각 채널 계정 ID와 OAuth 정책을 확정한 후 활성화해야 합니다.

## 다음 구현 단계

- 채널별 제목/설명 길이와 해시태그 규칙 분리
- YouTube Data API 업로드 어댑터
- Instagram Graph API 릴스 컨테이너 업로드
- Facebook Page Video 업로드
- TikTok Content Posting API 업로드
- 업로드 결과 URL과 상태를 `jobs/*.json` 또는 Notion에 기록
