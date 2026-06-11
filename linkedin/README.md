# LinkedIn 게시 설정

이 저장소는 LinkedIn 개인 프로필 또는 회사 페이지에 이미지 게시물을 예약
업로드할 수 있습니다.

## 1. LinkedIn 앱 생성

1. [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps)에서 앱을
   생성합니다.
2. 개인 프로필 게시라면 Products에서 `Share on LinkedIn`을 활성화하고
   `w_member_social` 권한으로 OAuth 토큰을 발급합니다.
3. 회사 페이지 게시라면 Community Management API 접근과
   `w_organization_social` 권한이 필요합니다. 인증한 사용자는 해당 페이지의
   관리자 또는 콘텐츠 관리자여야 합니다.

## 2. GitHub Actions Secret

저장소 `Settings > Secrets and variables > Actions`에 등록합니다.

- `LINKEDIN_ACCESS_TOKEN`: OAuth 2.0 사용자 액세스 토큰
- `LINKEDIN_AUTHOR_URN`:
  - 개인 프로필: `urn:li:person:{PERSON_ID}`
  - 회사 페이지: `urn:li:organization:{ORGANIZATION_ID}`

토큰은 만료될 수 있으므로 만료 전에 교체해야 합니다.

## 3. 큐 형식

`linkedin/queue.json`의 `items`에 아래 형식으로 추가합니다.

```json
{
  "id": "linkedin_20260612",
  "status": "pending",
  "commentary": "LinkedIn 본문",
  "hashtags": ["#MedicalAnimation", "#ScienceCommunication"],
  "image_url": "https://jhbropark.github.io/pages/images/example.jpg",
  "alt_text": "카드 이미지 설명",
  "scheduled_time": "2026-06-12T09:00:00+09:00"
}
```

워크플로우는 매시 30분에 실행되며 예약 시간이 지난 `pending` 항목만
게시합니다. 수동 테스트는 Actions의 `LinkedIn 예약 업로드`에서
`Run workflow`를 실행합니다.

## 권한 참고

- 개인 게시: `w_member_social`
- 회사 페이지 게시: `w_organization_social` 및 적절한 페이지 역할
- 공식 API는 `Linkedin-Version`과 `X-Restli-Protocol-Version: 2.0.0`
  헤더를 요구합니다.
